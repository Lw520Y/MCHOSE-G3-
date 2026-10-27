@echo off
rem build_exe.bat — 一键打包 MCHOSEG3Battery.exe（产物在 dist\ 下）
cd /d "%~dp0"
pip show pyinstaller >nul 2>&1 || pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed ^
  --name MCHOSEG3Battery ^
  --icon icon.ico ^
  --hidden-import pystray._win32 ^
  g3_tray.pyw
if errorlevel 1 (
  echo.
  echo 打包失败，请检查上方报错
  pause
  exit /b 1
)
echo.
echo 完成：dist\MCHOSEG3Battery.exe
pause
