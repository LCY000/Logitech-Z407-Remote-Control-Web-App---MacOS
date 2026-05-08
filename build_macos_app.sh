#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

if [ "${EUID:-$(id -u)}" -eq 0 ]; then
  echo "Do not build the macOS app with sudo."
  exit 1
fi

if [ ! -d venv ]; then
  python3 -m venv venv
fi

source venv/bin/activate

python -m pip install -r requirements.txt -r requirements-dev.txt

BUILD_ROOT=".pyinstaller"
DIST_ROOT="release"
export PYINSTALLER_CONFIG_DIR="${BUILD_ROOT}/config"

rm -rf "${BUILD_ROOT}" "${DIST_ROOT}"
mkdir -p "${PYINSTALLER_CONFIG_DIR}"

pyinstaller \
  --noconfirm \
  --clean \
  --distpath "${DIST_ROOT}" \
  --workpath "${BUILD_ROOT}/build" \
  Logitech_Z407_MacOS.spec

echo
echo "Build complete:"
echo "  ${DIST_ROOT}/Logitech Z407 Remote Control.app"
