#!/bin/bash
# Cập nhật code (sau git pull) - copy vào /opt và restart
set -e

INSTALL_DIR="/opt/control-server-web-gui"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ "$EUID" -ne 0 ]; then
  echo "Chạy: sudo bash scripts/update.sh"
  exit 1
fi

echo "Cập nhật code từ $PROJECT_DIR -> $INSTALL_DIR"
cp -r "$PROJECT_DIR"/app "$PROJECT_DIR"/templates "$PROJECT_DIR"/static "$INSTALL_DIR/"
cp -r "$PROJECT_DIR"/scripts "$PROJECT_DIR"/systemd "$INSTALL_DIR/"
cp "$PROJECT_DIR"/*.py "$PROJECT_DIR"/requirements.txt "$INSTALL_DIR/" 2>/dev/null || true
cp "$INSTALL_DIR"/systemd/*.service /etc/systemd/system/
systemctl daemon-reload
systemctl restart control-server-web-gui
echo "Xong. Panel đã restart."
