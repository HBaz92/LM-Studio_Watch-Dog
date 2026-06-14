@echo off
where python >nul 2>nul
if %errorlevel%==0 (
  set PYTHON_CMD=python
) else (
  where py >nul 2>nul
  if %errorlevel%==0 (
    set PYTHON_CMD=py
  ) else (
    echo Python 3.10+ was not found. Install Python from https://www.python.org/downloads/ and try again.
    exit /b 1
  )
)

%PYTHON_CMD% -m pip install -r requirements.txt
if not %errorlevel%==0 exit /b %errorlevel%

%PYTHON_CMD% -m pip install -r requirements-dev.txt
if not %errorlevel%==0 exit /b %errorlevel%

%PYTHON_CMD% -m PyInstaller --noconfirm --clean LM-Studio-WatchDog.spec
if not %errorlevel%==0 exit /b %errorlevel%

echo.
echo Portable EXE created at: dist\LM-Studio-WatchDog.exe
