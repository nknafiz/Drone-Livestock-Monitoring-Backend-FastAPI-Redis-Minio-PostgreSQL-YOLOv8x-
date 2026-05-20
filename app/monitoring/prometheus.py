"""
Prometheus monitoring and metrics collection.
"""
import logging
import time
from fastapi import FastAPI, Request
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    REGISTRY,
)

logger = logging.getLogger(__name__)

# Custom metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

active_connections = Gauge(
    "active_websocket_connections",
    "Active WebSocket connections",
)

detections_total = Counter(
    "detections_total",
    "Total detections processed",
    ["type", "status"],
)

detected_animals_total = Counter(
    "detected_animals_total",
    "Total animals detected",
    ["animal_class"],
)

detection_confidence = Histogram(
    "detection_confidence",
    "Detection confidence scores",
    ["animal_class"],
)

model_inference_time_ms = Histogram(
    "model_inference_time_ms",
    "YOLOv8 model inference time in milliseconds",
    buckets=[10, 50, 100, 200, 500, 1000, 2000, 5000],
)


def setup_prometheus(app: FastAPI) -> None:
    """Setup Prometheus metrics collection."""
    
    # Middleware to track metrics
    @app.middleware("http")
    async def prometheus_middleware(request: Request, call_next):
        """Track HTTP metrics."""
        method = request.method
        endpoint = request.url.path
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time
            
            # Record metrics
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status_code,
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)
        
        return response
    
    # Metrics endpoint
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        return generate_latest(REGISTRY)
    
    logger.info("Prometheus monitoring setup complete")


def record_detection(detection_type: str, status: str, confidence: float):
    """Record detection metrics."""
    detections_total.labels(type=detection_type, status=status).inc()
    if status == "success":
        detection_confidence.labels(animal_class="livestock").observe(confidence)


def record_animal_detection(animal_class: str, count: int = 1):
    """Record animal detections."""
    detected_animals_total.labels(animal_class=animal_class).inc(count)


def record_inference_time(inference_time_ms: float):
    """Record model inference time."""
    model_inference_time_ms.observe(inference_time_ms)
