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
if not exist node_modules\kokoro-js (
  echo Installing the free voice engine Kokoro, one time only...
  call npm install --no-audit --no-fund
  if errorlevel 1 goto npm_failed
)
if not exist out\.voice_ready (
  echo Downloading the free voice model, one time only, about 330 MB. Please wait...
  if not exist out mkdir out
  node src\voice.js "Voice ready." out\warmup.mp3
  if errorlevel 1 goto voice_failed
  echo ok> out\.voice_ready
)
if not exist .env (
  copy .env.example .env >nul
  echo.
  echo A file called .env will open. Paste your free Gemini key after GEMINI_API_KEY=
  echo The key is only used to WRITE the stories. The voice is free and offline.
  echo Get the key at https://aistudio.google.com/apikey then save and close Notepad.
  pause
  notepad .env
)

rem ---- 4. menu ----
:menu
echo.
echo ===== Stickman History =====
echo  1  Make history shorts (it asks how many, about 1:10 to 1:30 each)
echo  2  Make history shorts, vertical 9:16
echo  3  Show the story library (made and still to make)
echo  4  Test run with no key: placeholder story and voice, 1 video
echo  5  Voice test only
echo  6  Old sample: printing press explainer, first scene
echo  7  Remake a story already made ^(it shows them and asks which one^)
echo  8  Storybook sketches: the 5 prototype videos with voice and music
echo  9  Exit
echo.
choice /c 123456789 /n /m "Choose 1-9: "
if errorlevel 9 goto end
if errorlevel 8 goto sketches
if errorlevel 7 goto redo
if errorlevel 6 goto sample
if errorlevel 5 goto voice
if errorlevel 4 goto dry
if errorlevel 3 goto list
if errorlevel 2 goto shortsv
goto shorts

:shorts
node src\shorts.js
if errorlevel 1 goto failed
if exist "out\shorts" start "" "out\shorts"
goto menu

:shortsv
node src\shorts.js --aspect 9:16
if errorlevel 1 goto failed
if exist "out\shorts" start "" "out\shorts"
goto menu

:list
node src\shorts.js --list
goto menu

:dry
node src\shorts.js --count 1 --yes --mock-story --dry-voice --height 360 --no-music --topic "Test story"
if errorlevel 1 goto failed
if exist "out\shorts" start "" "out\shorts"
goto menu

:redo
node src\shorts.js --redo
if errorlevel 1 goto failed
if exist "out\shorts" start "" "out\shorts"
goto menu

:sketches
node src\sketches.js
if errorlevel 1 goto failed
if exist "out\sketches" start "" "out\sketches"
goto menu

:sample
node src\make.js scripts\printing-press.json --sample
if errorlevel 1 goto failed
start "" "out\printing-press"
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
echo Some tools are missing and the automatic installer ^(winget^) is not available on this PC.
echo Please install these by hand, then run this file again:
if defined NEED_NODE echo   Node.js:  https://nodejs.org
if defined NEED_PY echo   Python 3: https://python.org  ^(tick "Add to PATH"^)
if defined NEED_FFMPEG echo   ffmpeg:   https://www.gyan.dev/ffmpeg/builds/  ^(add its bin folder to PATH^)
pause
exit /b 1

:voice_failed
echo Could not download the voice model. Check your internet connection, then run this file again.
pause
exit /b 1

:npm_failed
echo Could not install the voice engine. Check your internet connection and run:  npm install
pause
exit /b 1

:pip_failed
echo Could not install Pillow and numpy. Try running:  %PY% -m pip install pillow numpy
pause
exit /b 1

:end
endlocal
