from __future__ import annotations

import getpass
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Optional

PASSWORD_FILE = Path("logs/security/location_password.json")
UNLOCK_ENV = "KOALABYTE_LOCATION_UNLOCKED"
PASSWORD_ENV = "KOALABYTE_LOCATION_PASSWORD"
PASSWORD_HASH_ENV = "KOALABYTE_LOCATION_PASSWORD_SHA256"


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _load_record(path: Path = PASSWORD_FILE) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def password_exists(path: Path = PASSWORD_FILE) -> bool:
    return bool(os.environ.get(PASSWORD_HASH_ENV) or os.environ.get(PASSWORD_ENV) or _load_record(path).get("password_sha256"))


def create_password(password: str, path: Path = PASSWORD_FILE) -> dict[str, object]:
    if len(password) < 6:
        raise ValueError("location password must be at least 6 characters")
    record = {
        "password_sha256": _hash_password(password),
        "created_at": time.time(),
        "scope": "password for local authorized location-gated actions only",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    try:
        path.chmod(0o600)
    except Exception:
        pass
    return {"created": True, "path": str(path), "scope": record["scope"]}


def verify_password(password: str, path: Path = PASSWORD_FILE) -> bool:
    env_hash = os.environ.get(PASSWORD_HASH_ENV, "").strip().lower()
    if env_hash:
        return hmac.compare_digest(_hash_password(password), env_hash)
    env_plain = os.environ.get(PASSWORD_ENV)
    if env_plain:
        return hmac.compare_digest(password, env_plain)
    record = _load_record(path)
    saved_hash = str(record.get("password_sha256", "")).strip().lower()
    if saved_hash:
        return hmac.compare_digest(_hash_password(password), saved_hash)
    return False


def setup_password_interactive(path: Path = PASSWORD_FILE, *, force: bool = False) -> dict[str, object]:
    if password_exists(path) and not force:
        return {"created": False, "path": str(path), "status": "already_configured"}
    print("KoalaByte protected actions password setup")
    print("Create the local password used to unlock protected actions such as scoped GNSS location fill.")
    while True:
        first = getpass.getpass("Create protected-actions password: ")
        second = getpass.getpass("Confirm protected-actions password: ")
        if first != second:
            print("Passwords did not match. Try again.")
            continue
        return create_password(first, path)


def unlock_interactive(path: Path = PASSWORD_FILE) -> bool:
    supplied = getpass.getpass("KoalaByte protected-actions password: ")
    if verify_password(supplied, path):
        os.environ[UNLOCK_ENV] = "1"
        os.environ["KOALABYTE_AUTHORIZED_LOCATION_LOGGING"] = "1"
        return True
    return False


def ensure_unlocked(password: Optional[str] = None, *, prompt: bool = False, path: Path = PASSWORD_FILE) -> bool:
    if os.environ.get(UNLOCK_ENV) in {"1", "true", "TRUE", "yes", "YES"}:
        return True
    if not password_exists(path):
        return False
    if password is not None:
        ok = verify_password(password, path)
        if ok:
            os.environ[UNLOCK_ENV] = "1"
            os.environ["KOALABYTE_AUTHORIZED_LOCATION_LOGGING"] = "1"
        return ok
    if prompt:
        return unlock_interactive(path)
    return False


def run_cli(argv: Optional[list[str]] = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="KoalaByte protected actions password setup/unlock")
    sub = parser.add_subparsers(dest="command", required=True)
    setup = sub.add_parser("setup", help="Create the password on first startup")
    setup.add_argument("--force", action="store_true")
    sub.add_parser("status", help="Show whether password is configured and session is unlocked")
    sub.add_parser("unlock", help="Prompt for the password and unlock this process")
    args = parser.parse_args(argv)
    if args.command == "setup":
        print(json.dumps(setup_password_interactive(force=args.force), indent=2, sort_keys=True))
        return 0
    if args.command == "status":
        print(json.dumps({"configured": password_exists(), "unlocked": os.environ.get(UNLOCK_ENV) in {"1", "true", "TRUE", "yes", "YES"}, "path": str(PASSWORD_FILE)}, indent=2, sort_keys=True))
        return 0
    if args.command == "unlock":
        ok = unlock_interactive()
        print(json.dumps({"unlocked": ok}, indent=2, sort_keys=True))
        return 0 if ok else 2
    return 1
