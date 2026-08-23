@echo off
REM ReelGeek launcher for Windows -- double-click this file.
cd /d "%~dp0"
where python >nul 2>nul || (
  echo Python 3 is not installed. Get it from https://www.python.org/downloads/
  pause & exit /b 1
)
where ffmpeg >nul 2>nul || (
  echo ffmpeg is missing. Install it with:  winget install Gyan.FFmpeg
  echo Then close this window, open a new one, and try again.
  pause & exit /b 1
)
python -m pip install --quiet --disable-pip-version-check -r requirements.txt
python -m reelgeek
pause
