# Authorized Lab Use Actions

KoalaByte Blue uses a defensive-only Research Lab action model. These actions replace old placeholder menu entries with safe, consent-gated workflows for owned hardware, lab devices, and written-scope assessments.

## Actions

| Action ID | Purpose | Output | XP |
|---|---|---|---:|
| `authorized_ble_inventory` | Build an inventory from passive BLE observations | Markdown inventory artifact | 10 |
| `gatt_readiness_checklist` | Prepare for an owned-device GATT review | Markdown checklist | 8 |
| `pairing_security_review` | Review pairing and access-control posture | Markdown review | 8 |
| `lab_beacon_plan` | Plan ESP32 lab beacon/peripheral simulation | Markdown plan | 10 |
| `packet_capture_notes` | Write safe nRF52840/Wireshark workflow notes | Markdown notes | 8 |
| `defensive_report` | Generate a defensive lab report template | Markdown report | 12 |
| `restricted_placeholder` | Locked reserved menu slot | No operational behavior | 0 |

## Authorization gate

Every lab action requires `authorized=True` when executed from code. If authorization is missing, the action returns:

```text
AUTH_REQUIRED
```

## Example

```python
from koalablue.authorized_lab_actions import AuthorizedLabActions

lab = AuthorizedLabActions()
result = lab.run("authorized_ble_inventory", authorized=True, context={"devices": []})
print(result.status, result.message, result.artifact_path)
```

## Boundaries

The action registry only creates checklists, plans, reports, passive inventories, and audit logs. Restricted menu slots remain non-operational.
