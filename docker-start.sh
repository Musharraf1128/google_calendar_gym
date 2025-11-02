#!/bin/bash
# Docker startup script for Google Calendar Gym

echo "=========================================="
echo "Google Calendar Gym - Docker Startup"
echo "=========================================="

# Check if user is in docker group
if ! groups | grep -q docker; then
    echo "⚠️  You need Docker permissions!"
    echo ""
    echo "Run one of these commands:"
    echo "  1. Add yourself to docker group: sudo usermod -aG docker $USER"
    echo "  2. Then log out and log back in"
    echo "  3. Or use: sudo docker-compose up --build"
    echo ""
    exit 1
fi

# Clean up any existing containers
echo "🧹 Cleaning up old containers..."
docker-compose down -v 2>/dev/null || true

# Remove old database if it exists
if [ -f "backend/gym_calendar.db" ]; then
    echo "🗑️  Removing old database..."
    rm backend/gym_calendar.db
fi

# Build and start services
echo "🏗️  Building and starting services..."
docker-compose up --build

echo ""
echo "=========================================="
echo "✅ Application started successfully!"
echo ""
echo "Access the application at:"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo "=========================================="
