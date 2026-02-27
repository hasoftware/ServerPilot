#!/bin/bash
# Reset database - tạo lại user Admin mặc định (Admin/Admin)
# Chạy: sudo INSTALL_DIR=/opt/control-server-web-gui bash scripts/reset_db.sh
# Hoặc từ thư mục cài đặt: sudo bash scripts/reset_db.sh

set -e
INSTALL_DIR="${INSTALL_DIR:-/opt/control-server-web-gui}"

echo "Dừng service..."
sudo systemctl stop control-server-web-gui 2>/dev/null || true

echo "Xóa database..."
rm -f "$INSTALL_DIR/data/control_server.db"

echo "Khởi động lại service..."
sudo systemctl start control-server-web-gui

echo "Xong. Đăng nhập với Admin/Admin"
