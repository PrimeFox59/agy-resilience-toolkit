import os
import sys
import time
import subprocess
import urllib.request

APP_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_SCRIPT = os.path.join(APP_DIR, "server.py")
PORT = 4567
HEALTH_URL = f"http://127.0.0.1:{PORT}/api/accounts"
PYTHONW = r"C:\Users\PRIMA\AppData\Local\Programs\Python\Launcher\pyw.exe"
if not os.path.exists(PYTHONW):
    PYTHONW = sys.executable

LOG_FILE = os.path.join(APP_DIR, "daemon.log")

def log(msg):
    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

def is_server_healthy():
    try:
        req = urllib.request.Request(HEALTH_URL, headers={"User-Agent": "Antigravity-Supervisor/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False

def start_server():
    log(f"Starting Antigravity Web UI on port {PORT}...")
    try:
        creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        p = subprocess.Popen(
            [PYTHONW, SERVER_SCRIPT, str(PORT)],
            cwd=APP_DIR,
            creationflags=creationflags
        )
        log(f"Antigravity Web UI started with PID {p.pid}")
        return p
    except Exception as e:
        log(f"Failed to start server: {e}")
        return None

def main():
    log("Antigravity Resilience Daemon started.")
    while True:
        try:
            if not is_server_healthy():
                log("Server is not responding. Spawning instance...")
                start_server()
                time.sleep(5)
            time.sleep(10)
        except Exception as e:
            log(f"Daemon loop error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
