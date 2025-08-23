#!/bin/bash

# Document Grading App - Full Service Startup Script

echo "🚀 Starting Document Grading App Services..."

# Ensure we run from the script's directory (repo root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Install dependencies
echo "📥 Installing dependencies..."
venv/bin/pip install -r requirements.txt

# Check if Redis is running
echo "🔍 Checking Redis status..."
if ! pgrep -x "valkey-server" > /dev/null && ! pgrep -x "redis-server" > /dev/null; then
    echo "⚠️  Valkey/Redis is not running. Please start Valkey first:"
    echo "   sudo systemctl start valkey"
    echo "   or"
    echo "   valkey-server"
    echo ""
    read -p "Press Enter to continue anyway (services may not work without Valkey/Redis)..."
fi

# Initialize database
echo "🗄️  Initializing database..."
export FLASK_APP=app.py
venv/bin/flask init-db

# Start Celery worker in background
echo "👷 Starting Celery worker..."
venv/bin/celery -A tasks worker --loglevel=info --concurrency=2 --queues=grading,maintenance &
CELERY_PID=$!

# Start Celery beat for scheduled tasks
echo "⏰ Starting Celery beat..."
venv/bin/celery -A tasks beat --loglevel=info &
BEAT_PID=$!

# Wait a moment for services to start
sleep 3

# Start Flask application
echo "🌐 Starting Flask application..."
echo "📱 Access the app at: http://localhost:5000"
echo "📊 Monitor jobs at: http://localhost:5000/jobs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $CELERY_PID 2>/dev/null
    kill $BEAT_PID 2>/dev/null
    echo "✅ Services stopped"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Start Flask app
venv/bin/python app.py

# Cleanup if Flask exits
cleanup
