@echo off
title PDF Organizer - Download Offline AI Model
echo ===================================================
echo   Downloading Multilingual Embedding Model Once
echo ===================================================
echo.
python "%~dp0download_model.py"
echo.
pause
