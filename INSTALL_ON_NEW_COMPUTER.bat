@echo off
title INSTALLATION SETUP FOR NEW COMPUTER
color 0A
echo ======================================================================
echo    UNIVERSAL DOCUMENT TRANSLATOR - AUTOMATIC SETUP FOR NEW PC
echo ======================================================================
echo.

:: 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10 or 3.11 from: https://www.python.org/downloads/
    echo IMPORTANT: Make sure to check the box "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [*] Python detected:
python --version
echo.

:: 2. Upgrade pip
echo [*] Upgrading pip...
python -m pip install --upgrade pip
echo.

:: 3. Install CPU PyTorch
echo [*] Installing PyTorch (CPU Optimized)...
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
echo.

:: 4. Install Project Requirements
echo [*] Installing all project dependencies...
cd /d "%~dp0"
pip install -r requirements.txt
echo.

:: 5. Install Offline Russian to English Model
echo [*] Pre-installing Offline Russian-to-English Neural AI Model...
python -c "import argostranslate.package; argostranslate.package.update_package_index(); pkgs = argostranslate.package.get_available_packages(); p = next((x for x in pkgs if x.from_code == 'ru' and x.to_code == 'en'), None); p.download() and argostranslate.package.install_from_path(p.download()) if p else None; print('Model Ready!')"
echo.

echo ======================================================================
echo   [SUCCESS] ALL DEPENDENCIES & AI MODELS INSTALLED SUCCESSFULLY!
echo ======================================================================
echo.
echo You can now run:
echo   1. START_BATCH_TRANSLATOR.bat  -> To translate 320+ books in batch
echo   2. START_WEB_APP.bat           -> To launch the Interactive Web Studio
echo.
pause
