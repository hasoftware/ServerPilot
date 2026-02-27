#!/bin/bash
# Control Server Web GUI - Quick Install Script for Ubuntu Server
set -e

INSTALL_DIR="/opt/control-server-web-gui"
PORT=1206
SERVICE_USER="www-data"

echo "=== Control Server Web GUI - Install ==="

# Check root
if [ "$EUID" -ne 0 ]; then
  echo "Chạy với quyền root: sudo bash install.sh"
  exit 1
fi

# Install system deps
apt-get update
apt-get install -y python3 python3-venv python3-pip ufw

# Get project dir FIRST (before changing directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Create install dir and copy project
mkdir -p "$INSTALL_DIR"
cp -r "$PROJECT_DIR"/* "$INSTALL_DIR/" 2>/dev/null || true

# Remove copied venv if any, then create fresh
rm -rf "$INSTALL_DIR/venv"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# Create data & logs
mkdir -p "$INSTALL_DIR/data" "$INSTALL_DIR/logs"
chown -R $SERVICE_USER:$SERVICE_USER "$INSTALL_DIR"

# Create .env if not exists (TTYD không cần TTYD_URL - terminal qua proxy trong panel)
if [ ! -f "$INSTALL_DIR/.env" ]; then
  cat > "$INSTALL_DIR/.env" << EOF
HOST=0.0.0.0
PORT=$PORT
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=sqlite+aiosqlite:///$INSTALL_DIR/data/control_server.db
LOG_DIR=$INSTALL_DIR/logs
MAX_LOG_SIZE_MB=10
LOG_RETENTION_DAYS=30
EOF
  chown $SERVICE_USER:$SERVICE_USER "$INSTALL_DIR/.env"
fi

# Install systemd service (chỉ panel, không ttyd)
cp "$INSTALL_DIR/systemd/control-server-web-gui.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable control-server-web-gui
systemctl start control-server-web-gui

# Firewall (chỉ mở port panel, KHÔNG mở 7681 - terminal đi qua proxy trong panel)
ufw allow $PORT/tcp 2>/dev/null || true
ufw --force enable 2>/dev/null || true

echo ""
echo "=== Cài đặt xong ==="
echo "Truy cập: http://<server-ip>:$PORT"
echo "Username: Admin"
echo "Password: Admin"
echo "Lần đầu đăng nhập: đổi mật khẩu và bật 2FA."
echo ""
echo "VNC Viewer: Bạn tự cài VNC server + websockify, cấu hình VNC_WS_URL trong .env"
echo "  ví dụ: apt install tigervnc-standalone-server; pip install websockify"
echo "  websockify 6080 localhost:5901"
echo "  Thêm vào .env: VNC_WS_URL=ws://localhost:6080"
echo ""
echo "systemctl status control-server-web-gui  # Trạng thái panel"
