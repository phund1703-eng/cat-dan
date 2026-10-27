"""
launch_studio.py — Trình khởi chạy thông minh toàn diện cho AutoVideoFactory Studio.

Tự động:
1. Nhận diện cổng tối ưu (tránh xung đột cổng 8000/8501).
2. Khởi chạy đồng bộ: Video Worker + FastAPI Backend + Streamlit Dashboard.
3. Tự động mở trình duyệt web tới giao diện Studio.
4. Dọn dẹp sạch sẽ toàn bộ tiến trình con khi đóng cửa sổ hoặc nhấn Ctrl+C.
"""

from __future__ import annotations

import atexit
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

# Đảm bảo UTF-8 cho console Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON_EXE = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"

procs: list[subprocess.Popen] = []
open_files: list = []


def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """Kiểm tra xem cổng TCP có đang rảnh không."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def is_autovideofactory_api(port: int) -> bool:
    """Kiểm tra cổng đã chạy đúng AutoVideoFactory API chưa."""
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/openapi.json",
            headers={"User-Agent": "AutoVideoFactory-Launcher"},
        )
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return "AutoVideoFactory" in data.get("info", {}).get("title", "")
    except Exception:
        return False


def find_free_port(start_port: int, max_tries: int = 20) -> int:
    """Tìm cổng rảnh từ start_port."""
    for p in range(start_port, start_port + max_tries):
        if is_port_available(p):
            return p
    return start_port


def wait_for_api_ready(api_port: int, timeout_sec: int = 15) -> bool:
    """Chờ API khởi động thành công."""
    start_t = time.time()
    url = f"http://127.0.0.1:{api_port}/openapi.json"
    while time.time() - start_t < timeout_sec:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AutoVideoFactory-Launcher"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def cleanup():
    """Tắt tất cả tiến trình con khi kết thúc."""
    global procs, open_files
    if procs:
        print("\n⏳ Đang dừng các dịch vụ...")
        for p in procs:
            try:
                if p.poll() is None:
                    p.terminate()
            except Exception:
                pass
        # Chờ nhẹ 1s để tiến trình thoát
        time.sleep(1)
        for p in procs:
            try:
                if p.poll() is None:
                    p.kill()
            except Exception:
                pass
        procs.clear()

    for f in open_files:
        try:
            f.close()
        except Exception:
            pass
    open_files.clear()


atexit.register(cleanup)


def signal_handler(sig, frame):
    cleanup()
    print("✅ Đã tắt toàn bộ dịch vụ. Tạm biệt!")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def main():
    print("=" * 70)
    print("       🎬 AUTOVIDEOFACTORY - KHỞI ĐỘNG PHÒNG THU VIDEO 🎬")
    print("=" * 70)

    # 1. Kiểm tra môi trường venv
    if not PYTHON_EXE.exists():
        print(f"❌ Không tìm thấy Python trong venv: {PYTHON_EXE}")
        print("   Vui lòng chạy file install.bat trước để thiết lập môi trường.")
        input("\nNhấn Enter để thoát...")
        sys.exit(1)

    # 2. Kiểm tra file .env
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        print("⚠️ Chưa có file .env! Đang tự động sao chép từ .env.example...")
        example_file = PROJECT_ROOT / ".env.example"
        if example_file.exists():
            env_file.write_text(example_file.read_text(encoding="utf-8"), encoding="utf-8")
            print("✅ Đã tạo file .env mới từ mẫu .env.example.")
            print("   Lưu ý: Bạn hãy mở .env và điền các API key thực tế nếu cần dùng AI online.")
        else:
            print("❌ Không tìm thấy .env.example để khởi tạo.")

    # 3. Lựa chọn cổng thông minh
    # API Backend: Ưu tiên 8000
    api_already_running = False
    if is_autovideofactory_api(8000):
        api_port = 8000
        api_already_running = True
        print("ℹ️ Phát hiện AutoVideoFactory API đã chạy sẵn trên cổng 8000.")
    elif is_port_available(8000):
        api_port = 8000
    else:
        # Cổng 8000 đang bị phần mềm khác chiếm
        api_port = find_free_port(8008)
        print(f"⚠️ Cổng 8000 đang bận (do ứng dụng khác sử dụng).")
        print(f"➡️ Tự động điều hướng API Backend sang cổng khả dụng: {api_port}")

    # Streamlit UI: Ưu tiên 8501
    ui_port = 8501 if is_port_available(8501) else find_free_port(8502)

    # 4. Chuẩn bị thư mục logs
    logs_dir = PROJECT_ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)

    env = os.environ.copy()
    env["API_URL"] = f"http://localhost:{api_port}"
    env["PYTHONIOENCODING"] = "utf-8"

    # 5. Khởi chạy Video Worker (Durable queue worker)
    print("\n[1/3] Khởi động Video Worker ngầm (xử lý hàng đợi render)...")
    worker_log = open(logs_dir / "worker.log", "a", encoding="utf-8")
    open_files.append(worker_log)
    worker_proc = subprocess.Popen(
        [str(PYTHON_EXE), "-m", "dashboard.worker.runner"],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=worker_log,
        stderr=subprocess.STDOUT,
    )
    procs.append(worker_proc)
    print("      ✅ Video Worker đang chạy.")

    # 6. Khởi chạy FastAPI Backend (nếu chưa chạy)
    if not api_already_running:
        print(f"[2/3] Khởi động API Backend (Uvicorn cổng {api_port})...")
        api_log = open(logs_dir / "api.log", "a", encoding="utf-8")
        open_files.append(api_log)
        api_proc = subprocess.Popen(
            [
                str(PYTHON_EXE),
                "-m",
                "uvicorn",
                "dashboard.api.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                str(api_port),
            ],
            cwd=str(PROJECT_ROOT),
            env=env,
            stdout=api_log,
            stderr=subprocess.STDOUT,
        )
        procs.append(api_proc)

        # Chờ API sẵn sàng
        print("      ⏳ Đang đợi API Backend sẵn sàng...")
        if wait_for_api_ready(api_port, timeout_sec=12):
            print(f"      ✅ API Backend đã sẵn sàng tại http://localhost:{api_port}")
        else:
            print("      ⚠️ API Backend đang khởi động hoặc ghi log vào logs/api.log")
    else:
        print(f"[2/3] API Backend đã sẵn sàng tại http://localhost:{api_port}")

    # 7. Khởi chạy Streamlit Dashboard
    print(f"[3/3] Khởi động Giao diện Streamlit Dashboard (cổng {ui_port})...")
    ui_log = open(logs_dir / "streamlit.log", "a", encoding="utf-8")
    open_files.append(ui_log)
    ui_proc = subprocess.Popen(
        [
            str(PYTHON_EXE),
            "-m",
            "streamlit",
            "run",
            "dashboard/ui/app.py",
            "--server.port",
            str(ui_port),
            "--server.headless",
            "true",
        ],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=ui_log,
        stderr=subprocess.STDOUT,
    )
    procs.append(ui_proc)

    ui_url = f"http://localhost:{ui_port}"

    # 8. Mở trình duyệt web
    time.sleep(2)
    print(f"      ✅ Giao diện sẵn sàng tại {ui_url}")
    print("      🌐 Đang tự động mở trình duyệt web...")
    try:
        webbrowser.open(ui_url)
    except Exception:
        pass

    # 9. In bảng trạng thái trực quan
    print("\n" + "=" * 70)
    print("                  🎉 HỆ THỐNG ĐÃ HOẠT ĐỘNG HOÀN HẢO! 🎉")
    print("=" * 70)
    print(f"  🟢 Video Worker  : Đang chạy ngầm (xem logs/worker.log)")
    print(f"  🟢 API Backend   : http://localhost:{api_port} (tài liệu: /docs)")
    print(f"  🟢 Studio UI     : {ui_url}")
    print("=" * 70)
    print("  💡 HƯỚNG DẪN:")
    print("  - Bạn có thể làm việc trực tiếp trên cửa sổ trình duyệt vừa mở.")
    print("  - Hãy GIỮ CỬA SỔ NÀY trong suốt quá trình làm video.")
    print("  - Khi xong việc, chỉ cần nhấn phím Ctrl + C để tắt toàn bộ hệ thống.")
    print("=" * 70 + "\n")

    # Giám sát các tiến trình
    try:
        while True:
            time.sleep(1)
            # Kiểm tra xem có tiến trình nào bị ngắt ngoài ý muốn không
            if worker_proc.poll() is not None:
                print("⚠️ Cảnh báo: Video Worker đã dừng ngoài ý muốn. Xem logs/worker.log")
                break
            if not api_already_running and api_proc.poll() is not None:
                print("⚠️ Cảnh báo: API Backend đã dừng ngoài ý muốn. Xem logs/api.log")
                break
            if ui_proc.poll() is not None:
                print("ℹ️ Giao diện Streamlit đã đóng.")
                break
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
        print("✅ Toàn bộ cổng và tiến trình đã được đóng an toàn.")


if __name__ == "__main__":
    main()
