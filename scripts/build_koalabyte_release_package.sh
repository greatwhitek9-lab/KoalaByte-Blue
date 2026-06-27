#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${KOALABYTE_RELEASE_DIR:-${REPO_ROOT}/dist}"
PKG_DIR="${OUT_DIR}/KoalaByte-Blue"
ZIP_PATH="${OUT_DIR}/KoalaByte-Blue-install-package.zip"
rm -rf "${PKG_DIR}"
mkdir -p "${PKG_DIR}" "${OUT_DIR}"
cd "${REPO_ROOT}"

items=(README.md install.sh scripts pi-companion firmware docs production systemd udev logrotate version training .github)
for item in "${items[@]}"; do
  [[ -e "${item}" ]] && cp -a "${item}" "${PKG_DIR}/"
done

if command -v zip >/dev/null 2>&1; then
  (cd "${OUT_DIR}" && zip -r "${ZIP_PATH}" KoalaByte-Blue >/dev/null)
  echo "Built release package: ${ZIP_PATH}"
else
  TAR_PATH="${OUT_DIR}/KoalaByte-Blue-install-package.tar.gz"
  (cd "${OUT_DIR}" && tar -czf "${TAR_PATH}" KoalaByte-Blue)
  echo "Built release package: ${TAR_PATH}"
fi
