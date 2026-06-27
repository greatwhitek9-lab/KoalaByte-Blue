/* KoalaByte Blue Heltec T114 combined-safe firmware.
 *
 * Default one-shot role:
 *   - Heltec T114 onboard nRF52840 is the primary BLE radio endpoint.
 *   - BLE RX: passive advertisement observation emits normalized JSON to the Pi.
 *   - BLE TX: Pi-commanded, bounded, non-connectable owned-lab beacon only.
 *   - ESP32-S3 DualEye BLE and Raspberry Pi BlueZ remain secondary/fallback nodes.
 *   - KillerKoala mouth/status commands share the same USB CDC JSON stream.
 *   - GNSS and LoRa status hooks are exposed, but direct GNSS UART and SX1262 radio
 *     driving stay guarded until the exact T114 pin map and recovery path are validated.
 *
 * Safety boundary: no pairing, no GATT writes, no spoofing, no jamming, and no LoRa
 * transmit path in this firmware. BLE transmit is limited to a local, non-connectable
 * lab beacon started by an explicit Pi command.
 */

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/sys/printk.h>
#include <zephyr/sys/util.h>
#include <zephyr/usb/usb_device.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/hci.h>

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define KOALA_DEVICE "heltec-t114-nrf52840"
#define KOALA_ROLE "primary"
#define KOALA_FW "0.3.0-t114-combined-safe-ble-txrx"
#define KOALA_DUPLICATE_SUPPRESS_MS 5000
#define KOALA_RSSI_CHANGE_DB 8
#define KOALA_CACHE_SIZE 48
#define KOALA_NAME_MAX 31
#define KOALA_MFG_MAX 20
#define KOALA_LINE_MAX 256
#define KOALA_STATUS_MS 15000
#define KOALA_FACE_DEFAULT_MS 4500
#define KOALA_TX_DEFAULT_MS 30000
#define KOALA_TX_MAX_MS 60000
#define KOALA_ADV_NAME_MAX 20

#define CONSOLE_NODE DT_CHOSEN(zephyr_console)
static const struct device *const console_dev = DEVICE_DT_GET(CONSOLE_NODE);

struct seen_entry {
    bt_addr_le_t addr;
    int8_t rssi;
    int64_t last_ms;
    bool used;
};

struct adv_summary {
    char name[KOALA_NAME_MAX + 1];
    char manufacturer_hex[(KOALA_MFG_MAX * 2) + 1];
};

static struct seen_entry seen[KOALA_CACHE_SIZE];
static uint32_t total_seen;
static uint32_t total_emitted;
static uint32_t total_tx_started;
static int64_t boot_ms;
static int64_t last_status_ms;
static bool ble_scan_active;
static bool ble_ready;
static bool ble_adv_active;
static int64_t ble_adv_until_ms;
static char ble_adv_name[KOALA_ADV_NAME_MAX + 1] = "KoalaByte-T114";

static char current_state[32] = "boot";
static char current_message[96] = "killerkoala online";
static bool face_enabled = true;
static int64_t face_until_ms;
static char rx_line[KOALA_LINE_MAX];
static size_t rx_len;

static void bytes_to_hex(const uint8_t *data, uint8_t len, char *out, size_t out_len)
{
    static const char hex[] = "0123456789abcdef";
    size_t pos = 0;

    if (!out || out_len == 0) {
        return;
    }
    if (len > KOALA_MFG_MAX) {
        len = KOALA_MFG_MAX;
    }
    for (uint8_t i = 0; i < len && pos + 2 < out_len; i++) {
        out[pos++] = hex[(data[i] >> 4) & 0x0f];
        out[pos++] = hex[data[i] & 0x0f];
    }
    out[pos] = '\0';
}

static void sanitize_ascii(char *text)
{
    if (!text) {
        return;
    }
    for (size_t i = 0; text[i] != '\0'; i++) {
        unsigned char ch = (unsigned char)text[i];
        if (ch < 32 || ch > 126 || ch == '"' || ch == '\\') {
            text[i] = '?';
        }
    }
}

static void copy_safe(char *dst, size_t dst_len, const char *src, const char *fallback)
{
    const char *value = (src && src[0]) ? src : fallback;
    if (!dst || dst_len == 0) {
        return;
    }
    snprintf(dst, dst_len, "%s", value ? value : "");
    sanitize_ascii(dst);
}

static bool extract_json_string(const char *line, const char *key, char *out, size_t out_len)
{
    char pattern[48];
    const char *p;
    const char *q;
    size_t len;

    if (!line || !key || !out || out_len == 0) {
        return false;
    }
    snprintf(pattern, sizeof(pattern), "\"%s\"", key);
    p = strstr(line, pattern);
    if (!p) {
        return false;
    }
    p = strchr(p + strlen(pattern), ':');
    if (!p) {
        return false;
    }
    p = strchr(p, '"');
    if (!p) {
        return false;
    }
    p++;
    q = strchr(p, '"');
    if (!q) {
        return false;
    }
    len = (size_t)(q - p);
    if (len >= out_len) {
        len = out_len - 1;
    }
    memcpy(out, p, len);
    out[len] = '\0';
    sanitize_ascii(out);
    return true;
}

static int extract_json_int(const char *line, const char *key, int fallback)
{
    char pattern[48];
    const char *p;

    if (!line || !key) {
        return fallback;
    }
    snprintf(pattern, sizeof(pattern), "\"%s\"", key);
    p = strstr(line, pattern);
    if (!p) {
        return fallback;
    }
    p = strchr(p + strlen(pattern), ':');
    if (!p) {
        return fallback;
    }
    p++;
    while (*p == ' ' || *p == '\t') {
        p++;
    }
    return atoi(p);
}

static bool json_true(const char *line, const char *key)
{
    char pattern[48];
    const char *p;

    if (!line || !key) {
        return false;
    }
    snprintf(pattern, sizeof(pattern), "\"%s\"", key);
    p = strstr(line, pattern);
    if (!p) {
        return false;
    }
    p = strchr(p + strlen(pattern), ':');
    if (!p) {
        return false;
    }
    p++;
    while (*p == ' ' || *p == '\t') {
        p++;
    }
    return strncmp(p, "true", 4) == 0;
}

static bool same_addr(const bt_addr_le_t *a, const bt_addr_le_t *b)
{
    return a && b && a->type == b->type && memcmp(&a->a, &b->a, sizeof(a->a)) == 0;
}

static bool should_emit(const bt_addr_le_t *addr, int8_t rssi)
{
    int64_t now = k_uptime_get();
    int empty = -1;
    int oldest = 0;
    int64_t oldest_ms = INT64_MAX;

    for (int i = 0; i < KOALA_CACHE_SIZE; i++) {
        if (!seen[i].used) {
            if (empty < 0) {
                empty = i;
            }
            continue;
        }
        if (same_addr(&seen[i].addr, addr)) {
            bool due = (now - seen[i].last_ms) >= KOALA_DUPLICATE_SUPPRESS_MS;
            bool moved = abs((int)rssi - (int)seen[i].rssi) >= KOALA_RSSI_CHANGE_DB;
            seen[i].last_ms = now;
            seen[i].rssi = rssi;
            return due || moved;
        }
        if (seen[i].last_ms < oldest_ms) {
            oldest_ms = seen[i].last_ms;
            oldest = i;
        }
    }

    int slot = empty >= 0 ? empty : oldest;
    seen[slot].addr = *addr;
    seen[slot].rssi = rssi;
    seen[slot].last_ms = now;
    seen[slot].used = true;
    return true;
}

static bool parse_ad_cb(struct bt_data *data, void *user_data)
{
    struct adv_summary *summary = user_data;

    if (!summary || !data) {
        return true;
    }
    if ((data->type == BT_DATA_NAME_COMPLETE || data->type == BT_DATA_NAME_SHORTENED) && summary->name[0] == '\0') {
        size_t copy_len = MIN((size_t)data->data_len, (size_t)KOALA_NAME_MAX);
        memcpy(summary->name, data->data, copy_len);
        summary->name[copy_len] = '\0';
        sanitize_ascii(summary->name);
    } else if (data->type == BT_DATA_MANUFACTURER_DATA && summary->manufacturer_hex[0] == '\0') {
        bytes_to_hex(data->data, data->data_len, summary->manufacturer_hex, sizeof(summary->manufacturer_hex));
    }
    return true;
}

static const char *addr_type_name(uint8_t type)
{
    switch (type) {
    case BT_ADDR_LE_PUBLIC:
        return "public";
    case BT_ADDR_LE_RANDOM:
        return "random";
    default:
        return "unknown";
    }
}

static void emit_ble_status(const char *reason)
{
    int64_t now = k_uptime_get();
    printk("{\"type\":\"ble_status\",\"device\":\"%s\",\"source\":\"%s\",\"role\":\"%s\",\"transport\":\"usb-cdc\",\"reason\":\"%s\",\"ble_ready\":%s,\"scan_active\":%s,\"adv_active\":%s,\"active_scan\":false,\"total_seen\":%u,\"total_emitted\":%u,\"total_tx_started\":%u,\"uptime_ms\":%lld}\n",
           KOALA_DEVICE, KOALA_DEVICE, KOALA_ROLE, reason ? reason : "status",
           ble_ready ? "true" : "false", ble_scan_active ? "true" : "false", ble_adv_active ? "true" : "false",
           total_seen, total_emitted, total_tx_started, (long long)(now - boot_ms));
}

static void emit_tx_status(const char *status, const char *reason)
{
    printk("{\"type\":\"ble_tx_status\",\"device\":\"%s\",\"source\":\"%s\",\"role\":\"%s\",\"transport\":\"usb-cdc\",\"status\":\"%s\",\"reason\":\"%s\",\"adv_active\":%s,\"adv_name\":\"%s\",\"non_connectable\":true,\"owned_lab_only\":true,\"total_tx_started\":%u}\n",
           KOALA_DEVICE, KOALA_DEVICE, KOALA_ROLE, status ? status : "status", reason ? reason : "status",
           ble_adv_active ? "true" : "false", ble_adv_name, total_tx_started);
}

static void emit_mouth_status(void)
{
    printk("{\"type\":\"heltec_mouth_status\",\"device\":\"heltec-t114\",\"source\":\"%s\",\"transport\":\"usb-cdc\",\"state\":\"%s\",\"message\":\"%s\",\"face_enabled\":%s,\"fw\":\"%s\",\"uptime_ms\":%lld}\n",
           KOALA_DEVICE, current_state, current_message, face_enabled ? "true" : "false", KOALA_FW,
           (long long)(k_uptime_get() - boot_ms));
}

static void emit_ack(const char *state)
{
    printk("{\"type\":\"killerkoala_tft_ack\",\"device\":\"heltec-t114-color\",\"source\":\"%s\",\"state\":\"%s\",\"active\":true,\"gnss_enabled\":false,\"ble_primary_enabled\":true,\"ble_scan_active\":%s,\"ble_tx_active\":%s,\"transport\":\"usb-cdc\"}\n",
           KOALA_DEVICE, state ? state : current_state, ble_scan_active ? "true" : "false", ble_adv_active ? "true" : "false");
}

static void emit_gnss_status(void)
{
    printk("{\"type\":\"gnss_status\",\"device\":\"heltec-t114\",\"source\":\"%s\",\"transport\":\"usb-cdc\",\"enabled\":false,\"guarded\":true,\"status\":\"pin_validation_required\",\"note\":\"GNSS JSON hook is present; direct GNSS UART parsing is disabled until the exact T114 GNSS UART pins are validated.\"}\n",
           KOALA_DEVICE);
}

static void emit_lora_status(void)
{
    printk("{\"type\":\"lora_status\",\"device\":\"heltec-t114\",\"source\":\"%s\",\"transport\":\"usb-cdc\",\"enabled\":false,\"guarded\":true,\"status\":\"pin_validation_required\",\"note\":\"SX1262/LoRa transmit and receive are disabled in combined-safe firmware until the exact SPI, DIO, reset, busy, RF switch, and region settings are validated.\"}\n",
           KOALA_DEVICE);
}

static void emit_node_roles(void)
{
    printk("{\"type\":\"node_roles\",\"device\":\"heltec-t114\",\"primary_ble\":\"heltec-t114-nrf52840\",\"rx_path\":\"passive_adv_observer\",\"tx_path\":\"pi_commanded_non_connectable_lab_beacon\",\"secondary_ble_nodes\":[\"esp32-s3-dualeye\",\"raspberry-pi-bluez\"],\"transport\":\"usb-cdc\",\"active_scan\":false}\n");
}

static void handle_face_command(const char *line)
{
    char value[96];
    int duration_ms = extract_json_int(line, "duration_ms", KOALA_FACE_DEFAULT_MS);

    if (duration_ms < 250) {
        duration_ms = KOALA_FACE_DEFAULT_MS;
    }
    if (duration_ms > 30000) {
        duration_ms = 30000;
    }
    if (extract_json_string(line, "state", value, sizeof(value))) {
        copy_safe(current_state, sizeof(current_state), value, "speaking");
    } else {
        copy_safe(current_state, sizeof(current_state), "speaking", "speaking");
    }
    if (extract_json_string(line, "message", value, sizeof(value))) {
        copy_safe(current_message, sizeof(current_message), value, "");
    }
    face_enabled = strstr(line, "\"enabled\":false") == NULL;
    face_until_ms = k_uptime_get() + duration_ms;
    emit_ack(current_state);
}

static void stop_lab_advertising(const char *reason)
{
    int err;

    if (!ble_adv_active) {
        emit_tx_status("idle", reason ? reason : "already_stopped");
        return;
    }
    err = bt_le_adv_stop();
    if (err) {
        printk("{\"type\":\"ble_tx_error\",\"device\":\"%s\",\"source\":\"%s\",\"message\":\"advertise stop failed\",\"err\":%d}\n",
               KOALA_DEVICE, KOALA_DEVICE, err);
        return;
    }
    ble_adv_active = false;
    ble_adv_until_ms = 0;
    emit_tx_status("stopped", reason ? reason : "stopped");
}

static void start_lab_advertising(const char *line)
{
    int err;
    int duration_ms = extract_json_int(line, "duration_ms", KOALA_TX_DEFAULT_MS);
    char value[KOALA_ADV_NAME_MAX + 1];
    const struct bt_data ad[] = {
        BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR)),
    };
    struct bt_data sd[] = {
        BT_DATA(BT_DATA_NAME_COMPLETE, ble_adv_name, strlen(ble_adv_name)),
    };

    if (!json_true(line, "confirm")) {
        emit_tx_status("blocked", "confirm_true_required");
        return;
    }
    if (!ble_ready) {
        emit_tx_status("blocked", "ble_not_ready");
        return;
    }
    if (duration_ms < 1000) {
        duration_ms = KOALA_TX_DEFAULT_MS;
    }
    if (duration_ms > KOALA_TX_MAX_MS) {
        duration_ms = KOALA_TX_MAX_MS;
    }
    if (extract_json_string(line, "name", value, sizeof(value))) {
        copy_safe(ble_adv_name, sizeof(ble_adv_name), value, "KoalaByte-T114");
    }
    sd[0].data = ble_adv_name;
    sd[0].data_len = strlen(ble_adv_name);

    if (ble_adv_active) {
        stop_lab_advertising("restart");
    }
    err = bt_le_adv_start(BT_LE_ADV_NCONN, ad, ARRAY_SIZE(ad), sd, ARRAY_SIZE(sd));
    if (err) {
        printk("{\"type\":\"ble_tx_error\",\"device\":\"%s\",\"source\":\"%s\",\"message\":\"non-connectable advertising start failed\",\"err\":%d}\n",
               KOALA_DEVICE, KOALA_DEVICE, err);
        return;
    }
    ble_adv_active = true;
    ble_adv_until_ms = k_uptime_get() + duration_ms;
    total_tx_started++;
    emit_tx_status("started", "pi_commanded_owned_lab_beacon");
}

static void handle_line(const char *line)
{
    if (!line || line[0] == '\0') {
        return;
    }
    if (strstr(line, "\"type\":\"killerkoala_face\"") || strstr(line, "\"type\":\"ai_face\"")) {
        handle_face_command(line);
    } else if (strstr(line, "\"type\":\"status\"") || strstr(line, "\"type\":\"heltec_mouth_status\"")) {
        emit_mouth_status();
    } else if (strstr(line, "\"type\":\"gnss_status\"")) {
        emit_gnss_status();
    } else if (strstr(line, "\"type\":\"lora_status\"")) {
        emit_lora_status();
    } else if (strstr(line, "\"type\":\"ble_status\"")) {
        emit_ble_status("command");
    } else if (strstr(line, "\"type\":\"ble_tx_status\"")) {
        emit_tx_status("status", "command");
    } else if (strstr(line, "\"type\":\"ble_lab_advertise_start\"")) {
        start_lab_advertising(line);
    } else if (strstr(line, "\"type\":\"ble_lab_advertise_stop\"")) {
        stop_lab_advertising("pi_commanded_stop");
    } else if (strstr(line, "\"type\":\"node_roles\"")) {
        emit_node_roles();
    } else {
        printk("{\"type\":\"error\",\"device\":\"heltec-t114\",\"source\":\"%s\",\"error\":\"unknown_type\",\"transport\":\"usb-cdc\"}\n", KOALA_DEVICE);
    }
}

static void poll_usb_commands(void)
{
    unsigned char ch;

    if (!device_is_ready(console_dev)) {
        return;
    }
    while (uart_poll_in(console_dev, &ch) == 0) {
        if (ch == '\n' || ch == '\r') {
            if (rx_len > 0) {
                rx_line[rx_len] = '\0';
                handle_line(rx_line);
                rx_len = 0;
            }
        } else if (rx_len + 1 < sizeof(rx_line)) {
            rx_line[rx_len++] = (char)ch;
        } else {
            rx_len = 0;
            printk("{\"type\":\"error\",\"device\":\"heltec-t114\",\"source\":\"%s\",\"error\":\"line_too_long\",\"transport\":\"usb-cdc\"}\n", KOALA_DEVICE);
        }
    }
}

static void device_found(const bt_addr_le_t *addr, int8_t rssi, uint8_t adv_type, struct net_buf_simple *ad)
{
    char addr_str[BT_ADDR_LE_STR_LEN];
    struct adv_summary summary = {0};

    total_seen++;
    if (!addr || !ad || !should_emit(addr, rssi)) {
        return;
    }

    bt_addr_le_to_str(addr, addr_str, sizeof(addr_str));
    bt_data_parse(ad, parse_ad_cb, &summary);

    printk("{\"type\":\"ble_adv_seen\",\"device\":\"%s\",\"source\":\"%s\",\"role\":\"%s\",\"transport\":\"usb-cdc\",\"addr\":\"%s\",\"addr_type\":\"%s\",\"addr_type_id\":%u,\"rssi\":%d,\"adv_type\":%u,\"active_scan\":false,\"seen_ms\":%lld,\"total_seen\":%u",
           KOALA_DEVICE, KOALA_DEVICE, KOALA_ROLE, addr_str, addr_type_name(addr->type), addr->type,
           rssi, adv_type, (long long)k_uptime_get(), total_seen);
    if (summary.name[0] != '\0') {
        printk(",\"name\":\"%s\"", summary.name);
    }
    if (summary.manufacturer_hex[0] != '\0') {
        printk(",\"manufacturer\":\"%s\"", summary.manufacturer_hex);
    }
    printk("}\n");
    total_emitted++;
}

static void start_ble_primary(void)
{
    int err;
    const struct bt_le_scan_param scan_param = {
        .type = BT_LE_SCAN_TYPE_PASSIVE,
        .options = BT_LE_SCAN_OPT_NONE,
        .interval = BT_GAP_SCAN_FAST_INTERVAL,
        .window = BT_GAP_SCAN_FAST_WINDOW,
    };

    err = bt_enable(NULL);
    if (err) {
        printk("{\"type\":\"ble_error\",\"device\":\"%s\",\"source\":\"%s\",\"role\":\"%s\",\"message\":\"Bluetooth init failed\",\"err\":%d}\n",
               KOALA_DEVICE, KOALA_DEVICE, KOALA_ROLE, err);
        return;
    }
    ble_ready = true;

    err = bt_le_scan_start(&scan_param, device_found);
    if (err) {
        printk("{\"type\":\"ble_error\",\"device\":\"%s\",\"source\":\"%s\",\"role\":\"%s\",\"message\":\"passive scan start failed\",\"err\":%d}\n",
               KOALA_DEVICE, KOALA_DEVICE, KOALA_ROLE, err);
        return;
    }
    ble_scan_active = true;
    emit_ble_status("started");
}

int main(void)
{
    int64_t now;

    boot_ms = k_uptime_get();

    if (usb_enable(NULL) != 0) {
        printk("{\"type\":\"usb_error\",\"device\":\"heltec-t114\",\"source\":\"%s\",\"message\":\"usb_enable failed\"}\n", KOALA_DEVICE);
    }

    k_sleep(K_MSEC(1200));
    printk("{\"type\":\"boot\",\"device\":\"heltec-t114\",\"source\":\"%s\",\"role\":\"%s\",\"fw\":\"%s\",\"transport\":\"usb-cdc\",\"scope\":\"primary BLE RX plus guarded Pi-commanded BLE TX and mouth/status JSON; GNSS and LoRa hooks guarded until pin validation\"}\n",
           KOALA_DEVICE, KOALA_ROLE, KOALA_FW);
    emit_node_roles();
    emit_mouth_status();
    emit_gnss_status();
    emit_lora_status();
    emit_tx_status("idle", "boot");
    start_ble_primary();

    while (true) {
        poll_usb_commands();
        now = k_uptime_get();
        if (face_enabled && face_until_ms > 0 && now > face_until_ms) {
            face_until_ms = 0;
            copy_safe(current_state, sizeof(current_state), "idle", "idle");
        }
        if (ble_adv_active && ble_adv_until_ms > 0 && now > ble_adv_until_ms) {
            stop_lab_advertising("duration_complete");
        }
        if (now - last_status_ms >= KOALA_STATUS_MS) {
            last_status_ms = now;
            emit_ble_status("heartbeat");
        }
        k_sleep(K_MSEC(30));
    }

    return 0;
}
