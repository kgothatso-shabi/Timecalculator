@echo off
REM Builds dist\TimeCalculator.exe (single file, no console window).
setlocal
cd /d "%~dp0"

if not exist .venv ( py -3 -m venv .venv || goto :fail )
call .venv\Scripts\activate.bat || goto :fail
python -m pip install --upgrade pip || goto :fail
pip install -r requirements-build.txt || goto :fail

echo Running tests...
python -m unittest discover -s tests || goto :fail

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

set "ICON="
if exist "assets\app.ico" set "ICON=--icon assets\app.ico"

pyinstaller --noconfirm --clean --windowed --onefile --name TimeCalculator %ICON% main.py || goto :fail

echo.
echo Done: dist\TimeCalculator.exe
exit /b 0

:fail
echo.
echo BUILD FAILED
exit /b 1
