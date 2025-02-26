@echo off
setlocal EnableDelayedExpansion

:: Get the directory where the batch file is located
set "APP_DIR=%~dp0"
set "PYTHON_SCRIPT=%APP_DIR%main.py"
set "VENV_DIR=%APP_DIR%venv"
set "FFMPEG_PATH=%APP_DIR%tools\ffmpeg.exe"

:: Check if Python script exists
if not exist "%PYTHON_SCRIPT%" (
    echo Error: Cannot find main.py in %APP_DIR%
    echo Please ensure you're running this batch file from the correct directory.
    pause
    exit /b 1
)

:: Check if FFmpeg exists
if not exist "%FFMPEG_PATH%" (
    echo Warning: FFmpeg not found in tools directory.
    echo The application will prompt you to download it if needed.
)

:: Check if virtual environment exists, create if it doesn't
if not exist "%VENV_DIR%" (
    echo Creating Python virtual environment...
    python -m venv "%VENV_DIR%"
    if !ERRORLEVEL! neq 0 (
        echo Error: Failed to create virtual environment.
        echo Please ensure Python is installed and available in PATH.
        pause
        exit /b 1
    )
)

:: Activate virtual environment and install requirements if needed
call "%VENV_DIR%\Scripts\activate.bat"
if !ERRORLEVEL! neq 0 (
    echo Error: Failed to activate virtual environment.
    pause
    exit /b 1
)

:: Check if requirements need to be installed
if not exist "%VENV_DIR%\Lib\site-packages\speech_recognition" (
    echo Installing required packages...
    pip install -r "%APP_DIR%requirements.txt"
    if !ERRORLEVEL! neq 0 (
        echo Error: Failed to install requirements.
        pause
        exit /b 1
    )
)

:: Run the application
echo Starting Audio to Text Converter...
python "%PYTHON_SCRIPT%"

:: Deactivate virtual environment
call "%VENV_DIR%\Scripts\deactivate.bat"

endlocal