# Drone Livestock Monitoring Backend

Production-ready FastAPI backend for real-time livestock monitoring using YOLOv8 computer vision.

## 🌟 Features

- **FastAPI** - Modern async Python web framework
- **YOLOv8** - Real-time object detection (livestock)
- **WebSocket** - Live frame streaming and detection results
- **PostgreSQL** - Persistent data storage
- **Redis** - Caching, rate limiting, session management
- **MinIO** - S3-compatible object storage for images/videos
- **Qdrant** - Vector database for embeddings/similarity search
- **JWT Authentication** - Secure API access with token refresh
- **RBAC** - Role-based access control (Admin, Technician, Viewer)
- **Argon2** - Password hashing for security
- **Prometheus** - Metrics and monitoring
- **Docker** - Containerized deployment
- **Nginx** - Reverse proxy and load balancing
- **Vault** - Secret management (optional)

## 📋 Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
   ┌───▼────────────────┐
   │  Nginx (Reverse    │
   │  Proxy/LB)         │
   └───┬────────────────┘
       │
   ┌───▼────────────────────────┐
   │  FastAPI Application       │
   │  ├─ Auth Routes            │
   │  ├─ Detection API          │
   │  ├─ WebSocket Handler      │
   │  └─ Health Checks          │
   └───┬────────────────────────┘
       │
   ├─────────────────────────────────┐
   │                                 │
┌──▼──────┐  ┌──────────┐  ┌───────▼──┐  ┌──────────┐  ┌─────────┐
│ Database│  │  Redis   │  │ MinIO    │  │ Qdrant   │  │ YOLOv8  │
│(Postgres)  │ (Cache)  │  │(Storage) │  │ (Vector) │  │ (Model) │
└─────────┘  └──────────┘  └──────────┘  └──────────┘  └─────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Git

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd Dron_ai_project

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Wait for services to be healthy (30-60 seconds)
docker-compose ps

# API will be available at: http://localhost:8000
# Docs at: http://localhost:8000/docs
# PgAdmin at: http://localhost:5050 (admin@example.com / admin)
# MinIO at: http://localhost:9001 (minioadmin / minioadmin)
# Grafana at: http://localhost:3000 (admin / admin)
```

### Local Development (without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup database
python -c "from app.db.connection import Database; await Database.create_tables()"

# Run development server
python app/main.py
```

## 🔐 Authentication

### Register New User

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "farmer1",
    "email": "farmer@example.com",
    "password": "SecurePassword123",
    "full_name": "John Farmer"
  }'
```

### Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "farmer1",
    "password": "SecurePassword123"
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Refresh Token

```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }'
```

## 📤 Detection API

### Upload Image for Detection

```bash
curl -X POST http://localhost:8000/api/detection/image \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@image.jpg" \
  -F "device_id=1"
```

### Upload Video for Detection

```bash
curl -X POST http://localhost:8000/api/detection/video \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@video.mp4" \
  -F "device_id=1"
```

### Get Detection Results

```bash
curl -X GET http://localhost:8000/api/detection/results \
  -H "Authorization: Bearer <access_token>"
```

## 🔌 WebSocket Real-time Streaming

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/detection/<user_id>');

ws.onopen = () => {
  console.log('Connected to detection stream');
  
  // Subscribe to device
  ws.send(JSON.stringify({
    type: 'subscribe',
    device_id: 1
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Detection result:', data);
  // data.type = 'frame_result'
  // data.data = {animal_count, confidence_score, bounding_boxes}
};

ws.close = () => {
  console.log('Disconnected from stream');
};
```

## 🏥 Health Checks

### API Health
```bash
curl http://localhost:8000/health
```

### All Services
```bash
curl http://localhost:8000/health/all
```

### Database
```bash
curl http://localhost:8000/health/db
```

### Redis
```bash
curl http://localhost:8000/health/redis
```

### YOLOv8 Model
```bash
curl http://localhost:8000/health/model
```

### MinIO Storage
```bash
curl http://localhost:8000/health/storage
```

## 📊 Monitoring

### Prometheus Metrics

Access metrics at: http://localhost:9090

Available metrics:
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `detections_total` - Total detections processed
- `detected_animals_total` - Animals detected by class
- `detection_confidence` - Confidence scores
- `model_inference_time_ms` - YOLOv8 inference time

### Grafana Dashboard

Access dashboard at: http://localhost:3000 (admin / admin)

Pre-configured dashboards:
- API Performance
- Detection Statistics
- Model Performance
- Infrastructure Health

## 🐳 Production Deployment

### Using Docker Compose (Production)

```bash
# Setup environment
cp .env.example .env
# Edit .env with production values

# Start production stack
docker-compose -f docker-compose.prod.yml up -d

# Monitor logs
docker-compose -f docker-compose.prod.yml logs -f api
```

### Kubernetes Deployment

```bash
# Generate Kubernetes manifests (optional)
# See k8s/ directory for Helm charts
helm install drone-api ./helm/drone-api
```

## 🔧 Configuration

Environment variables (`.env`):

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# Redis
REDIS_URL=redis://host:6379/0

# MinIO
MINIO_URL=http://minio:9000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# YOLOv8
YOLO_MODEL=yolov8n  # n, s, m, l, x
YOLO_CONF_THRESHOLD=0.25
YOLO_DEVICE=auto    # auto, cpu, 0 (gpu)

# Production
ENVIRONMENT=production
DEBUG=false
```

## 📚 API Documentation

### Interactive Docs (Swagger UI)
http://localhost:8000/docs

### ReDoc
http://localhost:8000/redoc

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app

# Specific test file
pytest tests/test_auth.py
```

## 📁 Project Structure

```
├── app/
│   ├── core/          # Exception handlers, middleware, dependencies
│   ├── auth/          # Authentication logic (JWT, password)
│   ├── db/            # Database models and connection
│   ├── services/      # Business logic (User, Detection)
│   ├── routes/        # API endpoints (auth, detection, health)
│   ├── ml/            # YOLOv8 model handler
│   ├── ws/            # WebSocket manager
│   ├── storage/       # MinIO client
│   ├── cache/         # Redis client
│   ├── monitoring/    # Prometheus metrics
│   └── main.py        # FastAPI application
├── config/            # Configuration (settings.py)
├── docker/            # Docker & Nginx configs
├── alembic/           # Database migrations
├── tests/             # Unit & integration tests
├── requirements.txt   # Python dependencies
├── docker-compose.yml # Development stack
└── README.md
```

## 🔐 Security Best Practices

✅ Implemented:
- Password hashing with Argon2
- JWT tokens with expiration
- Token blacklist for logout
- CORS configuration
- Rate limiting
- Input validation with Pydantic
- Secure headers (HTTPS ready)
- Non-root Docker user
- Health checks on dependencies
- Structured logging for audit trail

## 🐛 Troubleshooting

### Port already in use

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Database connection error

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

### YOLOv8 model download slow

Model (~100MB for yolov8n) is downloaded on first startup. This is normal.
To pre-download: `python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"`

### WebSocket connection refused

- Check if API is running: `curl http://localhost:8000/health`
- Check browser console for errors
- Verify WebSocket proxy in Nginx

## 📝 API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login user |
| POST | `/api/auth/refresh` | Refresh access token |
| POST | `/api/auth/logout` | Logout (blacklist token) |
| GET | `/api/auth/me` | Get current user |
| POST | `/api/detection/image` | Detect livestock in image |
| POST | `/api/detection/video` | Detect livestock in video |
| GET | `/api/detection/results` | Get detection history |
| WS | `/ws/detection/<user_id>` | Real-time detection stream |
| GET | `/health` | API health |
| GET | `/health/all` | All services health |
| GET | `/metrics` | Prometheus metrics |

## 📄 License

Proprietary - Drone Livestock Monitoring System

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section
2. Review logs: `docker-compose logs -f api`
3. Check service health: `/health/all`
4. Contact: support@example.com

## 🚀 Performance Tips

1. **Image Optimization**: Compress images before upload (< 5MB recommended)
2. **Batch Processing**: Process multiple frames in video mode
3. **GPU Usage**: Set `YOLO_DEVICE=0` for GPU inference (5-10x faster)
4. **Caching**: Detection results cached for 30 minutes by default
5. **Rate Limiting**: Default 100 requests/minute per client

---

**Version**: 1.0.0  
**Last Updated**: 2026-05-20  
**Status**: Production Ready ✅
