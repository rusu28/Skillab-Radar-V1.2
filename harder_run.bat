@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title SKILLAB Skill Radar Advanced Runner

set "PYTHON_CMD="
set "INTERACTIVE=0"
where py >nul 2>nul
if %ERRORLEVEL%==0 set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD (
  where python >nul 2>nul
  if %ERRORLEVEL%==0 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
  echo Python was not found.
  echo Install Python 3 from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating local virtual environment...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 (
    echo Failed to create .venv.
    pause
    exit /b 1
  )
)

set "VENV_PY=.venv\Scripts\python.exe"
set "DEPS_MARKER=.venv\.skillradar_deps_installed"

if "%~1"=="" (
  set "INTERACTIVE=1"
  goto menu
)
goto :dispatch

:menu
echo.
echo SKILLAB Skill Radar - Advanced Runner
echo =====================================
echo 1. Setup / auto-configure this PC
echo 2. Run pipeline and regenerate outputs
echo 3. Start Streamlit dashboard
echo 4. Run tests
echo 5. Full local rebuild: setup + pipeline + tests
echo 6. Start Jupyter notebooks
echo 0. Exit
echo.
set /p choice="Choose: "
if "%choice%"=="1" goto setup
if "%choice%"=="2" goto pipeline
if "%choice%"=="3" goto dashboard
if "%choice%"=="4" goto tests
if "%choice%"=="5" goto full
if "%choice%"=="6" goto notebooks
if "%choice%"=="0" goto end
echo Unknown option.
goto menu

:dispatch
if /I "%~1"=="setup" goto setup
if /I "%~1"=="pipeline" goto pipeline
if /I "%~1"=="dashboard" goto dashboard
if /I "%~1"=="tests" goto tests
if /I "%~1"=="full" goto full
if /I "%~1"=="notebooks" goto notebooks
echo Unknown command: %~1
echo Valid commands: setup pipeline dashboard tests full notebooks
exit /b 1

:setup
call :confirm_setup
if errorlevel 1 goto done
"%VENV_PY%" -m pip install -r requirements.txt
type nul > "%DEPS_MARKER%"
"%VENV_PY%" auto_config.py --smoke-test
goto done

:pipeline
call :confirm_pipeline
if errorlevel 1 goto done
call :ensure_deps
"%VENV_PY%" -m src.pipeline --config config.yaml
goto done

:dashboard
call :ensure_deps
"%VENV_PY%" -m streamlit run app/streamlit_app.py
goto done

:notebooks
call :ensure_deps
"%VENV_PY%" -m pip install -r requirements.txt
type nul > "%DEPS_MARKER%"
"%VENV_PY%" -m notebook notebooks
goto done

:tests
call :ensure_deps
"%VENV_PY%" -m unittest discover -s tests
goto done

:full
call :confirm_full
if errorlevel 1 goto done
"%VENV_PY%" -m pip install -r requirements.txt
type nul > "%DEPS_MARKER%"
"%VENV_PY%" auto_config.py --smoke-test
"%VENV_PY%" -m src.pipeline --config config.yaml
"%VENV_PY%" -m unittest discover -s tests
goto done

:done
echo.
echo Done.
if "%INTERACTIVE%"=="1" pause
goto end

:ensure_deps
if not exist "%DEPS_MARKER%" (
  echo Installing Python requirements into .venv...
  "%VENV_PY%" -m pip install -r requirements.txt
  if errorlevel 1 exit /b 1
  type nul > "%DEPS_MARKER%"
)
exit /b 0

:confirm_setup
if not "%INTERACTIVE%"=="1" exit /b 0
echo.
echo Are you sure you want to continue?
echo This will create/use .venv, install Python packages from requirements.txt,
echo update .env/config.yaml, and check local ESCO mapping paths.
set /p ans="Continue? (y/N): "
if /I "%ans%"=="y" exit /b 0
if /I "%ans%"=="yes" exit /b 0
echo Cancelled.
exit /b 1

:confirm_pipeline
if not "%INTERACTIVE%"=="1" exit /b 0
echo.
echo Are you sure you want to regenerate outputs?
echo This reads/writes data/cache, data/raw, results/csv, results/figures,
echo report, pitch outline, and submission manifest. It may call the Tracker API
echo if cache entries are missing.
set /p ans="Continue? (y/N): "
if /I "%ans%"=="y" exit /b 0
if /I "%ans%"=="yes" exit /b 0
echo Cancelled.
exit /b 1

:confirm_full
if not "%INTERACTIVE%"=="1" exit /b 0
echo.
echo Are you sure you want full rebuild?
echo This installs packages, auto-configures this PC, regenerates outputs,
echo and runs tests. It can take several minutes.
set /p ans="Continue? (y/N): "
if /I "%ans%"=="y" exit /b 0
if /I "%ans%"=="yes" exit /b 0
echo Cancelled.
exit /b 1

:end
endlocal
