@echo off
title Flask Stock App

cd /d %~dp0

call .venv\Scripts\activate

echo Starting Flask App...
echo.

python run.py

pause