@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  小偷进化修改器 - 打包 exe
echo ========================================
echo.

python -m pip install -r requirements-build.txt -q
if errorlevel 1 (
    echo pip 安装失败
    pause
    exit /b 1
)

if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

python -m PyInstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --uac-admin ^
  --name "小偷进化修改器" ^
  --hidden-import=pymem ^
  --hidden-import=pymem.memory ^
  --hidden-import=pymem.process ^
  --hidden-import=pymem.ressources ^
  --hidden-import=pymem.ressources.structure ^
  --hidden-import=psutil ^
  run.py

if errorlevel 1 (
    echo 打包失败
    pause
    exit /b 1
)

echo.
echo 完成: dist\小偷进化修改器.exe
echo 请右键 -^> 以管理员身份运行
echo.
copy /Y "dist\小偷进化修改器.exe" "..\..\小偷进化修改器.exe" >nul 2>&1
if exist "..\..\小偷进化修改器.exe" echo 已复制到: tools\小偷进化修改器.exe
pause
