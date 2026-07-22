Import("env")

from pathlib import Path

project = Path(env.subst("$PROJECT_DIR"))
# platformio.ini excludes integrated_main.cpp. Patch the generated wake-session
# translation unit that is actually compiled and flashed.
path = project / "src" / "integrated_main_wake_session.cpp"
text = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"guarded BLE failover patch expected exactly one {label} anchor, found {count}"
        )
    text = text.replace(old, new, 1)


replace_once(
    """bool bleReady = false;
bool wifiStarted = false;
""",
    """bool bleReady = false;
bool bleFallbackRequested = false;
bool bleInitAttempted = false;
bool bleQuarantined = false;
char bleRole[32] = "standby";
bool wifiStarted = false;
""",
    "BLE role state",
)

replace_once(
    """  doc["ble_ready"] = bleReady;
  doc["audio_ready"] = dualEyeAudioReady();
""",
    """  doc["ble_ready"] = bleReady;
  doc["ble_role"] = bleRole;
  doc["ble_fallback_requested"] = bleFallbackRequested;
  doc["ble_quarantined"] = bleQuarantined;
  doc["audio_ready"] = dualEyeAudioReady();
""",
    "node status BLE role fields",
)

replace_once(
    """class SeenCallbacks : public NimBLEAdvertisedDeviceCallbacks {
""",
    """void writeBleGuard(bool pending, bool quarantined) {
  prefs.begin(KOALA_BLE_NVS_NAMESPACE, false);
  prefs.putBool("pending", pending);
  prefs.putBool("quarantine", quarantined);
  prefs.end();
}

void loadBleCrashGuard() {
  prefs.begin(KOALA_BLE_NVS_NAMESPACE, true);
  const bool pending = prefs.getBool("pending", false);
  bleQuarantined = prefs.getBool("quarantine", false);
  prefs.end();
  if (pending) {
    // A reset before BLE init cleared its pending flag indicates the controller
    // startup did not complete. Quarantine prevents a persistent boot loop.
    bleQuarantined = true;
    writeBleGuard(false, true);
    copyText(bleRole, sizeof(bleRole), "quarantined");
  }
}

void emitBleRoleStatus(const char *reason) {
  StaticJsonDocument<384> doc;
  doc["type"] = "ble_role_status";
  doc["device"] = "esp32-s3-dualeye";
  doc["role"] = bleRole;
  doc["ready"] = bleReady;
  doc["requested"] = bleFallbackRequested;
  doc["quarantined"] = bleQuarantined;
  doc["reason"] = reason ? reason : "status";
  doc["heltec_primary"] = true;
  doc["crash_guarded"] = true;
  sendPayload(doc);
}

class SeenCallbacks : public NimBLEAdvertisedDeviceCallbacks {
""",
    "BLE crash guard helpers",
)

replace_once(
    """    doc["transport"] = "esp32-nimble";
    doc["face_sync"] = false;
""",
    """    doc["transport"] = "esp32-nimble";
    doc["role"] = bleRole;
    doc["heltec_primary"] = true;
    doc["fallback_active"] = bleFallbackRequested;
    doc["face_sync"] = false;
""",
    "BLE observation role metadata",
)

replace_once(
    """void setupBle() {
  NimBLEDevice::init(BLE_DEVICE_NAME);
  NimBLEScan *scan = NimBLEDevice::getScan();
  scan->setAdvertisedDeviceCallbacks(new SeenCallbacks(), true);
  scan->setActiveScan(false);
  scan->setInterval(160);
  scan->setWindow(80);
  NimBLEAdvertising *advertising = NimBLEDevice::getAdvertising();
  advertising->addServiceUUID(BLE_NODE_SERVICE_UUID);
  advertising->setScanResponse(true);
  advertising->start();
  bleReady = true;
  emitStatus("ble_node_ready_pi_coordinates_heltec_expression_sync");
}
""",
    """void setupBle() {
#if ENABLE_ESP32_BLE_FAILOVER
  if (bleReady || bleInitAttempted || !bleFallbackRequested) return;
  if (bleQuarantined) {
    copyText(bleRole, sizeof(bleRole), "quarantined");
    emitBleRoleStatus("controller_start_quarantined_after_previous_reset");
    return;
  }
  if (ESP.getFreeHeap() < SUBSYSTEM_READY_MIN_FREE_HEAP) {
    emitBleRoleStatus("insufficient_heap_for_guarded_ble_fallback");
    return;
  }

  bleInitAttempted = true;
  // Set the persistent marker before controller startup. If startup panics and
  // reboots, the next boot sees this marker and refuses to retry automatically.
  writeBleGuard(true, false);
  NimBLEDevice::init(BLE_DEVICE_NAME);
  NimBLEScan *scan = NimBLEDevice::getScan();
  scan->setAdvertisedDeviceCallbacks(new SeenCallbacks(), true);
  scan->setActiveScan(false);
  scan->setInterval(160);
  scan->setWindow(80);
  NimBLEAdvertising *advertising = NimBLEDevice::getAdvertising();
  advertising->addServiceUUID(BLE_NODE_SERVICE_UUID);
  advertising->setScanResponse(true);
  advertising->start();
  bleReady = true;
  writeBleGuard(false, false);
  copyText(bleRole, sizeof(bleRole), "heltec_fallback_ble_node");
  emitBleRoleStatus("guarded_ble_fallback_ready");
#else
  emitBleRoleStatus("firmware_ble_fallback_disabled");
#endif
}
""",
    "guarded BLE setup",
)

replace_once(
    """void bleScanTask(void *) {
  bleScanBusy = true;
  NimBLEScan *scan = NimBLEDevice::getScan();
  scan->start(BLE_SCAN_SECONDS, false);
  scan->clearResults();
  bleScanBusy = false;
  vTaskDelete(nullptr);
}
""",
    """void bleScanTask(void *) {
  bleScanBusy = true;
  if (bleReady && bleFallbackRequested) {
    NimBLEScan *scan = NimBLEDevice::getScan();
    scan->start(BLE_SCAN_SECONDS, false);
    scan->clearResults();
  }
  bleScanBusy = false;
  vTaskDelete(nullptr);
}

void handleBleRole(JsonDocument &doc) {
  const char *role = doc["role"] | "standby";
  const char *reason = doc["reason"] | "pi_role_election";

  if (!strcmp(role, "ble_recovery_clear")) {
    bleQuarantined = false;
    bleInitAttempted = false;
    bleFallbackRequested = false;
    copyText(bleRole, sizeof(bleRole), "standby");
    writeBleGuard(false, false);
    emitBleRoleStatus("operator_cleared_ble_quarantine");
    return;
  }

  if (!strcmp(role, "heltec_fallback_ble_node")) {
    bleFallbackRequested = true;
    copyText(bleRole, sizeof(bleRole), role);
    setupBle();
    if (bleReady && !bleScanBusy && !dualEyeAudioBusy()) {
      xTaskCreatePinnedToCore(bleScanTask, "BleFailoverScan", 4096, nullptr, 1,
                              nullptr, 0);
    } else if (!bleReady) {
      emitBleRoleStatus(reason);
    }
    return;
  }

  bleFallbackRequested = false;
  copyText(bleRole, sizeof(bleRole), "standby");
  if (bleReady) {
    NimBLEDevice::getScan()->stop();
    NimBLEDevice::getAdvertising()->stop();
  }
  emitBleRoleStatus(reason);
}
""",
    "BLE role handler",
)

# Insert the BLE role commands immediately before scan_nodes. The node-status
# branch has changed indentation and gained aliases over time, so using it as a
# multi-line anchor made this otherwise unrelated patch brittle.
replace_once(
    """  } else if (!strcmp(type, "scan_nodes")) {
""",
    """  } else if (!strcmp(type, "ble_role")) {
    handleBleRole(doc);
  } else if (!strcmp(type, "ble_recovery_clear")) {
    StaticJsonDocument<128> clearDoc;
    clearDoc["role"] = "ble_recovery_clear";
    handleBleRole(clearDoc);
  } else if (!strcmp(type, "scan_nodes")) {
""",
    "BLE role command routing before scan_nodes",
)

replace_once(
    """  if (!bleReady && now >= SUBSYSTEM_BLE_START_MS &&
      ESP.getFreeHeap() >= SUBSYSTEM_READY_MIN_FREE_HEAP) {
    setupBle();
  }
""",
    """  if (bleFallbackRequested && !bleReady && now >= SUBSYSTEM_BLE_START_MS &&
      ESP.getFreeHeap() >= SUBSYSTEM_READY_MIN_FREE_HEAP) {
    setupBle();
  }
""",
    "prevent unrequested BLE staging",
)

replace_once(
    """  loadWifiConfig();
  showIdleEyes();
""",
    """  loadWifiConfig();
  loadBleCrashGuard();
  showIdleEyes();
""",
    "boot BLE crash guard load",
)

path.write_text(text, encoding="utf-8")
print(f"Patched guarded Pi-to-ESP32 BLE failover in compiled source: {path}")
