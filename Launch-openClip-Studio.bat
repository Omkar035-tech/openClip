@echo off
title openClip Studio Desktop Launcher
cd /d "%~dp0"
start "" "clipper\.venv\Scripts\pythonw.exe" -m clipper.desktop
exit
