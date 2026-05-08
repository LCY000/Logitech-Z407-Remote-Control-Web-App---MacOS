#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

if [ "${EUID:-$(id -u)}" -eq 0 ]; then
  echo "Do not run this helper with sudo."
  echo "macOS Bluetooth and Accessibility permissions are granted to your user session, not a root shell."
  echo "Run: ./run_macos.sh"
  echo "If venv permissions were changed by sudo, fix them with:"
  echo "  sudo chown -R ${SUDO_USER:-$USER}:staff venv"
  exit 1
fi

if [ ! -d venv ]; then
  python3 -m venv venv
fi

if [ ! -w venv ]; then
  echo "The local venv is not writable by the current user."
  echo "This usually happens after running the helper with sudo."
  echo "Fix it with:"
  echo "  sudo chown -R $USER:staff venv"
  exit 1
fi

source venv/bin/activate

pip install -r requirements.txt

if [ "${1:-}" = "--debug-scan" ]; then
  shift
  python debug_ble_scan.py "$@"
  exit $?
fi

PORT="${Z407_PORT:-8765}"
LAN_MODE="false"
PREV_WAS_PORT="false"
PREV_WAS_IP="false"
EXPLICIT_IP=""

is_loopback_ip() {
  case "${1}" in
    localhost|127|127.*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

for arg in "$@"; do
  if [ "${PREV_WAS_IP}" = "true" ]; then
    EXPLICIT_IP="${arg}"
    PREV_WAS_IP="false"
    continue
  fi

  if [ "${PREV_WAS_PORT}" = "true" ]; then
    PORT="${arg}"
    PREV_WAS_PORT="false"
    continue
  fi

  case "${arg}" in
    --port)
      PREV_WAS_PORT="true"
      ;;
    --port=*)
      PORT="${arg#--port=}"
      ;;
    --ip)
      PREV_WAS_IP="true"
      ;;
    --ip=*)
      EXPLICIT_IP="${arg#--ip=}"
      ;;
    --lan)
      LAN_MODE="true"
      ;;
  esac
done

URL_HOST="127.0.0.1"
if [ -n "${EXPLICIT_IP}" ] && ! is_loopback_ip "${EXPLICIT_IP}"; then
  URL_HOST="${EXPLICIT_IP}"
  LAN_MODE="true"
fi

URL="http://${URL_HOST}:${PORT}"

echo "Starting Logitech Z407 Remote Control Web App..."
echo "Browser URL: ${URL}"
if [ "${LAN_MODE}" = "true" ]; then
  echo "LAN access enabled."
else
  echo "LAN access: run this script with --lan"
fi

if command -v open >/dev/null 2>&1; then
  (sleep 2 && open "${URL}") &
fi

python app.py --port "${PORT}" "$@"
