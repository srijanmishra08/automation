#!/bin/bash

# Start the WhatsApp Automation Backend
# Run this script to start the FastAPI server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

echo "🚀 Starting WhatsApp Automation Backend..."

# Check if virtual environment exists
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$BACKEND_DIR/venv"
fi

# Activate virtual environment
source "$BACKEND_DIR/venv/bin/activate"

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q -r "$BACKEND_DIR/requirements.txt"

# Check for .env file
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo "⚠️  No .env file found. Copying from .env.example..."
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    echo "⚠️  Please edit backend/.env with your credentials."
fi

# Create tasks directory
mkdir -p "$SCRIPT_DIR/tasks"

# Start the server
echo "🌐 Starting FastAPI server on http://localhost:8000"
echo "📚 API docs available at http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd "$BACKEND_DIR"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
