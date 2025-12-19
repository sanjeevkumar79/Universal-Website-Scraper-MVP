#!/bin/bash
set -e

echo "🚀 Starting Universal Website Scraper..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium

# Start FastAPI server
echo "✅ Starting server on http://localhost:8000"
uvicorn main:app --host 0.0.0.0 --port 8000
