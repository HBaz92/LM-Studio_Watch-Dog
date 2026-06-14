@echo off
where python >nul 2>nul
if %errorlevel%==0 (
  python -m lm_studio_watchdog serve
  exit /b %errorlevel%
)

where py >nul 2>nul
if %errorlevel%==0 (
  py -m lm_studio_watchdog serve
  exit /b %errorlevel%
)

echo Python 3.10+ was not found. Install Python from https://www.python.org/downloads/ and try again.
exit /b 1
