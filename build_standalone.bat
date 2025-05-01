@echo off
echo Building Standalone Clone Hero Video Downloader...
echo This may take a while since it needs to download and bundle ffmpeg.
python build_exe_standalone.py
echo.
echo If the build was successful, you'll find the standalone executable in the 'dist' folder.
echo This executable contains everything needed to run the program, including ffmpeg.
echo The console window has been hidden in the final executable.
echo.
pause 