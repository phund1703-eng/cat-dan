@echo off
chcp 65001 >nul
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║    AutoVideoFactory - Cài Đặt Tự Động   ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Kiểm tra Python
echo [1/9] Kiểm tra Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python chưa được cài đặt!
    echo    Tải tại: https://python.org/downloads
    pause
    exit /b 1
)
echo ✅ Python OK

:: Kiểm tra Git
echo [2/9] Kiểm tra Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Git chưa được cài đặt!
    echo    Tải tại: https://git-scm.com
    pause
    exit /b 1
)
echo ✅ Git OK

:: Kiểm tra FFmpeg
echo [3/9] Kiểm tra FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  FFmpeg chưa được cài đặt
    echo    Đang tải FFmpeg tự động qua winget...
    winget install --id Gyan.FFmpeg -e >nul 2>&1
    if errorlevel 1 (
        echo    ❌ Không thể tự động cài FFmpeg
        echo    Tải thủ công tại: https://ffmpeg.org/download.html
        echo    Sau đó thêm vào PATH và chạy lại install.bat
        pause
        exit /b 1
    )
    echo ✅ FFmpeg đã được cài đặt
) else (
    echo ✅ FFmpeg OK
)

:: Tạo virtual environment
echo [4/9] Tạo Python virtual environment...
if not exist "venv" (
    python -m venv venv
    echo ✅ Virtual environment đã tạo
) else (
    echo ✅ Virtual environment đã tồn tại
)

:: Kích hoạt venv
call venv\Scripts\activate.bat

:: Nâng cấp pip
echo [5/9] Nâng cấp pip...
python -m pip install --upgrade pip --quiet

:: Cài packages cơ bản trước
echo [6/9] Cài đặt dependencies cơ bản...
pip install python-dotenv pyyaml loguru rich tqdm httpx aiofiles Pillow --quiet
pip install google-generativeai --quiet
pip install edge-tts --quiet
pip install faster-whisper --quiet
pip install moviepy ffmpeg-python --quiet
pip install fastapi uvicorn[standard] pydantic pydantic-settings --quiet
pip install sqlalchemy alembic --quiet
pip install streamlit plotly pandas --quiet
pip install apscheduler feedparser --quiet
pip install requests --quiet
echo ✅ Dependencies cơ bản đã cài xong

:: Cài TTS (có thể mất thời gian)
echo [7/9] Cài đặt TTS engines...
pip install TTS --quiet 2>&1 | tail -1
echo ✅ TTS engines đã cài xong

:: Tạo thư mục cần thiết
echo [8/9] Tạo cấu trúc thư mục...
if not exist "data\jobs" mkdir "data\jobs"
if not exist "data\output" mkdir "data\output"
if not exist "data\cache\pexels" mkdir "data\cache\pexels"
if not exist "data\cache\pixabay" mkdir "data\cache\pixabay"
if not exist "data\scripts" mkdir "data\scripts"
if not exist "assets\voices" mkdir "assets\voices"
if not exist "assets\avatars" mkdir "assets\avatars"
if not exist "assets\music" mkdir "assets\music"
if not exist "assets\fonts" mkdir "assets\fonts"
if not exist "assets\templates" mkdir "assets\templates"
if not exist "config\credentials" mkdir "config\credentials"
if not exist "logs" mkdir "logs"
echo ✅ Thư mục đã tạo xong

:: Kiểm tra tài nguyên tĩnh: font, nhạc nền, thư mục output/cache
echo [9/9] Kiểm tra tài nguyên (font, nhạc nền, output/cache)...
if not exist "assets\fonts\BeVietnamPro-Bold.ttf" (
    echo ⚠️  Thiếu font BeVietnamPro-Bold.ttf — đang tải lại...
    python scripts\download_assets.py
)
if exist "assets\fonts\BeVietnamPro-Bold.ttf" (
    echo ✅ Font OK: assets\fonts\BeVietnamPro-Bold.ttf
) else (
    echo ❌ Vẫn thiếu font assets\fonts\BeVietnamPro-Bold.ttf
    echo    Cách sửa: chạy "python scripts\download_assets.py"
    echo    hoặc tải tay từ https://github.com/google/fonts/tree/main/ofl/bevietnampro
)
if not exist "assets\music\*.mp3" (
    echo ⚠️  Chưa có nhạc nền trong assets\music — đang tải lại...
    python scripts\download_assets.py
)
if exist "assets\music\*.mp3" (
    echo ✅ Nhạc nền OK: assets\music
) else (
    echo ❌ Vẫn chưa có file .mp3 nào trong assets\music
    echo    Cách sửa: chạy "python scripts\download_assets.py" — xem assets\music\README.md
)
if not exist "data\output" mkdir "data\output"
if not exist "data\cache" mkdir "data\cache"
if not exist "output" mkdir "output"
echo ✅ Thư mục output/cache OK
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ❌ FFmpeg vẫn chưa dùng được — cài tại https://ffmpeg.org/download.html rồi chạy lại install.bat
) else (
    echo ✅ FFmpeg OK
)

:: Tạo file .env nếu chưa có
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo.
    echo ⚠️  File .env đã được tạo từ .env.example
    echo    QUAN TRỌNG: Mở file .env và điền API keys của bạn!
)

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     ✅ Cài Đặt Hoàn Tất!                ║
echo  ╠══════════════════════════════════════════╣
echo  ║  Bước tiếp theo:                        ║
echo  ║  1. Mở file .env và điền API keys       ║
echo  ║  2. Chạy: start.bat                     ║
echo  ║  3. Mở browser: http://localhost:8501   ║
echo  ╚══════════════════════════════════════════╝
echo.
pause
