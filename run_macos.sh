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

for arg in "$@"; do
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
    --lan)
      LAN_MODE="true"
      ;;
  esac
done

URL="http://127.0.0.1:${PORT}"

echo "Starting Logitech Z407 Remote Control Web App..."
echo "Local URL: ${URL}"
if [ "${LAN_MODE}" = "true" ]; then
  echo "LAN access enabled."
else
  echo "LAN access: run this script with --lan"
fi

if command -v open >/dev/null 2>&1; then
  (sleep 2 && open "${URL}") &
fi

python app.py --port "${PORT}" "$@"
