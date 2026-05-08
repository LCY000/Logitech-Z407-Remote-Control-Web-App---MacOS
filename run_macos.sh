#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d venv ]; then
  python3 -m venv venv
fi

source venv/bin/activate

pip install -r requirements.txt

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
