__version__ = "0.13.0"

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
except Exception:
    # Music support is optional at import time; a missing service or user config
    # must never prevent the menu, voice bridge, or diagnostics from starting.
    pass
