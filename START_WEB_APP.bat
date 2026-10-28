@echo off
title DocTrans Master - Web Server
cd /d "%~dp0"
echo ======================================================================
echo    Starting DocTrans Master Web Studio...
echo    Open your browser at: http://127.0.0.1:8000
echo ======================================================================
echo.
python web_app.py
pause
