@echo off
REM Menjalankan backend STRUKKU agar bisa diakses dari emulator / HP di Wi-Fi yang sama
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
echo.
echo Alamat IP laptop ini (pakai untuk HP fisik):
ipconfig | findstr /i "IPv4"
echo.
echo Emulator Android : http://10.0.2.2:8000/api/v1
echo Web / Windows    : http://127.0.0.1:8000/api/v1
echo.
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
