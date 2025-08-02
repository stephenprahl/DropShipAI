#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Setting up Super Arbitrage environment...${NC}"

# Check if Python 3.8+ is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}❌ Python 3 is required but not installed. Please install Python 3.8 or higher.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print("{}.{}".format(sys.version_info.major, sys.version_info.minor))')
if [[ "$PYTHON_VERSION" < "3.8" ]]; then
    echo -e "${YELLOW}❌ Python 3.8 or higher is required. Found Python $PYTHON_VERSION.${NC}"
    exit 1
fi

# Create virtual environment
echo -e "${GREEN}Creating virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo -e "${GREEN}Upgrading pip...${NC}"
pip install --upgrade pip

# Install dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install -r requirements.txt

# Install development dependencies
echo -e "${GREEN}Installing development dependencies...${NC}"
pip install -e ".[dev]"

# Create necessary directories
echo -e "${GREEN}Creating directories...${NC}"
mkdir -p data/logs
mkdir -p data/screenshots

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "${GREEN}Creating .env file...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please update the .env file with your API keys and configuration.${NC}"
else
    echo -e "${GREEN}.env file already exists.${NC}"
fi

# Initialize the database
echo -e "${GREEN}Initializing database...${NC}"
python -c "from src.utils.database import Database; Database().initialize_database()"

echo -e "${GREEN}✅ Setup complete!${NC}"
echo -e "${YELLOW}To activate the virtual environment, run: source venv/bin/activate${NC}"
echo -e "${YELLOW}To run the arbitrage system: python run_arbitrage.py${NC}"
echo -e "${YELLOW}To run tests: python run_tests.py${NC}"
