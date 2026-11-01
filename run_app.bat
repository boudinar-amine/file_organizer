@echo off
title Local PDF Organizer
cd /d "%~dp0"

echo ============================================================
echo Starting Local PDF Organizer...
echo Working Directory: %CD%
echo ============================================================

set "PYTHON_EXE="

:: 1. Check Python 3.10 direct installation path
if exist "C:\Users\HP\AppData\Local\Programs\Python\Python310\python.exe" (
    set "PYTHON_EXE=C:\Users\HP\AppData\Local\Programs\Python\Python310\python.exe"
)

:: 2. Check system PATH python
if "%PYTHON_EXE%"=="" (
    where python >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_EXE=python"
    )
)

:: 3. Check py launcher
if "%PYTHON_EXE%"=="" (
    where py >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_EXE=py"
    )
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python was not found on your system!
    echo Please make sure Python 3.10+ is installed.
    pause
    exit /b 1
)

echo Using Python: %PYTHON_EXE%
echo Launching GUI...
echo.

"%PYTHON_EXE%" main.py

if errorlevel 1 (
    echo.
    echo ============================================================
    echo Application exited with an error (Code: %ERRORLEVEL%).
    echo ============================================================
    pause
)
