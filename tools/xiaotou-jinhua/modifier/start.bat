@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo 当前目录: %CD%
echo 建议: 右键本文件 -^> 以管理员身份运行
echo.
python -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo pip 安装失败
    pause
    exit /b 1
)
python run.py
if errorlevel 1 pause