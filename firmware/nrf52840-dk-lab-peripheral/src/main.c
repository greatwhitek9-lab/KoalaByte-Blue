/* KoalaByte Blue nRF52840 DK authorized lab peripheral.
 *
 * Safe purpose: advertise as a clearly labeled lab peripheral and expose one
 * read-only GATT status characteristic for owned-device/client testing.
 */

#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/uuid.h>

#define DEVICE_NAME CONFIG_BT_DEVICE_NAME
#define DEVICE_NAME_LEN (sizeof(DEVICE_NAME) - 1)

static const char lab_status[] =
    "KoalaByte Blue authorized lab peripheral; read-only demo";

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

static const struct bt_data ad[] = {
    BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR)),
    BT_DATA(BT_DATA_NAME_COMPLETE, DEVICE_NAME, DEVICE_NAME_LEN),
};

static const struct bt_data sd[] = {
    BT_DATA_BYTES(BT_DATA_UUID128_ALL,
                  0x01, 0x00, 0x00, 0x00,
                  0x00, 0x00,
                  0x00, 0x65,
                  0x75, 0x6c,
                  0x42, 0x61, 0x6c, 0x61, 0x6f, 0x4b),
};

static void connected(struct bt_conn *conn, uint8_t err)
{
    if (err) {
        printk("Connection failed: 0x%02x\n", err);
        return;
    }
    printk("Client connected to KoalaByte Blue lab peripheral\n");
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

    printk("KoalaByte Blue nRF52840 DK lab peripheral booting\n");
    printk("Scope: owned hardware and authorized lab testing only\n");

    err = bt_enable(NULL);
    if (err) {
        printk("Bluetooth init failed: %d\n", err);
        return err;
    }

    err = bt_le_adv_start(BT_LE_ADV_CONN_NAME, ad, ARRAY_SIZE(ad), sd, ARRAY_SIZE(sd));
    if (err) {
        printk("Advertising failed to start: %d\n", err);
        return err;
    }

    printk("Advertising as %s\n", DEVICE_NAME);
    printk("GATT status characteristic is read-only\n");

    while (true) {
        k_sleep(K_SECONDS(10));
        printk("KoalaByte Blue lab peripheral alive\n");
    }

    return 0;
}
