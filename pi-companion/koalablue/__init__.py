__version__ = "0.13.1"

try:
    from .killerkoala_runtime_limits import install_killerkoala_runtime_limits

    install_killerkoala_runtime_limits()
except Exception:
    # TinyLlama remains optional. The phrase engine and fixed local responses must
    # still load if Ollama/httpx is unavailable during a partial installation.
    pass

try:
    from .runtime_log_hardening import install_runtime_log_hardening

    install_runtime_log_hardening()
except Exception:
    # Logging hardening is fail-soft at import time, but production entrypoints
    # explicitly import the same package and source validation checks the module.
    pass

# T114 menu, status, scan, and bounded-lab TX actions must never compete with the
# BLE/GNSS service for the Heltec tty. This is a required runtime safety layer;
# import failures intentionally fail package validation rather than reverting to
# direct serial access. Explicit maintenance mode remains available through
# KOALABYTE_ALLOW_DIRECT_HELTEC_SERIAL=1 after the owner service is stopped.
from . import t114_bluez as _t114_bluez
from .t114_runtime_broker import install as _install_t114_runtime_broker

_install_t114_runtime_broker(_t114_bluez)
del _install_t114_runtime_broker

# Koala Kombat passive survey actions use the same two serial owners and bounded
# event ledgers. The legacy direct-open helper remains in the source for explicit
# offline maintenance, but production imports always replace its runtime route.
from . import koala_kombat_kruisin as _koala_kombat_kruisin
from .koala_kombat_runtime_broker import install as _install_koala_kombat_broker

_install_koala_kombat_broker(_koala_kombat_kruisin)
del _install_koala_kombat_broker

try:
    from .greatwhite_reef import install_menu_catalog

    install_menu_catalog()
except Exception:
    # Menu extensions must never prevent core package imports.
    pass

try:
    from .twocan_read_only import install_menu_catalog as install_twocan_read_only_menu

    install_twocan_read_only_menu()
    from . import menu_catalog as _menu_catalog

    # This command intentionally appears in Koala Kan and the nested TwoCan
    # menu. Keep the same visible label so duplicate-route validation recognizes
    # it as one shared safety-note action rather than two conflicting actions.
    for _row in _menu_catalog.SUBMENU_ITEMS.get("twocan_read_only", []):
        if str(_row.get("command", "")) == "twocan_clear_codes_safety_note":
            _row["label"] = "TwoCan Clear Codes Safety Note"
except Exception:
    # Optional OBD-II/read-only menu support must not block core package imports.
    pass

try:
    from . import mopidy_player as _mopidy_player
    from .mopidy_player import install_menu_catalog as install_music_player_menu

    # Lyrebird is the KoalaByte product name. Mopidy remains the stable internal
    # engine, service, RPC API, configuration format, and command namespace.
    _mopidy_player.GROUP_NAME = "Lyrebird"
    install_music_player_menu()

    from .lyrebird_brand import install_lyrebird_brand

    install_lyrebird_brand()

    from .lyrebird_browser import install_lyrebird_browser

    install_lyrebird_browser()

    from .lyrebird_voice_alias import install_lyrebird_voice_alias

    install_lyrebird_voice_alias()
except Exception:
    # Music support is optional at import time; a missing service or user config
    # must never prevent the menu, voice bridge, or diagnostics from starting.
    pass

try:
    from .rf_ble_lab_gates import install_rf_ble_lab_gates

    install_rf_ble_lab_gates()
except Exception:
    # RF/BLE lab routing must fail closed: if the optional routing layer cannot
    # load, the existing passive behavior remains in effect.
    pass

try:
    from .menu_actionability import install_menu_actionability

    # Install last so it audits the final composed GreatWhite, TwoCan, Lyrebird,
    # RF/BLE, core menu and UI dispatch chain rather than only the base runner.
    install_menu_actionability()
except Exception:
    # Core imports remain available, but CI treats a missing actionability layer
    # as a deployment failure before the one-shot is considered flash-ready.
    pass
