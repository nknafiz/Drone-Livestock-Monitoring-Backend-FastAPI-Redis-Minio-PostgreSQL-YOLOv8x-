```html
<div align="center">
<img src="https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png" width="220" alt="FastAPI"/>
# DLM — Drone Livestock Monitoring System
### by **NK. Nafiz Khan** — Backend Engineer
**Production-grade real-time livestock monitoring platform** using YOLOv8, WebSocket streaming, vector search, and enterprise security — built for drone operations in large-scale farming.

---
[![FastAPI](https://img.shields.io/badge/FastAPI-Async_API-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Computer_Vision-00FF00?style=for-the-badge)](https://ultralytics.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7+-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![MinIO](https://img.shields.io/badge/MinIO-S3_Storage-C72E49?style=for-the-badge&logo=minio&logoColor=white)](https://min.io)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-5C5CFF?style=for-the-badge)](https://qdrant.tech)
[![Docker](https://img.shields.io/badge/Docker-Container-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Prometheus](https://img.shields.io/badge/Prometheus-Monitoring-E6522C?style=for-the-badge&logo=prometheus&logoColor=white)](https://prometheus.io)
</div>
---
```

## 🧠 What Makes This Different

This is not a basic detection wrapper. Every decision is engineered for scale, reliability, and operational excellence in real-world drone livestock monitoring.

| Problem | What Most Systems Do | What DLM Does |
|---|---|---|
| Token invalidation | Token expiry only | Redis blacklist per `jti` + refresh token rotation |
| Model serving | Simple inference | Optimized YOLOv8 with GPU support, warm-up, and batching |
| Real-time streaming | Polling | High-performance WebSocket with binary frame support |
| Search & analytics | Simple SQL queries | Qdrant vector DB for similarity search + embeddings |
| Storage | Local filesystem | MinIO S3-compliant with lifecycle policies |
| Security | Basic JWT | Argon2 hashing, RBAC (Admin/Technician/Viewer), rate limiting |
| Observability | Basic logs | Prometheus metrics + Grafana dashboards |
| Deployment | Manual | Full Docker Compose + production-ready Kubernetes manifests |

---

## 📋 Table of Contents
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Security System](#-security-system)
- [All API Endpoints](#-all-api-endpoints)
- [How Key Features Work](#-how-key-features-work)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Environment Configuration](#-environment-configuration)
- [Running the App](#-running-the-app)
- [Real-time WebSocket](#-real-time-websocket)
- [Monitoring & Observability](#-monitoring--observability)
- [API Documentation](#-api-documentation)
- [Performance](#-performance)

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────────────┐
│ Drone / Web / Mobile Clients                                 │
│ WebSocket + REST + Binary Frame Streaming                    │
└─────────────────────────────┬────────────────────────────────┘
                              │ HTTP + WS (TLS)
┌─────────────────────────────▼──────────────────────────────┐
│ Nginx (Reverse Proxy + Load Balancer + Rate Limiting)     │
└─────────────────────────────┬──────────────────────────────┘
                              │
┌─────────────────────────────▼──────────────────────────────┐
│ FastAPI Application (Uvicorn + ASGI)                       │
│ ├─ Auth (JWT + RBAC)                                       │
│ ├─ Detection Service (YOLOv8)                              │
│ ├─ WebSocket Manager                                       │
│ ├─ Storage & Vector Service                                │
│ └─ Monitoring & Health                                     │
└─────────────────────────────┬──────────────────────────────┘
                              │
       ┌──────────────────────┼──────────────────────┐
┌──────▼──────┐ ┌───────────▼────┐ ┌───────────────▼──────┐
│ PostgreSQL  │ │ Redis          │ │ MinIO (S3)            │
│ (asyncpg)   │ │ (Cache + Blacklist) │ (Images/Videos)   │
└─────────────┘ └────────────────┘ └──────────────────────┘
                              │
                       ┌──────▼──────┐
                       │ Qdrant      │
                       │ Vector DB   │
                       └─────────────┘
                              │
                       ┌──────▼──────┐
                       │ YOLOv8      │
                       │ (GPU/CPU)   │
                       └─────────────┘
```

---

## 🛠 Tech Stack

### Backend Core
| Layer | Technology | Version | Role |
|---|---|---|---|
| Web Framework | FastAPI | Latest | Async API + WebSocket |
| ASGI Server | Uvicorn | Latest | High-performance server |
| ORM | SQLModel + SQLAlchemy | Latest | Type-safe models |
| ML Model | Ultralytics YOLOv8 | Latest | Real-time livestock detection |
| Vector DB | Qdrant | Latest | Embedding similarity search |
| Cache & Sessions | Redis | 7+ | Token blacklist, rate limiting |
| Object Storage | MinIO | Latest | S3-compatible media storage |
| Auth | python-jose + Argon2 | Latest | JWT + secure hashing |
| Monitoring | Prometheus + Grafana | Latest | Metrics & dashboards |

### Deployment & Ops
| Tool | Purpose |
|---|---|
| Docker + Compose | Full stack orchestration |
| Nginx | Reverse proxy & security |
| Alembic | Database migrations |
| Pydantic v2 | Settings & validation |

---

## 📁 Project Structure

```
drone-livestock-monitoring/
│
├── app/
│ ├── core/                  # config, security, dependencies, middleware
│ ├── auth/                  # JWT, RBAC, password service
│ ├── db/                    # models, connection, migrations
│ ├── services/              # business logic (detection, user, analytics)
│ ├── ml/                    # YOLOv8 handler, preprocessing, postprocessing
│ ├── routes/                # API endpoints (auth, detection, health)
│ ├── ws/                    # WebSocket manager & handlers
│ ├── storage/               # MinIO client
│ ├── cache/                 # Redis client
│ ├── monitoring/            # Prometheus metrics
│ ├── schemas/               # Pydantic models
│ └── main.py                # FastAPI app + lifespan
│
├── config/
│ └── settings.py            # Pydantic BaseSettings with validation
│
├── docker/                  # Dockerfile, nginx.conf, supervisord
├── alembic/                 # DB migrations
├── tests/                   # Unit + integration tests
├── k8s/                     # Kubernetes manifests & Helm charts
├── docker-compose.yml
├── docker-compose.prod.yml
├── requirements.txt
└── .env.example
```

---

## 🔐 Security System

### JWT + RBAC
- **Roles**: Admin, Technician, Viewer
- Redis-backed token blacklist on logout
- Refresh token rotation
- Declarative role guards via FastAPI `Depends()`

### Password Security
Argon2id hashing (Password Hashing Competition winner). All passwords validated before hashing.

### Production Hardening
- Startup validation of all critical secrets
- Rate limiting per IP and per user
- Secure headers middleware
- Input sanitization with Pydantic
- Non-root containers

---

## 📡 All API Endpoints

### 🔑 Auth
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/register` | ❌ | Create user with role |
| POST | `/api/auth/login` | ❌ | OAuth2-style login |
| POST | `/api/auth/refresh` | ❌ | Rotate tokens |
| POST | `/api/auth/logout` | ✅ | Blacklist current token |
| GET | `/api/auth/me` | ✅ | Current user profile |

### 📸 Detection
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/detection/image` | ✅ | Single image detection |
| POST | `/api/detection/video` | ✅ | Video file processing |
| GET | `/api/detection/results` | ✅ | Paginated history |
| GET | `/api/detection/results/{id}` | ✅ | Single result with embeddings |

### 🔌 WebSocket
`ws://<host>/ws/detection/{user_id}`

### 🏥 Health & Monitoring
| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | API health |
| GET | `/health/all` | Full stack health |
| GET | `/metrics` | Prometheus metrics |

---

## 🔍 How Key Features Work

### YOLOv8 Detection Pipeline
1. Image/Video preprocessing (resize, normalization)
2. Warm model inference with GPU support
3. Post-processing + confidence filtering
4. Embedding generation → Qdrant storage
5. Result persistence + real-time broadcast

### Real-time WebSocket Architecture
- Connection manager with user isolation
- Binary frame support for low-latency
- Automatic reconnection handling
- Subscription-based device filtering

### Vector Similarity Search
Qdrant stores detection embeddings for:
- Similar animal pattern search
- Historical comparison
- Anomaly detection

---

## 🚀 Installation & Setup

### Using Docker (Recommended)

```bash
git clone <repo-url>
cd drone-livestock-monitoring

cp .env.example .env
# Edit .env with your secrets

docker compose up -d
```

### Local Development

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Database setup
alembic upgrade head

# Run server
uvicorn app.main:app --reload --port 8000
```

---

## 🔧 Environment Configuration

Key variables (production enforced):

```env
MODE=production
SECRET_KEY=...
JWT_REFRESH_SECRET_KEY=...
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
MINIO_ROOT_USER=...
YOLO_MODEL=yolov8n.pt
YOLO_DEVICE=0          # 0 = GPU, cpu = CPU
```

---

## ▶️ Running the App

```bash
# Development
docker compose up -d

# Production
docker compose -f docker-compose.prod.yml up -d
```

**Services:**
- API → http://localhost:8000
- Swagger → http://localhost:8000/docs
- Grafana → http://localhost:3000
- MinIO → http://localhost:9001

---

## 📡 Real-time WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/detection/user123');

ws.onmessage = (event) => {
  const result = JSON.parse(event.data);
  // Live detection: animal_count, confidence, bbox, etc.
};
```

---

## 📊 Monitoring & Observability

**Prometheus Metrics:**
- `detections_total`
- `animals_detected_total{class="cattle"}`
- `model_inference_time_seconds`
- `http_requests_total`

**Grafana Dashboards** included for:
- Detection Performance
- System Health
- API Latency
- Model Metrics

---

## 📖 API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## ⚡ Performance

- YOLOv8n inference: **~5-15ms** on GPU
- WebSocket latency: **< 100ms**
- Concurrent users: 500+ with proper scaling
- Connection pooling and Redis caching for hot paths

---

**Built with ❤️ by NK. Nafiz Khan**  
*Senior Backend Engineer specialized in high-performance AI systems and real-time applications.*

**Version**: 1.0.0  
**Status**: Production Ready ✅  
**Last Updated**: May 20, 2026
```
