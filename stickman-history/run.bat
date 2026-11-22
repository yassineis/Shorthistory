@echo off
setlocal
cd /d "%~dp0"
title Stickman History

rem ---- 1. check the tools ----
where node >nul 2>nul
if errorlevel 1 goto no_node
where ffmpeg >nul 2>nul
if errorlevel 1 goto no_ffmpeg

set PY=
where python >nul 2>nul
if not errorlevel 1 set PY=python
if not defined PY (
  where py >nul 2>nul
  if not errorlevel 1 set PY=py
)
if not defined PY goto no_python
set PYTHON=%PY%

rem ---- 2. one-time setup ----
%PY% -c "import PIL, numpy" >nul 2>nul
if errorlevel 1 (
  echo Installing Pillow and numpy, one time only...
  %PY% -m pip install pillow numpy
  if errorlevel 1 goto pip_failed
)
if not exist .env (
  copy .env.example .env >nul
  echo.
  echo A file called .env will open. Paste your free Gemini key after GEMINI_API_KEY=
  echo Get the key at https://aistudio.google.com/apikey then save and close Notepad.
  pause
  notepad .env
)

rem ---- 3. menu ----
:menu
echo.
echo ===== Stickman History =====
echo  1  Sample: first scene only, to check voice and style
echo  2  Full video, 16:9
echo  3  Full video, vertical 9:16 for Shorts
echo  4  Test run with placeholder voice, no key needed
echo  5  Voice test only
echo  6  Exit
echo.
choice /c 123456 /n /m "Choose 1-6: "
if errorlevel 6 goto end
if errorlevel 5 goto voice
if errorlevel 4 goto dry
if errorlevel 3 goto vertical
if errorlevel 2 goto full
goto sample

:sample
node src\make.js scripts\printing-press.json --sample
if errorlevel 1 goto failed
start "" "out\printing-press"
goto menu

:full
node src\make.js scripts\printing-press.json
if errorlevel 1 goto failed
start "" "out\printing-press"
goto menu

:vertical
node src\make.js scripts\printing-press.json --aspect 9:16 --out out\printing-press-vertical
if errorlevel 1 goto failed
start "" "out\printing-press-vertical"
goto menu

:dry
node src\make.js scripts\printing-press.json --dry-voice --out out\dry-test
if errorlevel 1 goto failed
start "" "out\dry-test"
goto menu

:voice
node src\voice.js "In the fourteen forties, a goldsmith named Johannes Gutenberg had an idea." out\voice-test.mp3
if errorlevel 1 goto failed
start "" "out\voice-test.mp3"
goto menu

:failed
echo.
echo Something went wrong. Read the error above. If it mentions rate limits, wait a minute and run again:
echo finished scenes are saved and will be skipped.
goto menu

:no_node
echo Node.js was not found. Install it from https://nodejs.org then run this file again.
pause
exit /b 1

:no_ffmpeg
echo ffmpeg was not found. Install it from https://ffmpeg.org and add it to your PATH, then run this file again.
pause
exit /b 1

:no_python
echo Python was not found. Install Python 3 from https://python.org, tick "Add to PATH", then run this file again.
pause
exit /b 1

:pip_failed
echo Could not install Pillow and numpy. Try running:  %PY% -m pip install pillow numpy
pause
exit /b 1

:end
endlocal
