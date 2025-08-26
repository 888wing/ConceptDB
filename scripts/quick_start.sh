#!/bin/bash

# ConceptDB Quick Start Script - One-click setup
set -e

echo "🚀 Starting ConceptDB - Evolutionary Concept-Type Database"
echo "=================================================="

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed."
    exit 1
fi

echo "✅ Prerequisites checked"

# Create directories
echo "📁 Creating necessary directories..."
mkdir -p data logs pg_data qdrant_data

# Create .env if needed
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# ConceptDB Configuration
LOG_LEVEL=INFO
EVOLUTION_PHASE=1
CONCEPT_RATIO=0.1
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=conceptdb
POSTGRES_USER=concept_user
POSTGRES_PASSWORD=concept_pass
QDRANT_HOST=localhost
QDRANT_PORT=6333
DATABASE_PATH=./data/concepts.db
EOF
fi

# Build and start
echo "🐳 Building and starting services..."
docker-compose down 2>/dev/null || true
docker-compose build
docker-compose up -d

# Wait for health
echo "⏳ Waiting for services..."
sleep 10

# Check services
check_service() {
    if curl -sf "$2" > /dev/null 2>&1; then
        echo "✅ $1 is ready"
    else
        echo "⚠️  $1 is starting..."
    fi
}

check_service "Qdrant" "http://localhost:6333/health"
check_service "API" "http://localhost:8000/health"
check_service "Studio" "http://localhost:3000"

echo ""
echo "=================================================="
echo "🎉 ConceptDB is running!"
echo "=================================================="
echo ""
echo "📊 Access points:"
echo "  • Web Studio:    http://localhost:3000"
echo "  • API Docs:      http://localhost:8000/docs"
echo "  • Qdrant UI:     http://localhost:6333/dashboard"
echo ""
echo "🛑 To stop: docker-compose down"
echo "📖 View logs: docker-compose logs -f"