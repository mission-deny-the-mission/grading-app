#!/bin/bash

# Document Grading Web App Startup Script

echo "Starting Document Grading Web App..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment and install dependencies
echo "Installing dependencies..."
venv/bin/pip install -r requirements.txt

# Start the Flask application
echo "Starting Flask application..."
echo "Access the app at: http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo ""

venv/bin/python app.py
