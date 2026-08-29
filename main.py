from datetime import datetime, timedelta
from flask import Flask, jsonify, request

app = Flask(__name__)

# Cơ sở dữ liệu giả lập trên RAM (Có thể thay thế bằng SQLite hoặc MongoDB/PostgreSQL nếu cần lưu trữ lâu dài)
# Cấu trúc: { "MAC_ADDRESS": { "status": "active", "expires_at": "2026-09-28T...", "trial": True } }
devices_db = {}


@app.route("/")
def home():
  return "ESP32 License Server is running successfully!"


@app.route("/api/check-license", methods=["GET"])
def check_license():
  # Lấy địa chỉ MAC từ request (Ví dụ: /api/check-license?mac=11:22:33:44:55:66)
  mac_address = request.args.get("mac")

  if not mac_address:
    return (
        jsonify({"error": "Missing mac address parameter", "status": "error"}),
        400,
    )

  mac_address = mac_address.upper()
  now = datetime.utcnow()

  # Nếu thiết bị chưa từng kết nối lên hệ thống -> Tự động cấp 30 ngày dùng thử (Trial)
  if mac_address not in devices_db:
    expiry_date = now + timedelta(days=30)
    devices_db[mac_address] = {
        "status": "active",
        "expires_at": expiry_date.isoformat(),
        "trial": True,
        "created_at": now.isoformat(),
    }

  device_info = devices_db[mac_address]
  expiry_time = datetime.fromisoformat(device_info["expires_at"])

  # Kiểm tra xem hạn sử dụng đã qua chưa
  if now > expiry_time:
    device_info["status"] = "expired"
    return jsonify({
        "mac": mac_address,
        "status": "expired",
        "message": "License expired. Please renew.",
        "expires_at": device_info["expires_at"],
    })

  # Nếu còn hạn
  return jsonify({
      "mac": mac_address,
      "status": "active",
      "message": "License is valid.",
      "trial": device_info["trial"],
      "expires_at": device_info["expires_at"],
  })


# API phụ để bạn chủ động kích hoạt/gia hạn thiết bị từ xa nếu cần
@app.route("/api/admin/activate", methods=["POST"])
def admin_activate():
  data = request.json
  mac_address = data.get("mac")
  days = data.get("days", 365)  # Mặc định gia hạn 1 năm

  if not mac_address:
    return jsonify({"error": "Missing mac"}), 400

  mac_address = mac_address.upper()
  expiry_date = datetime.utcnow() + timedelta(days=int(days))

  devices_db[mac_address] = {
      "status": "active",
      "expires_at": expiry_date.isoformat(),
      "trial": False,
  }

  return jsonify({
      "success": True,
      "mac": mac_address,
      "new_expires_at": expiry_date.isoformat(),
  })


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=10000)
