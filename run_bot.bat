@echo off
echo =========================================
echo 🐕 Starting Crypto Trading Bot...
echo =========================================
echo.
echo 📦 Checking and installing required packages...
pip install fastapi uvicorn httpx numpy jinja2 pydantic google-generativeai python-multipart python-dotenv
echo.
echo 🚀 Starting the FastApi server...
python main.py
pause