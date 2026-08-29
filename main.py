from datetime import datetime
from fastapi import FastAPI, HTTPException
import sqlite3
import uvicorn

app = FastAPI(title="Device License Server")

# Khởi tạo cơ sở dữ liệu SQLite cục bộ (miễn phí, tự sinh file licenses.db)
def init_db():
    conn = sqlite3.connect("licenses.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            mac TEXT PRIMARY KEY,
            expire_date TEXT,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# 1. API kiểm tra bản quyền (Thiết bị ESP32 sẽ gọi API này)
@app.get("/api/check-license")
def check_license(mac: str):
    conn = sqlite3.connect("licenses.db")
    cursor = conn.cursor()
    cursor.execute("SELECT expire_date, status FROM devices WHERE mac = ?", (mac.upper(),))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"status": "not_found", "message": "Thiết bị chưa được đăng ký bản quyền"}

    expire_date_str, status = row
    
    # Kiểm tra hạn sử dụng so với ngày hiện tại
    try:
        expire_date = datetime.strptime(expire_date_str, "%Y-%m-%d")
        if status != "active" or datetime.now() > expire_date:
            return {"status": "expired", "message": "Thiết bị đã hết hạn bản quyền"}
    except Exception:
        return {"status": "error", "message": "Lỗi định dạng ngày tháng"}

    return {"status": "active", "expire_date": expire_date_str, "message": "Bản quyền hợp lệ"}

# 2. API thêm hoặc gia hạn thiết bị (Dùng để bạn quản lý từ xa)
@app.post("/api/set-license")
def set_license(mac: str, expire_date: str):
    # Định dạng expire_date yêu cầu: "YYYY-MM-DD" (Ví dụ: "2026-12-31")
    conn = sqlite3.connect("licenses.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO devices (mac, expire_date, status) VALUES (?, ?, 'active')
        ON CONFLICT(mac) DO UPDATE SET expire_date = ?, status = 'active'
    """, (mac.upper(), expire_date, expire_date))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Đã cập nhật hạn cho MAC {mac.upper()} đến {expire_date}"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
