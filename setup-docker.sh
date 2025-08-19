#!/bin/bash

# Grading App Docker Setup Script

set -e

echo "🚀 Setting up Grading App with Docker..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "✅ .env file created. Please edit it with your API keys."
else
    echo "✅ .env file already exists."
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p uploads instance

# Set proper permissions
echo "🔐 Setting proper permissions..."
chmod 755 uploads instance

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo ""
echo "For Production:"
echo "  make build"
echo "  make up"
echo ""
echo "For Development with Dev Containers:"
echo "  1. Open VS Code"
echo "  2. Install 'Dev Containers' extension"
echo "  3. Press Ctrl+Shift+P and select 'Dev Containers: Reopen in Container'"
echo ""
echo "For Development with Docker Compose:"
echo "  make dev"
echo ""
echo "For more information, see README-Docker.md"
echo ""
