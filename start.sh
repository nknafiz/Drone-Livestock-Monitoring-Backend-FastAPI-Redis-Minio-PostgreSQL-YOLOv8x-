#!/bin/bash
# Production startup script with proper error handling

set -e

echo "🚀 Starting Drone Livestock Monitoring Backend..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please copy .env.example to .env and configure it"
    exit 1
fi

# Load environment
export $(cat .env | grep -v '^#' | xargs)

# Check required environment variables
required_vars=("DATABASE_URL" "REDIS_URL" "MINIO_URL" "JWT_SECRET_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Missing required environment variable: $var"
        exit 1
    fi
done

echo "✅ Environment validated"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi

echo "✅ Docker is available"

# Build images
echo "📦 Building Docker images..."
docker-compose build

# Start services
echo "🐳 Starting services..."
if [ "$1" == "prod" ]; then
    docker-compose -f docker-compose.prod.yml up -d
    echo "📍 Production mode"
else
    docker-compose up -d
    echo "📍 Development mode"
fi

# Wait for services
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check health
echo "🏥 Checking service health..."
if curl -s http://localhost:8000/health/all | grep -q "healthy"; then
    echo "✅ All services are healthy"
else
    echo "⚠️  Services are starting up (this may take a moment)"
fi

# Display info
echo ""
echo "✅ Startup complete!"
echo ""
echo "📍 Service URLs:"
echo "  - API: http://localhost:8000"
echo "  - Docs: http://localhost:8000/docs"
echo "  - Health: http://localhost:8000/health"
if [ "$1" != "prod" ]; then
    echo "  - PgAdmin: http://localhost:5050 (admin@example.com / admin)"
    echo "  - MinIO: http://localhost:9001 (minioadmin / minioadmin)"
    echo "  - Grafana: http://localhost:3000 (admin / admin)"
    echo "  - Prometheus: http://localhost:9090"
fi
echo ""
echo "📝 View logs:"
echo "  docker-compose logs -f api"
echo ""
