#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REV="${NCS_REVISION:-v2.9.0}"
SDK_VER="${ZEPHYR_SDK_VERSION:-0.17.0}"
export NCS_WORKSPACE="${NCS_WORKSPACE:-${REPO_ROOT}/third_party/ncs}"
export ZEPHYR_SDK_INSTALL_DIR="${ZEPHYR_SDK_INSTALL_DIR:-${REPO_ROOT}/third_party/zephyr-sdk-${SDK_VER}}"
export NCS_REVISION="${REV}"
export ZEPHYR_SDK_VERSION="${SDK_VER}"
export INSTALL_NCS_TOOLCHAIN="${INSTALL_NCS_TOOLCHAIN:-auto}"
export STRICT_NCS_TOOLCHAIN="${STRICT_NCS_TOOLCHAIN:-1}"

mkdir -p "${REPO_ROOT}/third_party"

echo "Preparing local NCS workspace"
echo "NCS_WORKSPACE=${NCS_WORKSPACE}"
echo "NCS_REVISION=${NCS_REVISION}"
echo "ZEPHYR_SDK_INSTALL_DIR=${ZEPHYR_SDK_INSTALL_DIR}"

bash "${REPO_ROOT}/scripts/setup_nrf_connect_sdk_toolchain.sh" "$@"
