import subprocess
import threading
import time
import sys
import socket

def check_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        result = sock.connect_ex(('localhost', port))
        return result == 0
    finally:
        sock.close()

def run_backend():
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "backend.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
    except Exception as e:
        print(f"❌ Backend error: {e}")

def run_admin():
    time.sleep(3)
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            "admin_dashboard/app.py",
            "--server.port", "8501",
            "--server.headless", "true"
        ])
    except Exception as e:
        print(f"❌ Admin dashboard error: {e}")

if __name__ == "__main__":
    print("="*60)
    print("🎱 SNOOKER CAFE MANAGEMENT SYSTEM")
    print("="*60)
    
    # Check ports
    if check_port(8000):
        print("⚠️  Port 8000 is already in use (backend may already be running)")
    if check_port(8501):
        print("⚠️  Port 8501 is already in use (admin may already be running)")
    
    print()
    print("🚀 Starting services...")
    print("   API  → http://localhost:8000")
    print("   API Docs → http://localhost:8000/docs")
    print("   Admin → http://localhost:8501")
    print("   Login password: admin123")
    print("="*60)
    
    t1 = threading.Thread(target=run_backend, daemon=True)
    t2 = threading.Thread(target=run_admin, daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()