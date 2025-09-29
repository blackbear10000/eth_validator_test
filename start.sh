#!/bin/bash

# ETH Validator Testing - Quick Start Script
# This script sets up and runs the complete validator lifecycle test

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}ETH Validator Lifecycle Testing${NC}"
echo -e "${BLUE}=====================================${NC}"

# Check dependencies
echo -e "${YELLOW}Checking dependencies...${NC}"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose >/dev/null 2>&1; then
    echo -e "${RED}❌ docker-compose not found. Please install Docker Compose.${NC}"
    exit 1
fi

# Check if Kurtosis is available
if ! command -v kurtosis >/dev/null 2>&1; then
    echo -e "${RED}❌ Kurtosis not found. Please install Kurtosis.${NC}"
    echo -e "${YELLOW}Install with: curl -fsSL https://docs.kurtosis.com/install | bash${NC}"
    exit 1
fi

# Check if Python is available
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All dependencies found${NC}"

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
cd scripts
if [ ! -f "venv/bin/activate" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Install eth2-deposit-cli from GitHub (optional for advanced features)
if [ ! -d "eth2-deposit-cli" ]; then
    echo -e "${YELLOW}Installing eth2-deposit-cli from GitHub...${NC}"
    git clone https://github.com/ethereum/staking-deposit-cli.git eth2-deposit-cli 2>/dev/null || echo "Note: eth2-deposit-cli clone skipped (optional)"
    if [ -d "eth2-deposit-cli" ]; then
        cd eth2-deposit-cli
        pip install -r requirements.txt 2>/dev/null || echo "Note: eth2-deposit-cli requirements install failed (optional)"
        cd ..
    fi
fi
cd ..

echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Create necessary directories
echo -e "${YELLOW}Setting up directories...${NC}"
mkdir -p keys deposits logs

# Make scripts executable
chmod +x scripts/*.py
chmod +x scripts/orchestrate.py

echo -e "${GREEN}✓ Setup completed${NC}"

# Parse command line arguments
COMMAND=${1:-full-test}

case $COMMAND in
    "full-test")
        echo -e "${BLUE}Running full validator lifecycle test...${NC}"
        cd scripts
        source venv/bin/activate
        python3 orchestrate.py full-test
        ;;
    "quick-start")
        echo -e "${BLUE}Quick start - infrastructure only...${NC}"
        cd scripts
        source venv/bin/activate
        python3 orchestrate.py start-infra
        ;;
    "cleanup")
        echo -e "${YELLOW}Cleaning up all services...${NC}"
        cd scripts
        source venv/bin/activate
        python3 orchestrate.py cleanup
        ;;
    "status")
        echo -e "${BLUE}Checking service status...${NC}"
        echo -e "${YELLOW}Docker containers:${NC}"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo
        echo -e "${YELLOW}Kurtosis enclaves:${NC}"
        kurtosis enclave ls || echo "No Kurtosis enclaves running"
        ;;
    "logs")
        echo -e "${BLUE}Showing service logs...${NC}"
        echo -e "${YELLOW}Docker Compose logs:${NC}"
        docker-compose logs --tail=50
        ;;
    "help")
        echo -e "${BLUE}ETH Validator Testing Commands:${NC}"
        echo ""
        echo -e "${GREEN}./start.sh full-test${NC}    - Run complete validator lifecycle test"
        echo -e "${GREEN}./start.sh quick-start${NC}  - Start infrastructure only"
        echo -e "${GREEN}./start.sh cleanup${NC}      - Stop and remove all services"
        echo -e "${GREEN}./start.sh status${NC}       - Show status of running services"
        echo -e "${GREEN}./start.sh logs${NC}         - Show service logs"
        echo -e "${GREEN}./start.sh help${NC}         - Show this help"
        echo ""
        echo -e "${YELLOW}Individual phases:${NC}"
        echo "cd scripts && source venv/bin/activate"
        echo "python3 orchestrate.py generate-keys"
        echo "python3 orchestrate.py create-deposits"
        echo "python3 orchestrate.py wait-activation"
        echo "python3 orchestrate.py monitor"
        echo "python3 orchestrate.py test-exit"
        echo "python3 orchestrate.py test-withdrawal"
        echo "python3 orchestrate.py generate-report"
        ;;
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        echo -e "${YELLOW}Use './start.sh help' to see available commands${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}✓ Operation completed${NC}"