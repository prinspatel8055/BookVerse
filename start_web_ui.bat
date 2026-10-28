@echo off
title DocTrans Master - Universal Document & Image Translator Web UI
color 0B
echo ======================================================================
echo    Starting DocTrans Master Web Interface
echo    Universal PDF, FB2 & In-Diagram Image OCR Translator
echo ======================================================================
echo.
echo [1/2] Opening your browser to http://127.0.0.1:8000 ...
timeout /t 2 /nobreak >nul
start http://127.0.0.1:8000
echo [2/2] Launching FastAPI Web Server...
echo.
python web_app.py
pause
