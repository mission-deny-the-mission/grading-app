#!/bin/bash

# Grading App Spec-Driven Development Setup Script
# This script sets up the simplified Spec Kit CLI for the grading app project

set -e

echo "🚀 Setting up Spec-Driven Development for Grading App..."

# Check if we're in the right directory
if [ ! -f "app.py" ] || [ ! -f "models.py" ]; then
    echo "❌ Error: Please run this script from the grading-app root directory"
    exit 1
fi

# Install Click for CLI functionality
echo "📦 Installing required dependencies..."
pip install click

# Create symlink for easier access
if [ ! -L "/usr/local/bin/specify" ]; then
    echo "🔗 Creating symlink for specify command..."
    sudo ln -sf "$(pwd)/specify_cli.py" /usr/local/bin/specify 2>/dev/null || {
        echo "⚠️  Could not create system-wide symlink. Adding local alias instead..."
        echo "alias specify='python $(pwd)/specify_cli.py'" >> ~/.bashrc
        echo "alias specify='python $(pwd)/specify_cli.py'" >> ~/.zshrc 2>/dev/null || true
    }
fi

# Make the CLI executable
chmod +x specify_cli.py

# Clean up temporary files
echo "🧹 Cleaning up temporary files..."
rm -rf temp-spec-kit

# Initialize the project
echo "🏗️  Initializing Spec-Driven Development..."
python specify_cli.py init --here

echo ""
echo "✅ Spec-Driven Development setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Start your AI coding agent in this directory"
echo "2. Use the following slash commands:"
echo "   /constitution - View/modify project principles"
echo "   /specify - Define what you want to build"
echo "   /plan - Create technical implementation plans"
echo "   /tasks - Generate actionable task lists"
echo "   /implement - Execute implementation"
echo ""
echo "🔧 Available commands:"
echo "   specify check    - Check system requirements"
echo "   specify status   - Show current status"
echo "   specify init     - Initialize new project"
echo ""
echo "📁 Created files:"
echo "   - .specify/           - Spec-Driven Development directory"
echo "   - .specify/memory/    - Constitution and project memory"
echo "   - .specify/specs/     - Feature specifications"
echo "   - .specify/templates/ - Reusable templates"
echo "   - specify_cli.py      - Simplified CLI tool"
