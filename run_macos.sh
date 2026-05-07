#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d venv ]; then
  python3 -m venv venv
fi

source venv/bin/activate

pip install -r requirements.txt

PORT="${Z407_PORT:-8765}"
URL="http://127.0.0.1:${PORT}"

echo "Starting Logitech Z407 Remote Control Web App..."
echo "Local URL: ${URL}"
echo "LAN access: run this script with --lan"

if command -v open >/dev/null 2>&1; then
  (sleep 2 && open "${URL}") &
fi

python app.py --port "${PORT}" "$@"
