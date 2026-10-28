@echo off
title Upload AI-Book-Translator to GitHub
color 0b
echo ========================================================
echo       UPLOADING AI-BOOK-TRANSLATOR TO GITHUB
echo ========================================================
echo.
echo Pushing code to https://github.com/prinspatel8055/AI-Book-Translator ...
echo If a browser window opens, click "Authorize Git Credential Manager" / "Sign in with browser".
echo.
git push -u origin main
echo.
if %errorlevel% equ 0 (
    echo ========================================================
    echo   SUCCESS! All project files are now live on GitHub!
    echo ========================================================
) else (
    echo [!] Push failed or cancelled. Please try again.
)
echo.
pause
