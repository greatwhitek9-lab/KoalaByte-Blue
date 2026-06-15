/* KoalaByte Blue nRF52840 DK authorized lab peripheral.
 *
 * Safe purpose: advertise as a clearly labeled owned lab peripheral, emit a
 * synthetic Ear Tag TX Lab service-data pattern for RF/signal-integrity
 * observation, and expose one read-only GATT status characteristic for
 * owned-device/client testing.
 *
 * This firmware does not replay captured packets, captured identifiers, or raw
 * NRF_RADIO packet bytes. The transmitted data below is generated locally and
 * clearly identifies the device as lab hardware.
 */

#include <stdint.h>
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/uuid.h>

#define DEVICE_NAME CONFIG_BT_DEVICE_NAME
#define DEVICE_NAME_LEN (sizeof(DEVICE_NAME) - 1)

#define LAB_BEACON_REFRESH_SECONDS 5

static uint16_t lab_sequence;

static const char lab_status[] =
    "KoalaByte Blue Ear Tag TX Lab; synthetic owned-device BLE advertisement; no captured packet replay";

/* 4b6f616c-6142-6c75-6500-000000000001: KoalaBlue lab service */
static struct bt_uuid_128 koala_service_uuid = BT_UUID_INIT_128(
    0x01, 0x00, 0x00, 0x00,
    0x00, 0x00,
    0x00, 0x65,
    0x75, 0x6c,
    0x42, 0x61, 0x6c, 0x61, 0x6f, 0x4b);

/* 4b6f616c-6142-6c75-6500-000000000002: read-only status characteristic */
static struct bt_uuid_128 koala_status_uuid = BT_UUID_INIT_128(
    0x02, 0x00, 0x00, 0x00,
    0x00, 0x00,
    0x00, 0x65,
    0x75, 0x6c,
    0x42, 0x61, 0x6c, 0x61, 0x6f, 0x4b);

/*
 * Synthetic service-data payload for observation and packet-loss/sequence tests.
 * Layout after the 128-bit UUID:
 *   0-3  ASCII KBTX magic
 *   4    payload format version
 *   5    synthetic pattern byte A
 *   6    synthetic pattern byte B
 *   7    synthetic pattern byte C
 *   8    sequence low byte
 *   9    sequence high byte
 *   10   simple XOR check byte for the synthetic sequence bytes
 */
static uint8_t tx_lab_service_data[] = {
    /* 4b6f616c-6142-6c75-6554-584c41420001: Koala TX Lab service-data UUID */
    0x01, 0x00, 0x42, 0x41,
    0x4c, 0x58,
    0x54, 0x65,
    0x75, 0x6c,
    0x42, 0x61, 0x6c, 0x61, 0x6f, 0x4b,
    'K', 'B', 'T', 'X',
    0x01,
    0xA5, 0x5A, 0x3C,
    0x00, 0x00,
    0xFF,
};

static ssize_t read_lab_status(struct bt_conn *conn,
                               const struct bt_gatt_attr *attr,
                               void *buf,
                               uint16_t len,
                               uint16_t offset)
{
    const char *value = lab_status;
    return bt_gatt_attr_read(conn, attr, buf, len, offset, value, strlen(value));
}

BT_GATT_SERVICE_DEFINE(koala_lab_svc,
    BT_GATT_PRIMARY_SERVICE(&koala_service_uuid.uuid),
    BT_GATT_CHARACTERISTIC(&koala_status_uuid.uuid,
                           BT_GATT_CHRC_READ,
                           BT_GATT_PERM_READ,
                           read_lab_status,
                           NULL,
                           NULL),
);

static struct bt_data ad[] = {
    BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR)),
    BT_DATA(BT_DATA_SVC_DATA128, tx_lab_service_data, sizeof(tx_lab_service_data)),
};

static const struct bt_data sd[] = {
    BT_DATA(BT_DATA_NAME_COMPLETE, DEVICE_NAME, DEVICE_NAME_LEN),
};

static void update_synthetic_payload(void)
{
    tx_lab_service_data[24] = (uint8_t)(lab_sequence & 0xff);
    tx_lab_service_data[25] = (uint8_t)((lab_sequence >> 8) & 0xff);
    tx_lab_service_data[26] = (uint8_t)(0xff ^ tx_lab_service_data[24] ^ tx_lab_service_data[25]);
}

static int start_lab_advertising(void)
{
    update_synthetic_payload();
    return bt_le_adv_start(BT_LE_ADV_CONN, ad, ARRAY_SIZE(ad), sd, ARRAY_SIZE(sd));
}

static void connected(struct bt_conn *conn, uint8_t err)
{
    if (err) {
        printk("Connection failed: 0x%02x\n", err);
        return;
    }
    printk("Client connected to KoalaByte Blue Ear Tag TX Lab peripheral\n");
}

static void disconnected(struct bt_conn *conn, uint8_t reason)
{
    printk("Client disconnected: 0x%02x\n", reason);
}

BT_CONN_CB_DEFINE(conn_callbacks) = {
    .connected = connected,
    .disconnected = disconnected,
};

int main(void)
{
    int err;

    printk("KoalaByte Blue nRF52840 DK Ear Tag TX Lab booting\n");
    printk("Scope: synthetic owned-device BLE advertisement only; no captured packet replay\n");

    err = bt_enable(NULL);
    if (err) {
        printk("Bluetooth init failed: %d\n", err);
        return err;
    }

    err = start_lab_advertising();
    if (err) {
        printk("Advertising failed to start: %d\n", err);
        return err;
    }

    printk("Advertising synthetic Ear Tag TX Lab payload as %s\n", DEVICE_NAME);
    printk("GATT status characteristic is read-only\n");

    while (true) {
        k_sleep(K_SECONDS(LAB_BEACON_REFRESH_SECONDS));
        lab_sequence++;
        err = bt_le_adv_stop();
        if (err && err != -EALREADY) {
            printk("Advertising stop failed: %d\n", err);
        }
        err = start_lab_advertising();
        if (err) {
            printk("Advertising restart failed: %d\n", err);
        } else {
            printk("Ear Tag TX Lab sequence=%u\n", lab_sequence);
        }
    }

    return 0;
}
