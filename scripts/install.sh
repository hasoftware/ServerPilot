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

# Install system deps (ttyd for Web Terminal)
apt-get update
apt-get install -y python3 python3-venv python3-pip ufw
# ttyd for Web Terminal (universe repo)
apt-get install -y software-properties-common 2>/dev/null || true
add-apt-repository -y universe 2>/dev/null || true
apt-get install -y ttyd 2>/dev/null || echo "Bỏ qua ttyd - cài thủ công: sudo apt install ttyd"

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

# Detect server IP for TTYD_URL
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

# Create .env if not exists
if [ ! -f "$INSTALL_DIR/.env" ]; then
  cat > "$INSTALL_DIR/.env" << EOF
HOST=0.0.0.0
PORT=$PORT
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=sqlite+aiosqlite:///$INSTALL_DIR/data/control_server.db
LOG_DIR=$INSTALL_DIR/logs
MAX_LOG_SIZE_MB=10
LOG_RETENTION_DAYS=30
TTYD_URL=http://${SERVER_IP}:7681
EOF
  chown $SERVICE_USER:$SERVICE_USER "$INSTALL_DIR/.env"
else
  # Ensure TTYD_URL exists in .env
  if ! grep -q "^TTYD_URL=" "$INSTALL_DIR/.env" 2>/dev/null; then
    echo "TTYD_URL=http://${SERVER_IP}:7681" >> "$INSTALL_DIR/.env"
  fi
fi

# Install systemd services
cp "$INSTALL_DIR/systemd/control-server-web-gui.service" /etc/systemd/system/
TTYD_BIN=$(which ttyd 2>/dev/null || echo "/usr/bin/ttyd")
sed "s|ExecStart=.*|ExecStart=$TTYD_BIN -p 7681 -i 0.0.0.0 /bin/bash|" "$INSTALL_DIR/systemd/control-server-ttyd.service" > /etc/systemd/system/control-server-ttyd.service
systemctl daemon-reload
systemctl enable control-server-web-gui control-server-ttyd
systemctl start control-server-web-gui control-server-ttyd

# Firewall
ufw allow $PORT/tcp 2>/dev/null || true
ufw allow 7681/tcp 2>/dev/null || true
ufw --force enable 2>/dev/null || true

echo ""
echo "=== Cài đặt xong ==="
echo "Truy cập: http://<server-ip>:$PORT"
echo "Username: Admin"
echo "Password: Admin"
echo "Lần đầu đăng nhập: đổi mật khẩu và bật 2FA."
echo ""
echo "systemctl status control-server-web-gui  # Trạng thái panel"
echo "systemctl status control-server-ttyd     # Trạng thái terminal"
