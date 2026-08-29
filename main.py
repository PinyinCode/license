from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

# Cơ sở dữ liệu giả lập trên RAM
devices_db = {}

# Giao diện HTML với lịch chọn ngày hết hạn cụ thể
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Quản lý Bản quyền ESP32</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f4f7f6; color: #333; }
        .container { max-width: 850px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h2 { color: #007BFF; }
        table { width: 100%%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
        th { background: #007BFF; color: white; }
        input, select, button { padding: 8px; margin: 5px 0; border: 1px solid #ccc; border-radius: 4px; }
        button { background: #28a745; color: white; border: none; cursor: pointer; }
        button:hover { background: #218838; }
        .form-group { background: #e9ecef; padding: 15px; border-radius: 6px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Quản lý Bản quyền Thiết bị ESP32</h2>
        
        <div class="form-group">
            <h3>Thêm hoặc Cập nhật hạn thiết bị</h3>
            <form action="/admin/add" method="POST">
                <label>Địa chỉ MAC:</label><br>
                <input type="text" name="mac" placeholder="Ví dụ: AA:BB:CC:DD:EE:FF" required style="width: 100%%;"><br>
                <label>Ngày hết hạn cụ thể:</label><br>
                <input type="date" name="expiry_date" required style="width: 100%%;"><br><br>
                <button type="submit">Lưu / Cập nhật</button>
            </form>
        </div>

        <h3>Danh sách thiết bị đã kết nối</h3>
        <table>
            <tr>
                <th>Địa chỉ MAC</th>
                <th>Trạng thái</th>
                <th>Loại</th>
                <th>Ngày hết hạn</th>
            </tr>
            {% for mac, info in devices.items() %}
            <tr>
                <td><b>{{ mac }}</b></td>
                <td style="color: {{ 'green' if info.status == 'active' else 'red' }};">{{ info.status }}</td>
                <td>{{ 'Dùng thử (Trial)' if info.trial else 'Chính thức' }}</td>
                <td>{{ info.expires_at }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""


@app.route("/")
def home():
  return "ESP32 License Server is running!"


@app.route("/admin", methods=["GET"])
def admin_panel():
  return render_template_string(ADMIN_HTML, devices=devices_db)


@app.route("/admin/add", methods=["POST"])
def admin_add():
  mac = request.form.get("mac")
  expiry_date_str = request.form.get("expiry_date")  # Định dạng YYYY-MM-DD từ input date

  if mac and expiry_date_str:
    mac = mac.strip().upper()
    try:
      # Chuyển chuỗi ngày thành datetime (đặt giờ hết hạn là cuối ngày 23:59:59)
      expiry_date = datetime.strptime(expiry_date_str, "%Y-m-%d").replace(
          hour=23, minute=59, second=59
      )
      devices_db[mac] = {
          "status": "active",
          "expires_at": expiry_date.isoformat(),
          "trial": False,
      }
    except ValueError:
      pass

  return admin_panel()


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

  if mac_address not in devices_db:
    expiry_date = now + timedelta(days=30)  # Tự động cấp 30 ngày trial
    devices_db[mac_address] = {
        "status": "active",
        "expires_at": expiry_date.isoformat(),
        "trial": True,
        "created_at": now.isoformat(),
    }

  device_info = devices_db[mac_address]
  expiry_time = datetime.fromisoformat(device_info["expires_at"])

  if now > expiry_time:
    device_info["status"] = "expired"
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


@app.route("/api/admin/activate", methods=["POST"])
def admin_activate():
  data = request.json
  if not data:
    return jsonify({"error": "Invalid JSON"}), 400
  mac = data.get("mac")
  expiry_date_str = data.get(
      "expires_at"
  )  # Nhận trực tiếp chuỗi thời gian nếu gọi API

  if not mac or not expiry_date_str:
    return jsonify({"error": "Missing mac or expires_at"}), 400

  mac = mac.upper()
  devices_db[mac] = {
      "status": "active",
      "expires_at": expiry_date_str,
      "trial": False,
  }
  return jsonify(
      {"success": True, "mac": mac, "new_expires_at": expiry_date_str}
  )


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=10000)
