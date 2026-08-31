@echo off
REM ══════════════════════════════════════════════════════════════════════════════
REM Aero Piston Engine Digital Twin - One-Click Demo Launcher (Windows)
REM ══════════════════════════════════════════════════════════════════════════════
REM
REM This script launches the complete Digital Twin system and opens the
REM dashboard in your default browser.
REM
REM Usage:
REM   Double-click run_demo.bat
REM   OR: run_demo.bat
REM
REM ══════════════════════════════════════════════════════════════════════════════

setlocal enabledelayedexpansion

REM Set colors (Windows 10+)
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "BLUE=[94m"
set "CYAN=[96m"
set "NC=[0m"

REM Print banner
echo.
echo %CYAN%═══════════════════════════════════════════════════════════════════════════%NC%
echo %CYAN%   ____ _____     _           _    ____                                   %NC%
echo %CYAN%  / ___^|_   _^|__ ^| ^| _____  _^| ^|  / ___^| __ _ _ __ ___   ___  ___       %NC%
echo %CYAN% ^| ^|  _  ^| ^|/ _ \^| ^|/ / _ \^| ^| ^| ^|  _ / _` ^| '_ ` _ \ / _ \/ __^|      %NC%
echo %CYAN% ^| ^|_^| ^| ^| ^| (_) ^|   ^< (_) ^| ^| ^| ^|_^| ^| (_^| ^| ^| ^| ^| ^| ^|  __/\__ \      %NC%
echo %CYAN%  \____^| ^|_^|\___/^|_^|\_\___/^|_^|_^|  \____^|\__,_^|_^| ^|_^| ^|_^|\___^|^|___/      %NC%
echo %CYAN%                                                                          %NC%
echo %CYAN%        MALE UAV Aero-Engine Digital Twin (DRDO Tapas-BH-201)            %NC%
echo %CYAN%═══════════════════════════════════════════════════════════════════════════%NC%
echo.

REM Function to print status
call :print_status "Checking prerequisites..."

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo %RED%✗ Docker is not installed!%NC%
    echo Please install Docker Desktop from https://docs.docker.com/desktop/install/windows-install/
    pause
    exit /b 1
)
echo %GREEN%✓%NC% Docker is installed

REM Check if Docker Compose is available
docker compose version >nul 2>&1
if errorlevel 1 (
    docker-compose --version >nul 2>&1
    if errorlevel 1 (
        echo %RED%✗ Docker Compose is not installed!%NC%
        echo Please install Docker Compose from https://docs.docker.com/compose/install/
        pause
        exit /b 1
    )
    set "COMPOSE_CMD=docker-compose"
) else (
    set "COMPOSE_CMD=docker compose"
)
echo %GREEN%✓%NC% Docker Compose is available

REM Check if Docker daemon is running
docker info >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%⚠ Docker daemon is not running. Starting Docker Desktop...%NC%
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo Waiting for Docker to start...
    timeout /t 30 /nobreak >nul
    
    REM Check again
    docker info >nul 2>&1
    if errorlevel 1 (
        echo %RED%✗ Docker failed to start. Please start Docker Desktop manually.%NC%
        pause
        exit /b 1
    )
)
echo %GREEN%✓%NC% Docker daemon is running

echo.

REM Stop any existing containers
call :print_status "Stopping existing containers..."
%COMPOSE_CMD% down --remove-orphans >nul 2>&1
echo %GREEN%✓%NC% Existing containers stopped

REM Build and start services
echo.
call :print_status "Building and starting services..."
echo This may take a few minutes on first run...
echo.

%COMPOSE_CMD% up -d --build
if errorlevel 1 (
    echo %RED%✗ Failed to start services%NC%
    pause
    exit /b 1
)

echo.
echo %GREEN%✓%NC% All services started

REM Wait for services
echo.
call :print_status "Waiting for services to become ready..."

REM Wait for TimescaleDB
echo | set /p="  Waiting for TimescaleDB "
set /a "wait_time=0"
:wait_db
if %wait_time% geq 120 goto :db_timeout
%COMPOSE_CMD% exec -T timescaledb pg_isready -U postgres -d aerotwin >nul 2>&1
if not errorlevel 1 (
    echo %GREEN% ✓%NC%
    goto :wait_backend
)
echo -n .
timeout /t 2 /nobreak >nul
set /a "wait_time+=2"
goto :wait_db
:db_timeout
echo %RED% Timeout%NC%

:wait_backend
echo | set /p="  Waiting for Backend "
set /a "wait_time=0"
:wait_be
if %wait_time% geq 120 goto :be_timeout
curl -s http://localhost:8081/health >nul 2>&1
if not errorlevel 1 (
    echo %GREEN% ✓%NC%
    goto :wait_frontend
)
echo -n .
timeout /t 2 /nobreak >nul
set /a "wait_time+=2"
goto :wait_be
:be_timeout
echo %RED% Timeout%NC%

:wait_frontend
echo | set /p="  Waiting for Frontend "
set /a "wait_time=0"
:wait_fe
if %wait_time% geq 120 goto :fe_timeout
curl -s http://localhost:3000 >nul 2>&1
if not errorlevel 1 (
    echo %GREEN% ✓%NC%
    goto :services_ready
)
echo -n .
timeout /t 2 /nobreak >nul
set /a "wait_time+=2"
goto :wait_fe
:fe_timeout
echo %RED% Timeout%NC%

:services_ready
echo.
echo %GREEN%✓%NC% All services are ready

REM Open browser
echo.
call :print_status "Opening dashboard in browser..."
start http://localhost:3000

REM Print service info
echo.
echo %CYAN%═══════════════════════════════════════════════════════════════════════════%NC%
echo %CYAN%  Services Running%NC%
echo %CYAN%═══════════════════════════════════════════════════════════════════════════%NC%
echo.
echo   %GREEN%Dashboard:%NC%      http://localhost:3000
echo   %GREEN%WebSocket:%NC%      ws://localhost:8080
echo   %GREEN%REST API:%NC%       http://localhost:8081
echo   %GREEN%Database:%NC%       postgresql://localhost:5432/aerotwin
echo.
echo %CYAN%═══════════════════════════════════════════════════════════════════════════%NC%
echo.
echo   %YELLOW%Commands:%NC%
echo     View logs:      %COMPOSE_CMD% logs -f
echo     Stop services:  %COMPOSE_CMD% down
echo     Restart:        %COMPOSE_CMD% restart
echo.
echo %CYAN%═══════════════════════════════════════════════════════════════════════════%NC%
echo.

REM Keep window open
pause
exit /b 0

:print_status
echo %GREEN%✓%NC% %~1
goto :eof
