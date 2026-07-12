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
except Exception:
    # Optional OBD-II/read-only menu support must not block core package imports.
    pass
