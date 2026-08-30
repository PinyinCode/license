from datetime import datetime, timedelta
import json
import os
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
)
import requests

app = Flask(__name__)
app.secret_key = os.urandom(24)

DB_FILE = "devices.json"

# --- CẤU HÌNH GITHUB OAUTH ---
GITHUB_CLIENT_ID = "Ov23liD2PKCxgNkZfUj5"
GITHUB_CLIENT_SECRET = "158a74d6beed0ed201ad9a7c4a041738d3185eb6"
YOUR_GITHUB_USERNAME = "PinyinCode"

# Link file firmware .bin của bạn trên Render Static Site
DEFAULT_FIRMWARE_URL = "https://esp32-z1t9.onrender.com/xiaozhi.bin"
DEFAULT_LATEST_VERSION = "v1.1.0"


def load_db():
  if os.path.exists(DB_FILE):
    try:
      with open(DB_FILE, "r") as f:
        return json.load(f)
    except:
      return {}
  return {}


def save_db(data):
  with open(DB_FILE, "w") as f:
    json.dump(data, f, indent=4)


# --- GIAO DIỆN TRANG ĐĂNG NHẬP ---
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Đăng nhập - Quản lý OTA ESP32</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; background: #f4f7f6; display: flex; justify-content: center; align-items: center; height: 100vh; color: #333; }
        .login-card { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); text-align: center; width: 350px; }
        h2 { color: #007BFF; margin-bottom: 10px; }
        p { color: #666; font-size: 14px; margin-bottom: 25px; }
        .github-btn { background: #24292e; color: white; padding: 12px 20px; text-decoration: none; border-radius: 4px; display: inline-block; font-weight: bold; width: 100%; box-sizing: border-box; }
        .github-btn:hover { background: #2c3238; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>Quản Trị ESP32</h2>
        <p>Vui lòng xác thực tài khoản quản trị</p>
        <a href="/login/authorize" class="github-btn">Đăng nhập bằng GitHub</a>
    </div>
</body>
</html>
"""

# --- GIAO DIỆN TRANG QUẢN TRỊ ---
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Quản lý Bản quyền & OTA ESP32</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f4f7f6; color: #333; }
        .container { max-width: 950px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { display: flex; justify-content: space-between; align-items: center; }
        h2 { color: #007BFF; margin: 0; }
        .logout-btn { background: #dc3545; color: white; padding: 6px 12px; text-decoration: none; border-radius: 4px; font-size: 14px; }
        .logout-btn:hover { background: #c82333; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
        th { background: #007BFF; color: white; }
        input, select, button { padding: 8px; margin: 5px 0; border: 1px solid #ccc; border-radius: 4px; }
        button { background: #28a745; color: white; border: none; cursor: pointer; }
        button:hover { background: #218838; }
        .ota-btn { background: #17a2b8; padding: 6px 10px; font-size: 13px; border-radius: 4px; color: white; text-decoration: none; display: inline-block; }
        .ota-btn:hover { background: #138496; }
        .ota-active { background: #ffc107; color: #212529; font-weight: bold; }
        .form-group { background: #e9ecef; padding: 15px; border-radius: 6px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Quản lý Bản quyền & OTA ESP32</h2>
            <a href="/logout" class="logout-btn">Đăng xuất ({{ user }})</a>
        </div>
        <hr style="margin: 20px 0; border: 0; border-top: 1px solid #eee;">
        
        <div class="form-group">
            <h3>Thêm hoặc Cập nhật hạn thiết bị</h3>
            <form action="/admin/add" method="POST">
                <label>Địa chỉ MAC:</label><br>
                <input type="text" name="mac" placeholder="Ví dụ: 24:0A:C4:12:34:56" required style="width: 100%;"><br>
                <label>Ngày hết hạn cụ thể:</label><br>
                <input type="date" name="expiry_date" required style="width: 100%;"><br><br>
                <button type="submit">Lưu / Cập nhật</button>
            </form>
        </div>

        <h3>Danh sách thiết bị đã lưu</h3>
        <table>
            <tr>
                <th>Địa chỉ MAC</th>
                <th>Trạng thái</th>
                <th>Loại</th>
                <th>Ngày hết hạn</th>
                <th>Thao tác OTA</th>
            </tr>
            {% for mac, info in devices.items() %}
            <tr>
                <td><b>{{ mac }}</b></td>
                <td style="color: {{ 'green' if info.status == 'active' else 'red' }};">{{ info.status }}</td>
                <td>{{ 'Dùng thử (Trial)' if info.trial else 'Chính thức' }}</td>
                <td>{{ info.expires_at }}</td>
                <td>
                    {% if info.get('ota_pending', False) %}
                        <span class="ota-btn ota-active">Chờ cập nhật...</span>
                        <a href="/admin/cancel-ota/{{ mac }}" style="font-size:12px; color:red; margin-left: 5px;">Hủy</a>
                    {% else %}
                        <a href="/admin/trigger-ota/{{ mac }}" class="ota-btn">Cập nhật OTA</a>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""


@app.route("/")
def home():
  return "ESP32 License & OTA Server is running!"


@app.route("/login")
def login():
  if "user" in session:
    return redirect(url_for("admin_panel"))
  return render_template_string(LOGIN_HTML)


@app.route("/login/authorize")
def login_authorize():
  github_auth_url = (
      f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}"
  )
  return redirect(github_auth_url)


@app.route("/login/callback")
def callback():
  code = request.args.get("code")
  if not code:
    return "Đăng nhập thất bại từ GitHub!", 400

  token_url = "https://github.com/login/oauth/access_token"
  headers = {"Accept": "application/json"}
  data = {
      "client_id": GITHUB_CLIENT_ID,
      "client_secret": GITHUB_CLIENT_SECRET,
      "code": code,
  }
  response = requests.post(token_url, json=data, headers=headers)
  token_json = response.json()
  access_token = token_json.get("access_token")

  if not access_token:
    return "Không thể lấy Token xác thực từ GitHub!", 400

  user_url = "https://api.github.com/user"
  user_headers = {
      "Authorization": f"Bearer {access_token}",
      "Accept": "application/json",
  }
  user_response = requests.get(user_url, headers=user_headers)
  user_data = user_response.json()
  github_username = user_data.get("login")

  if (
      github_username
      and github_username.lower() == YOUR_GITHUB_USERNAME.lower()
  ):
    session["user"] = github_username
    return redirect(url_for("admin_panel"))
  else:
    return (
        f"Truy cập bị từ chối! Tài khoản GitHub ({github_username})"
        " không có quyền quản trị hệ thống này.",
        403,
    )


@app.route("/logout", methods=["GET", "POST"])
def logout():
  session.clear()
  return redirect(url_for("login"))


@app.route("/admin", methods=["GET"])
def admin_panel():
  if "user" not in session:
    return redirect(url_for("login"))

  devices = load_db()
  return render_template_string(
      ADMIN_HTML, devices=devices, user=session["user"]
  )


@app.route("/admin/add", methods=["POST"])
def admin_add():
  if "user" not in session:
    return redirect(url_for("login"))

  mac = request.form.get("mac")
  expiry_date_str = request.form.get("expiry_date")

  if mac and expiry_date_str:
    mac = mac.strip().upper()
    try:
      expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").replace(
          hour=23, minute=59, second=59
      )
      db = load_db()
      if mac in db:
        db[mac]["expires_at"] = expiry_date.isoformat()
        db[mac]["status"] = "active"
      else:
        db[mac] = {
            "status": "active",
            "expires_at": expiry_date.isoformat(),
            "trial": False,
            "ota_pending": False,
            "created_at": datetime.utcnow().isoformat(),
        }
      save_db(db)
    except ValueError:
      pass

  return redirect(url_for("admin_panel"))


@app.route("/admin/trigger-ota/<path:mac>", methods=["GET"])
def trigger_ota(mac):
  if "user" not in session:
    return redirect(url_for("login"))

  mac = mac.strip().upper()
  db = load_db()
  if mac in db:
    db[mac]["ota_pending"] = True
    save_db(db)

  return redirect(url_for("admin_panel"))


@app.route("/admin/cancel-ota/<path:mac>", methods=["GET"])
def cancel_ota(mac):
  if "user" not in session:
    return redirect(url_for("login"))

  mac = mac.strip().upper()
  db = load_db()
  if mac in db:
    db[mac]["ota_pending"] = False
    save_db(db)

  return redirect(url_for("admin_panel"))


@app.route("/api/check-license", methods=["GET"])
def check_license():
  mac_address = request.args.get("mac")
  if not mac_address:
    return (
        jsonify({"error": "Missing mac address parameter", "status": "error"}),
        400,
    )

  mac_address = mac_address.upper()
  now = datetime.utcnow()
  db = load_db()

  if mac_address not in db:
    expiry_date = now + timedelta(days=30)
    db[mac_address] = {
        "status": "active",
        "expires_at": expiry_date.isoformat(),
        "trial": True,
        "ota_pending": False,
        "created_at": now.isoformat(),
    }
    save_db(db)

  device_info = db[mac_address]
  expiry_time = datetime.fromisoformat(device_info["expires_at"])

  if now > expiry_time:
    device_info["status"] = "expired"
    save_db(db)
    return jsonify({
        "mac": mac_address,
        "status": "expired",
        "message": "License expired.",
        "expires_at": device_info["expires_at"],
    })

  return jsonify({
      "mac": mac_address,
      "status": "active",
      "message": "License is valid.",
      "trial": device_info["trial"],
      "expires_at": device_info["expires_at"],
  })


@app.route("/api/check-update", methods=["GET"])
def check_update():
  mac_address = request.args.get("mac")
  if not mac_address:
    return jsonify({"update_available": False, "error": "Missing MAC"}), 400

  mac_address = mac_address.upper()
  db = load_db()

  if mac_address in db and db[mac_address].get("ota_pending", False):
    db[mac_address]["ota_pending"] = False
    save_db(db)

    return jsonify({
        "update_available": True,
        "latest_version": DEFAULT_LATEST_VERSION,
        "firmware_url": DEFAULT_FIRMWARE_URL,
        "changelog": "Cập nhật từ xa theo yêu cầu quản trị viên.",
    })

  return jsonify({"update_available": False})


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=10000)
