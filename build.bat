@echo off
rem Builds dist\FIFA14.exe (single-file installer + launcher).
rem Requires Python 3 with pyinstaller and pillow, and the payload\ folder (see README).
cd /d "%~dp0" || exit /b 1
if not exist payload\emulator\shadPS4.exe ( echo Missing payload\emulator\shadPS4.exe & exit /b 1 )
if not exist payload\game_patch\FIFA14-fix\FIFA14.xml ( echo Missing payload\game_patch\FIFA14-fix & exit /b 1 )
if not exist payload\extractor\pkg_extractor.exe ( echo Missing payload\extractor\pkg_extractor.exe & exit /b 1 )
python make_icon.py assets\app.ico || exit /b 1
python make_banner.py assets\banner.png || exit /b 1
python -m PyInstaller --noconfirm --clean --onefile --windowed --name FIFA14 ^
  --icon assets\app.ico ^
  --add-data "assets;assets" ^
  --add-data "payload;payload" ^
  --hidden-import PIL.Image ^
  --hidden-import PIL.ImageTk ^
  fifa14_pc.py || exit /b 1
echo BUILD OK: %~dp0dist\FIFA14.exe
