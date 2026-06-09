import qrcode
from pathlib import Path
from backend.database import init_db, get_tables
import socket
import os

init_db()
tables = get_tables()

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

local_ip = get_local_ip()
print(f"Using local IP: {local_ip}")

qr_dir = Path("qr_codes")
try:
    qr_dir.mkdir(exist_ok=True)
except Exception as e:
    print(f"❌ Error creating qr_codes folder: {e}")
    exit(1)

if not tables:
    print("⚠️ No tables found. Add tables in admin dashboard first.")
else:
    for table in tables:
        url = f"http://{local_ip}:8000/order?table_id={table['id']}"
        try:
            img = qrcode.make(url)
            fname = f"qr_codes/table_{table['id']}_{table['name'].replace(' ', '_')}.png"
            img.save(fname)
            print(f"✅ {table['name']}: {url} → {fname}")
        except Exception as e:
            print(f"❌ Error creating QR for {table['name']}: {e}")