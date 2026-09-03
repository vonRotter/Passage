@echo off
REM Passage -- start the game on Windows.
REM Double-click this file, or run it from a command prompt in this folder.

setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)

%PY% -c "import numpy, pygame" >nul 2>nul
if errorlevel 1 (
    echo Installing numpy and pygame, one moment...
    %PY% -m pip install --quiet numpy pygame
    if errorlevel 1 (
        echo.
        echo Could not install the two libraries Passage needs.
        echo Install Python 3.11 or newer from https://www.python.org/downloads/
        echo and make sure you tick "Add Python to PATH".
        echo.
        pause
        exit /b 1
    )
)

%PY% -m passage %*
if errorlevel 1 pause
endlocal
