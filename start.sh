#!/bin/bash

echo "Starting YouTube Downloader Server..."
echo

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment."
        exit 1
    fi
fi

# Activate venv
source .venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -q

# Load .env file if it exists
if [ -f ".env" ]; then
    echo "Loading environment variables from .env..."
    export $(grep -v '^#' .env | xargs)
fi

# Start server
echo
echo "Server starting at http://127.0.0.1:8000"
echo "Press CTRL+C to stop"
echo
uvicorn main:app --reload
