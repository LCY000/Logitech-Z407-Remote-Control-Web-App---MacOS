#!/bin/bash
# Builds "Logitech Z407 Remote Control.app" and a versioned zip ready for GitHub Releases.
set -euo pipefail

cd "$(dirname "$0")"

if [ "${EUID:-$(id -u)}" -eq 0 ]; then
  echo "Do not build the macOS app with sudo."
  exit 1
fi

if [ ! -d venv ] || [ ! -x venv/bin/python ]; then
  python3 -m venv venv
fi

source venv/bin/activate

if ! command -v python >/dev/null 2>&1; then
  deactivate 2>/dev/null || true
  python3 -m venv --clear venv
  source venv/bin/activate
fi

python -m pip install --quiet -r requirements.txt -r requirements-dev.txt

# Never package a build that fails its own tests.
python -m pytest -q

APP_NAME="Logitech Z407 Remote Control"
VERSION="$(python -c 'from z407_version import __version__; print(__version__)')"
ARCH="$(python -c 'import platform; print(platform.machine())')"
BUILD_ROOT=".pyinstaller"
DIST_ROOT="release"
APP_PATH="${DIST_ROOT}/${APP_NAME}.app"
ZIP_PATH="${DIST_ROOT}/Logitech-Z407-Remote-Control-v${VERSION}-macOS-${ARCH}.zip"
export PYINSTALLER_CONFIG_DIR="${BUILD_ROOT}/config"

# Only clear this build's own outputs; zips of earlier versions in release/ are kept.
rm -rf "${BUILD_ROOT}" "${APP_PATH}" "${DIST_ROOT:?}/${APP_NAME}" "${ZIP_PATH}"
mkdir -p "${PYINSTALLER_CONFIG_DIR}" "${DIST_ROOT}"

pyinstaller \
  --noconfirm \
  --clean \
  --log-level WARN \
  --distpath "${DIST_ROOT}" \
  --workpath "${BUILD_ROOT}/build" \
  Logitech_Z407_MacOS.spec

# PyInstaller also leaves the unbundled folder next to the .app; only the .app is needed.
rm -rf "${DIST_ROOT:?}/${APP_NAME}"

# Clear extended attributes, then re-sign ad hoc so the bundle's signature is consistent.
xattr -cr "${APP_PATH}" 2>/dev/null || true
codesign --force --deep --sign - "${APP_PATH}"
codesign --verify --deep --strict "${APP_PATH}"

# ditto keeps symlinks and the code signature intact (plain `zip` breaks app bundles).
ditto -c -k --sequesterRsrc --keepParent "${APP_PATH}" "${ZIP_PATH}"

echo
echo "Build complete (v${VERSION}, ${ARCH}):"
echo "  ${APP_PATH}"
echo "  ${ZIP_PATH}"
