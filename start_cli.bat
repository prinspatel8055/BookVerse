@echo off
title DocTrans Master - CLI Interactive Mode
color 0A
echo ======================================================================
echo    DocTrans Master - Command Line Tool
echo    Universal PDF, FB2 & Diagram Image Translator
echo ======================================================================
echo.
echo Examples of commands:
echo   1. Translate a single PDF:
echo      python cli.py translate "path\to\book.pdf" --target en
echo.
echo   2. Translate with page range (e.g. pages 1 to 5):
echo      python cli.py translate "path\to\book.pdf" --pages 1-5 --target en
echo.
echo   3. Translate an entire Russian folder:
echo      python cli.py batch "d:\Python books tech\hacking_books_ru-main\hacking_books_ru-main\exploits" --target en
echo.
echo ======================================================================
cmd /k
