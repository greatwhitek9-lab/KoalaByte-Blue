/* KoalaByte Blue nRF52840 Dongle BLE-primary observer.
 *
 * Safe purpose: passively observe BLE advertisements from authorized lab space,
 * emit normalized JSON observations to the Raspberry Pi over USB CDC serial,
 * and act as the canonical BLE source for the main branch node-manager flow.
 *
 * This firmware does not pair, connect, write, spoof, disrupt, or replay BLE traffic.
 */

#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include <zephyr/sys/util.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/hci.h>

#define KOALA_DEVICE "nrf52840-dongle"
#define KOALA_ROLE "primary"
#define KOALA_DUPLICATE_SUPPRESS_MS 5000
#define KOALA_RSSI_CHANGE_DB 8
#define KOALA_CACHE_SIZE 32
#define KOALA_NAME_MAX 31
#define KOALA_MFG_MAX 20
#define KOALA_STATUS_MS 15000

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
static int64_t boot_ms;
static int64_t last_status_ms;

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

static bool same_addr(const bt_addr_le_t *a, const bt_addr_le_t *b)
{
    return bt_addr_le_cmp(a, b) == 0;
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

static void emit_status(const char *reason)
{
    int64_t now = k_uptime_get();
    printk("{\"type\":\"ble_status\",\"device\":\"%s\",\"source\":\"%s\",\"role\":\"%s\",\"transport\":\"usb-cdc\",\"reason\":\"%s\",\"scan_active\":true,\"active_scan\":false,\"total_seen\":%u,\"total_emitted\":%u,\"uptime_ms\":%lld}\n",
           KOALA_DEVICE, KOALA_DEVICE, KOALA_ROLE, reason ? reason : "status",
           total_seen, total_emitted, (long long)(now - boot_ms));
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

int main(void)
{
    int err;
    const struct bt_le_scan_param scan_param = {
        .type = BT_LE_SCAN_TYPE_PASSIVE,
        .options = BT_LE_SCAN_OPT_NONE,
        .interval = BT_GAP_SCAN_FAST_INTERVAL,
        .window = BT_GAP_SCAN_FAST_WINDOW,
    };

    boot_ms = k_uptime_get();
    printk("{\"type\":\"boot\",\"device\":\"%s\",\"source\":\"%s\",\"role\":\"%s\",\"fw\":\"0.1.0-main-dongle-ble-primary\",\"transport\":\"usb-cdc\",\"scope\":\"passive BLE advertisement observation only\"}\n",
           KOALA_DEVICE, KOALA_DEVICE, KOALA_ROLE);

    err = bt_enable(NULL);
    if (err) {
        printk("{\"type\":\"ble_error\",\"device\":\"%s\",\"source\":\"%s\",\"role\":\"%s\",\"message\":\"Bluetooth init failed\",\"err\":%d}\n",
               KOALA_DEVICE, KOALA_DEVICE, KOALA_ROLE, err);
        return err;
    }

    err = bt_le_scan_start(&scan_param, device_found);
    if (err) {
        printk("{\"type\":\"ble_error\",\"device\":\"%s\",\"source\":\"%s\",\"role\":\"%s\",\"message\":\"scan start failed\",\"err\":%d}\n",
               KOALA_DEVICE, KOALA_DEVICE, KOALA_ROLE, err);
        return err;
    }

    emit_status("started");

    while (true) {
        k_sleep(K_MSEC(500));
        int64_t now = k_uptime_get();
        if (now - last_status_ms >= KOALA_STATUS_MS) {
            last_status_ms = now;
            emit_status("heartbeat");
        }
    }

    return 0;
}
