@echo off
echo Starting AeroTwin Digital Twin System...
docker compose up -d --build
timeout /t 5 >nul
start http://localhost:3000
echo System is live at http://localhost:3000