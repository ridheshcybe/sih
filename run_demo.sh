#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# Aero Piston Engine Digital Twin - One-Click Demo Launcher
# ══════════════════════════════════════════════════════════════════════════════
#
# This script launches the complete Digital Twin system and opens the
# dashboard in your default browser.
#
# Usage:
#   chmod +x run_demo.sh
#   ./run_demo.sh
#
# ══════════════════════════════════════════════════════════════════════════════

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print banner
echo -e "${CYAN}"
echo "═══════════════════════════════════════════════════════════════════════════"
echo "   ____ _____     _           _    ____                                   "
echo "  / ___|_   _|__ | | _____  _| |  / ___| __ _ _ __ ___   ___  ___       "
echo " | |  _  | |/ _ \\| |/ / _ \\| | | |  _ / _\` | '_ \` _ \\ / _ \\/ __|      "
echo " | |_| | | | (_) |   < (_) | | | | |_| | (_| | | | | | |  __/\\__ \\      "
echo "  \\____| |_|\\___/|_|\\_\\___/|_|_|  \\____|\\__,_|_| |_| |_|\\___||___/      "
echo "                                                                          "
echo "        MALE UAV Aero-Engine Digital Twin (DRDO Tapas-BH-201)            "
echo "═══════════════════════════════════════════════════════════════════════════"
echo -e "${NC}"

# Function to print status messages
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed!"
        echo "Please install Docker from https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed!"
        echo "Please install Docker Compose from https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    print_status "Docker is installed"
}

# Check if Docker daemon is running
check_docker_daemon() {
    if ! docker info &> /dev/null; then
        print_warning "Docker daemon is not running. Attempting to start..."
        
        # Try to start Docker (macOS)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            open -a Docker
            echo "Waiting for Docker to start..."
            sleep 10
            
            # Wait for Docker to be ready
            for i in {1..30}; do
                if docker info &> /dev/null; then
                    break
                fi
                sleep 2
            done
        else
            print_error "Please start Docker daemon manually"
            exit 1
        fi
    fi
    
    print_status "Docker daemon is running"
}

# Stop any existing containers
stop_existing() {
    print_info "Stopping any existing containers..."
    docker-compose down --remove-orphans 2>/dev/null || true
    print_status "Existing containers stopped"
}

# Build and start services
start_services() {
    print_info "Building and starting services..."
    echo ""
    
    # Build and start in detached mode
    docker-compose up -d --build
    
    echo ""
    print_status "All services started"
}

# Wait for services to be healthy
wait_for_services() {
    print_info "Waiting for services to become healthy..."
    echo ""
    
    local max_wait=120
    local wait_time=0
    
    # Wait for TimescaleDB
    echo -n "  Waiting for TimescaleDB "
    while [ $wait_time -lt $max_wait ]; do
        if docker-compose exec -T timescaledb pg_isready -U postgres -d aerotwin &> /dev/null; then
            echo -e " ${GREEN}✓${NC}"
            break
        fi
        echo -n "."
        sleep 2
        wait_time=$((wait_time + 2))
    done
    
    # Wait for Backend
    echo -n "  Waiting for Backend "
    wait_time=0
    while [ $wait_time -lt $max_wait ]; do
        if curl -s http://localhost:8081/health &> /dev/null; then
            echo -e " ${GREEN}✓${NC}"
            break
        fi
        echo -n "."
        sleep 2
        wait_time=$((wait_time + 2))
    done
    
    # Wait for Frontend
    echo -n "  Waiting for Frontend "
    wait_time=0
    while [ $wait_time -lt $max_wait ]; do
        if curl -s http://localhost:3000 &> /dev/null; then
            echo -e " ${GREEN}✓${NC}"
            break
        fi
        echo -n "."
        sleep 2
        wait_time=$((wait_time + 2))
    done
    
    echo ""
    print_status "All services are healthy"
}

# Open browser
open_browser() {
    local url="http://localhost:3000"
    
    print_info "Opening dashboard in browser..."
    
    # Detect OS and open browser
    case "$OSTYPE" in
        darwin*)
            open "$url"
            ;;
        linux*)
            if command -v xdg-open &> /dev/null; then
                xdg-open "$url"
            elif command -v gnome-open &> /dev/null; then
                gnome-open "$url"
            else
                print_warning "Could not auto-open browser. Please navigate to: $url"
            fi
            ;;
        msys*|cygwin*|mingw*)
            start "$url"
            ;;
        *)
            print_warning "Could not auto-open browser. Please navigate to: $url"
            ;;
    esac
}

# Print service status
print_status_info() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  Services Running${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${GREEN}Dashboard:${NC}      http://localhost:3000"
    echo -e "  ${GREEN}WebSocket:${NC}      ws://localhost:8080"
    echo -e "  ${GREEN}REST API:${NC}       http://localhost:8081"
    echo -e "  ${GREEN}Database:${NC}       postgresql://localhost:5432/aerotwin"
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${YELLOW}Commands:${NC}"
    echo -e "    View logs:      docker-compose logs -f"
    echo -e "    Stop services:  docker-compose down"
    echo -e "    Restart:        docker-compose restart"
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Main execution
main() {
    echo ""
    
    # Run checks
    check_docker
    check_docker_daemon
    
    echo ""
    
    # Stop existing containers
    stop_existing
    
    # Build and start services
    start_services
    
    # Wait for services
    wait_for_services
    
    # Open browser
    open_browser
    
    # Print status
    print_status_info
}

# Handle script interruption
trap 'echo -e "\n${RED}Script interrupted${NC}"; exit 1' INT TERM

# Run main function
main
