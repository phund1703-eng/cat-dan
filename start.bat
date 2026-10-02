@echo off
chcp 65001 >nul
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     AutoVideoFactory - Khởi Động         ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Kích hoạt virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo ❌ Chưa cài đặt! Hãy chạy install.bat trước.
    pause
    exit /b 1
)

:: Kiểm tra .env
if not exist ".env" (
    echo ❌ File .env chưa có! Copy từ .env.example và điền API keys.
    pause
    exit /b 1
)

echo Đang khởi động các dịch vụ...
echo.

:: Khởi động Redis (nếu có Docker)
echo [1/3] Kiểm tra Redis...
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Redis chưa chạy - Celery worker sẽ không hoạt động
    echo    Cài Redis: https://github.com/microsoftarchive/redis/releases
) else (
    echo ✅ Redis đang chạy
)

:: Khởi động Celery Worker (background)
echo [2/3] Khởi động Celery Worker...
start /b "Celery Worker" cmd /c "venv\Scripts\activate && celery -A dashboard.worker.celery_app worker --loglevel=info --logfile=logs\celery.log 2>&1"
timeout /t 2 /nobreak >nul
echo ✅ Celery Worker đã khởi động

:: Khởi động FastAPI Backend (background)
echo [3/3] Khởi động API Backend...
start /b "API Backend" cmd /c "venv\Scripts\activate && uvicorn dashboard.api.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 | python -c \"import sys; [print(line, end='') for line in sys.stdin]\" > logs\api.log 2>&1"
timeout /t 2 /nobreak >nul
echo ✅ API Backend đã khởi động tại http://localhost:8000

echo.
echo  Đang mở Dashboard...
start "" "http://localhost:8501"
timeout /t 1 /nobreak >nul

:: Khởi động Streamlit Dashboard (foreground)
echo ✅ Mở Dashboard tại http://localhost:8501
echo.
echo  Nhấn Ctrl+C để dừng hệ thống
echo.
streamlit run dashboard\ui\app.py --server.port 8501 --server.headless true
