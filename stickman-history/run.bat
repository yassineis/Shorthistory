@echo off
setlocal
cd /d "%~dp0"
title Stickman History

rem ---- 1. check the tools ----
set NEED_NODE=
set NEED_FFMPEG=
set NEED_PY=

where node >nul 2>nul
if errorlevel 1 set NEED_NODE=1
where ffmpeg >nul 2>nul
if errorlevel 1 set NEED_FFMPEG=1

set PY=
python -c "pass" >nul 2>nul
if not errorlevel 1 set PY=python
if not defined PY (
  py -c "pass" >nul 2>nul
  if not errorlevel 1 set PY=py
)
if not defined PY set NEED_PY=1

rem ---- 2. install what is missing (needs Windows 10/11 winget) ----
if defined NEED_NODE goto install
if defined NEED_FFMPEG goto install
if defined NEED_PY goto install
goto tools_ok

:install
where winget >nul 2>nul
if errorlevel 1 goto no_winget
echo.
echo Some tools are missing. Installing them now. Say Yes if Windows asks for permission.
echo.
if defined NEED_NODE (
  echo Installing Node.js...
  winget install -e --id OpenJS.NodeJS.LTS --silent --accept-package-agreements --accept-source-agreements
)
if defined NEED_PY (
  echo Installing Python...
  winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
)
if defined NEED_FFMPEG (
  echo Installing ffmpeg...
  winget install -e --id Gyan.FFmpeg --silent --accept-package-agreements --accept-source-agreements
)
echo.
echo Installation finished. Close this window, then double-click run.bat again.
echo Windows only sees the new programs in a fresh window.
pause
exit /b 0

:tools_ok
set PYTHON=%PY%

rem ---- 3. one-time setup ----
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

rem ---- 4. menu ----
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

:no_winget
echo.
echo Some tools are missing and the automatic installer (winget) is not available on this PC.
echo Please install these by hand, then run this file again:
if defined NEED_NODE echo   Node.js:  https://nodejs.org
if defined NEED_PY echo   Python 3: https://python.org  (tick "Add to PATH")
if defined NEED_FFMPEG echo   ffmpeg:   https://www.gyan.dev/ffmpeg/builds/  (add its bin folder to PATH)
pause
exit /b 1

:pip_failed
echo Could not install Pillow and numpy. Try running:  %PY% -m pip install pillow numpy
pause
exit /b 1

:end
endlocal
