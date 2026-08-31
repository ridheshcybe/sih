#!/bin/bash
echo "Starting AeroTwin Digital Twin System..."
docker compose up -d --build
sleep 5
open http://localhost:3000 || xdg-open http://localhost:3000
echo "System is live at http://localhost:3000"