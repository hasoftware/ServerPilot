# Control Server Web GUI

Web Management Panel chạy trên Ubuntu Server, dùng để quản lý server và các chức năng hệ thống (Cronjob, v.v.).

- **Port**: 1206
- **Stack**: FastAPI + SQLite + APScheduler
- **Auth**: Username/Password + 2FA (TOTP)

## Tính năng

- **Dashboard**: Uptime, CPU, RAM, Disk, số cronjob active
- **Cronjob Manager**: Thêm/sửa/xóa cronjob, CURL/WGET, cron expression, bật/tắt log
- **Authentication**: Admin/Admin mặc định, bắt buộc đổi mật khẩu + 2FA lần đầu
- **systemd**: Tự khởi động lại khi reboot/crash, load cronjob từ DB

## Cài đặt nhanh (Ubuntu Server)

### 1. Clone repo

```bash
git clone https://github.com/hasoftware/ServerPilot.git
cd ServerPilot
```

### 2. Chạy script cài đặt

```bash
sudo bash scripts/install.sh
```

### 3. Mở port 1206

```bash
sudo ufw allow 1206/tcp
sudo ufw reload
```

### 4. Truy cập

- URL: `http://<server-ip>:1206`
- Username: `Admin`
- Password: `Admin`
- Lần đầu: đổi mật khẩu và bật 2FA (Google Authenticator)

## Cài đặt thủ công

### Yêu cầu

- Python 3.10+
- Ubuntu Server

### Bước 1: Clone & cài dependencies

```bash
git clone https://github.com/YOUR_USER/Control_Server_Web_GUI.git
cd Control_Server_Web_GUI
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Bước 2: Cấu hình .env

```bash
cp .env.example .env
# Chỉnh sửa .env: SECRET_KEY, PORT (mặc định 1206)
```

### Bước 3: Chạy thử

```bash
python run.py
# Hoặc: uvicorn app.main:app --host 0.0.0.0 --port 1206
```

### Bước 4: systemd (production)

```bash
# Copy service file
sudo cp systemd/control-server-web-gui.service /etc/systemd/system/

# Chỉnh sửa WorkingDirectory và ExecStart nếu cài ở path khác
sudo nano /etc/systemd/system/control-server-web-gui.service

# Enable và start
sudo systemctl daemon-reload
sudo systemctl enable control-server-web-gui
sudo systemctl start control-server-web-gui
```

## Cấu trúc project

```
Control_Server_Web_GUI/
├── app/
│   ├── main.py           # FastAPI app
│   ├── config.py
│   ├── init_db.py        # Default Admin user
│   ├── auth/             # Login, 2FA, session
│   ├── database/         # SQLite, models
│   └── services/
│       ├── cronjob/      # Scheduler, executor
│       └── dashboard/    # Metrics API
├── templates/
├── static/
├── systemd/
├── scripts/
├── requirements.txt
└── run.py
```

## systemd service

File `systemd/control-server-web-gui.service`:

- `Restart=always` – tự khởi động lại khi crash
- `RestartSec=5` – đợi 5 giây trước khi restart
- `WantedBy=multi-user.target` – tự chạy khi boot

Khi khởi động:

- Load tất cả cronjob enabled từ DB
- Không duplicate, không mất cấu hình
- APScheduler chạy trong process, không dùng crontab hệ thống

## Cron expression

Format: `phút giờ ngày tháng thứ`

Ví dụ:

- `*/5 * * * *` – mỗi 5 phút
- `0 * * * *` – mỗi giờ
- `0 0 * * *` – mỗi ngày lúc 00:00

## Mở rộng

Code được thiết kế module hóa. Để thêm service mới:

1. Tạo `app/services/<tên_service>/`
2. Thêm routes, models nếu cần
3. Include router vào `app/main.py`
4. Thêm menu và trang UI tương ứng

## Xử lý lỗi

**Đăng nhập Admin/Admin báo sai:**

```bash
sudo systemctl stop control-server-web-gui
sudo rm -f /opt/control-server-web-gui/data/control_server.db
sudo systemctl start control-server-web-gui
```

Hoặc dùng script: `sudo bash scripts/reset_db.sh` (chạy từ thư mục project)

**Service crash do bcrypt:** Cài bcrypt 4.0.1:

```bash
sudo -u www-data /opt/control-server-web-gui/venv/bin/pip install "bcrypt==4.0.1"
sudo systemctl restart control-server-web-gui
```

## License

MIT
