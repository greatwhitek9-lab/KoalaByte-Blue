#!/usr/bin/env python3
from koalablue import boomerang


if __name__ == "__main__":
    boomerang.KILLERKOALA_BOOMERANG_ALERTS["boomerang_start"] = "BOOMerang!"
    raise SystemExit(boomerang.run_cli())
