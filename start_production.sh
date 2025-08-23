#!/bin/bash

# Document Grading App - Production Service Startup Script
# This script assumes deployment to /opt/grading-app

cd /opt/grading-app
echo "🚀 Starting Document Grading App Production Services..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Install dependencies
echo "📥 Installing dependencies..."
venv/bin/pip install -r requirements.txt

# Install production dependencies
echo "📦 Installing Gunicorn..."
venv/bin/pip install gunicorn

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
venv/bin/flask init-db

# Start Celery worker in background
echo "👷 Starting Celery worker..."
venv/bin/celery -A tasks worker --loglevel=info --concurrency=8 --queues=grading,maintenance &
CELERY_PID=$!

# Start Celery beat for scheduled tasks
echo "⏰ Starting Celery beat..."
venv/bin/celery -A tasks beat --loglevel=info &
BEAT_PID=$!

# Wait a moment for services to start
sleep 3

# Start Gunicorn application server
echo "🌐 Starting Gunicorn application server..."
echo "📱 Access the app at: http://localhost:8000"
echo "📊 Monitor jobs at: http://localhost:8000/jobs"
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

# Start Gunicorn with production settings
venv/bin/gunicorn --config gunicorn.conf.py app:app

# Cleanup if Gunicorn exits
cleanup