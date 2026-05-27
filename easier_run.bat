@echo off
setlocal
cd /d "%~dp0"
title SKILLAB Innovation Challenge Configurer

echo.
echo ============================================================
echo   SKILLAB Innovation Challenge Configurer
echo   Project: Skill Radar
echo ============================================================
echo.
echo This helper prepares this PC to run the project.
echo.
echo What it will do:
echo   1. Find Python on this computer.
echo      - Needed because the analytics pipeline and Streamlit app are Python-based.
echo.
echo   2. Create or reuse the local virtual environment: .venv
echo      - Keeps project packages separate from global Python packages.
echo.
echo   3. Install packages from requirements.txt
echo      - Includes pandas, requests, matplotlib, seaborn, Streamlit, Jupyter, etc.
echo.
echo   4. Run auto_config.py
echo      - Finds the ESCO Excel mapping files.
echo      - Updates config.yaml with local paths.
echo      - Creates/keeps .env with SKILLAB Tracker API credentials.
echo      - Checks that important Python imports work.
echo.
echo It will NOT delete your data.
echo It may download/install Python packages from the internet.
echo.
echo After this finishes, useful commands are:
echo   harder_run.bat pipeline    - regenerate CSVs and figures
echo   harder_run.bat dashboard   - open Streamlit dashboard
echo   harder_run.bat notebooks   - open notebook fallback
echo   harder_run.bat tests       - run validation tests
echo.

set /p ans="Continue with configuration? (y/N): "
if /I not "%ans%"=="y" if /I not "%ans%"=="yes" (
  echo.
  echo Cancelled. Nothing was changed.
  pause
  exit /b 1
)

echo.
echo Starting setup...
call harder_run.bat setup
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
  echo Configuration finished.
  echo Next recommended command: harder_run.bat dashboard
) else (
  echo Configuration failed with exit code %EXIT_CODE%.
  echo Check the messages above. Most common issue: Python is missing from PATH.
)
echo.
pause
exit /b %EXIT_CODE%
