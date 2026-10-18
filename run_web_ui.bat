@echo off
chcp 65001 >nul
title MarkItDown Studio
echo ===================================================
echo   Đang khởi động MarkItDown Studio...
echo ===================================================
python "%~dp0web_ui.py"
pause
