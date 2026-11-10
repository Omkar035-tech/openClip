import sys
import time
import threading
import urllib.request
import webview
import uvicorn
from pathlib import Path
from clipper.web import app

PORT = 8080
SERVER_URL = f"http://127.0.0.1:{PORT}"

def is_server_alive():
    try:
        with urllib.request.urlopen(f"{SERVER_URL}/api/long-form/projects", timeout=1) as response:
            return response.status == 200
    except Exception:
        return False

def start_uvicorn_server():
    """Runs FastAPI backend inside a background daemon thread."""
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")

def launch_desktop_app():
    """
    Native Windows Desktop Application for openClip Studio.
    Uses Microsoft Edge Chromium WebView2 engine (same engine as Tauri).
    Provides native window chrome, hardware-accelerated canvas, zero browser limits,
    and automatic backend lifecycle management.
    """
    if not is_server_alive():
        print(f"[Desktop] Launching openClip backend on {SERVER_URL}...")
        server_thread = threading.Thread(target=start_uvicorn_server, daemon=True)
        server_thread.start()

        # Wait for backend readiness
        for _ in range(30):
            if is_server_alive():
                break
            time.sleep(0.3)
    else:
        print(f"[Desktop] Connected to existing openClip backend on {SERVER_URL}")

    # Create native Windows WebView2 window (Tauri-equivalent architecture)
    window = webview.create_window(
        title="openClip Studio - AI Video Editor (Desktop)",
        url=SERVER_URL,
        width=1400,
        height=900,
        min_size=(1024, 700),
        resizable=True,
        fullscreen=False,
        confirm_close=False,
        background_color="#0b0f19"
    )

    # Start native Windows event loop using Edge Chromium WebView2
    webview.start(gui="edgechromium", debug=False)

if __name__ == "__main__":
    launch_desktop_app()
