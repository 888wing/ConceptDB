#!/bin/bash

# ConceptDB Demo Environment Startup Script

echo "🚀 Starting ConceptDB Demo Environment..."
echo "==========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Stop any existing containers
echo "📦 Stopping existing containers..."
docker-compose down

# Start services
echo "🔧 Starting services..."
docker-compose up -d postgres qdrant

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

# Check PostgreSQL health
until docker-compose exec postgres pg_isready -U concept_user -d conceptdb &> /dev/null; do
    echo "   PostgreSQL is starting up..."
    sleep 2
done
echo "✅ PostgreSQL is ready!"

# Check Qdrant health
echo "⏳ Waiting for Qdrant to be ready..."
until curl -f http://localhost:6333/health &> /dev/null; do
    echo "   Qdrant is starting up..."
    sleep 2
done
echo "✅ Qdrant is ready!"

# Start API server (if Python environment is set up)
if [ -f "requirements.txt" ]; then
    echo "🐍 Starting API server..."
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment and install dependencies
    source venv/bin/activate
    pip install -q -r requirements.txt
    
    # Start API server in background
    uvicorn src.api.main:app --reload --port 8000 &
    API_PID=$!
    
    # Wait for API to be ready
    echo "⏳ Waiting for API server to be ready..."
    sleep 5
    until curl -f http://localhost:8000/health &> /dev/null; do
        echo "   API server is starting up..."
        sleep 2
    done
    echo "✅ API server is ready!"
else
    echo "⚠️  Python requirements.txt not found. Skipping API server."
fi

# Start Web Studio (if Node.js is set up)
if [ -f "studio/package.json" ]; then
    echo "🎨 Starting Web Studio..."
    cd studio
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo "Installing Node.js dependencies..."
        npm install
    fi
    
    # Start studio in background
    npm run dev &
    STUDIO_PID=$!
    
    echo "⏳ Waiting for Web Studio to be ready..."
    sleep 10
    echo "✅ Web Studio is starting at http://localhost:3000"
    
    cd ..
else
    echo "⚠️  studio/package.json not found. Skipping Web Studio."
fi

echo ""
echo "==========================================="
echo "🎉 ConceptDB Demo Environment is Ready!"
echo "==========================================="
echo ""
echo "📊 Service Status:"
echo "   PostgreSQL:  http://localhost:5432"
echo "   Qdrant:      http://localhost:6333"
echo "   API Server:  http://localhost:8000"
echo "   Web Studio:  http://localhost:3000"
echo ""
echo "🔧 Quick Commands:"
echo "   Query via CLI:  conceptdb query \"find similar products\""
echo "   Check status:   conceptdb status"
echo "   Stop services:  docker-compose down"
echo ""
echo "📚 Documentation: https://github.com/yourusername/conceptdb"
echo ""
echo "Press Ctrl+C to stop all services..."

# Keep script running
wait