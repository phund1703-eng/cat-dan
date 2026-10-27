@echo off
chcp 65001 >nul
title AutoVideoFactory Studio
cd /d "%~dp0"

:: Kích hoạt virtual environment và khởi chạy qua launch_studio.py
if exist "venv\Scripts\python.exe" (
    ".\venv\Scripts\python.exe" launch_studio.py
) else (
    echo ❌ Chưa cài đặt môi trường ảo! Hãy chạy install.bat trước.
    pause
    exit /b 1
)

if errorlevel 1 (
    echo.
    echo ❌ Hệ thống dừng lại với lỗi.
    pause
)
