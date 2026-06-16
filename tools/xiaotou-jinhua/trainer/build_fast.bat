@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  小偷进化修改器 - 快速版 exe（不覆盖标准版）
echo ========================================
echo.

python -m pip install -r requirements-build.txt -q
if errorlevel 1 (
    echo pip 安装失败
    pause
    exit /b 1
)

if not exist dist mkdir dist

python -m PyInstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --uac-admin ^
  --name "小偷进化修改器-快速版" ^
  --hidden-import=pymem ^
  --hidden-import=pymem.memory ^
  --hidden-import=pymem.process ^
  --hidden-import=pymem.ressources ^
  --hidden-import=pymem.ressources.structure ^
  --hidden-import=psutil ^
  run_fast.py

if errorlevel 1 (
    echo 打包失败
    pause
    exit /b 1
)

echo.
echo 完成: dist\小偷进化修改器-快速版.exe
echo 标准版未被修改: dist\小偷进化修改器.exe
echo.
copy /Y "dist\小偷进化修改器-快速版.exe" "..\..\小偷进化修改器-快速版.exe" >nul 2>&1
if exist "..\..\小偷进化修改器-快速版.exe" echo 已复制到: tools\小偷进化修改器-快速版.exe
pause
