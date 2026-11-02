#!/usr/bin/env bash
set -e
echo "=== NVM Panel setup ==="
if ! command -v python3 >/dev/null; then
  echo "Installing python3..."; apt update && apt install -y python3 python3-venv python3-pip
fi
cd "$(dirname "$0")"
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
mkdir -p uploads instances
chmod +x scripts/*.sh 2>/dev/null || true
echo "Starting NVM Panel on http://0.0.0.0:6767"
echo "Default admin login: admin / admin123  (change it after first login)"
./venv/bin/python app.py
