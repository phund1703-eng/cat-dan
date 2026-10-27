@echo off
chcp 65001 >nul
title AutoVideoFactory Studio
cd /d "%~dp0"

if exist "venv\Scripts\python.exe" (
    ".\venv\Scripts\python.exe" launch_studio.py
) else (
    echo ❌ Không tìm thấy môi trường ảo Python tại venv\Scripts!
    echo Hãy đảm bảo bạn đã chạy install.bat trước.
    pause
    exit /b 1
)

if errorlevel 1 (
    echo.
    echo Hệ thống kết thúc với mã lỗi %errorlevel%.
    pause
)
