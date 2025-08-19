#!/bin/bash

# Start Flask App in Development Container

echo "🚀 Starting Flask app in development container..."

# Check if we're in a dev container or if containers are running
if [ -f /.dockerenv ]; then
    echo "✅ Running inside container, starting Flask app..."
    python app.py
else
    echo "📦 Starting Flask web service..."
    docker-compose -f docker-compose.dev.yml --profile web up -d
    
    echo ""
    echo "✅ Flask app started!"
    echo "🌐 Access the app at: http://localhost:5001"
    echo ""
    echo "To view logs: docker-compose -f docker-compose.dev.yml logs -f web"
    echo "To stop: docker-compose -f docker-compose.dev.yml stop web"
fi
