#!/bin/bash

# Installation script for systemd services

echo "🔧 Installing Document Grading App systemd services..."

# Create grader user if it doesn't exist
echo "👤 Creating grader user..."
if ! id "grader" &>/dev/null; then
    sudo useradd --system --home-dir /opt/grading-app --shell /bin/false grader
    echo "✅ Created grader user"
else
    echo "ℹ️  grader user already exists"
fi

# Create log directory
echo "📁 Creating log directories..."
sudo mkdir -p /var/log/grading-app
sudo chown grader:grader /var/log/grading-app

# Create run directory
sudo mkdir -p /var/run/grading-app
sudo chown grader:grader /var/run/grading-app

# Copy systemd unit files
echo "📋 Installing systemd unit files..."
sudo cp grading-app.service /etc/systemd/system/
sudo cp grading-app-celery.service /etc/systemd/system/
sudo cp grading-app-celery-beat.service /etc/systemd/system/

# Set proper ownership and permissions
echo "🔐 Setting permissions..."
sudo chown -R grader:grader /opt/grading-app
sudo chmod +x /opt/grading-app/start_production.sh

# Reload systemd
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

# Enable services
echo "✅ Enabling services..."
sudo systemctl enable grading-app-celery.service
sudo systemctl enable grading-app-celery-beat.service
sudo systemctl enable grading-app.service

echo ""
echo "✅ Installation complete!"
echo ""
echo "To start the services:"
echo "  sudo systemctl start grading-app-celery"
echo "  sudo systemctl start grading-app-celery-beat"
echo "  sudo systemctl start grading-app"
echo ""
echo "To check service status:"
echo "  sudo systemctl status grading-app"
echo "  sudo systemctl status grading-app-celery"
echo "  sudo systemctl status grading-app-celery-beat"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u grading-app -f"
echo "  sudo journalctl -u grading-app-celery -f"