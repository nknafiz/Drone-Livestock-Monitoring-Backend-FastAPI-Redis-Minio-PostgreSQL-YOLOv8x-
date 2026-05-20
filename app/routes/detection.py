"""
Detection API routes for image/video upload and result retrieval.
"""
import logging
import tempfile
from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Form,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.exceptions import ValidationException, ResourceNotFoundException
from app.db.connection import get_session
from app.db.models import Detection
from app.services.detection_service import DetectionService
from app.monitoring.prometheus import (
    record_detection,
    record_animal_detection,
    record_inference_time,
)
from config.settings import settings
import uuid
from datetime import datetime
from fastapi import BackgroundTasks
from app.storage.minio_client import MinIOClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/detection", tags=["Detection"])


class DetectionResponse:
    """Detection result response schema."""

    @staticmethod
    def from_model(detection: Detection) -> dict:
        metadata = detection.device_metadata or {}
        class_counts = metadata.get("class_counts", {})

        return {
            "id": detection.id,
            "device_id": detection.device_id,
            "detection_type": detection.detection_type,
            "image_path": detection.image_path,
            "video_path": detection.video_path,

            # ✅ Count summary
            "animal_count": detection.animal_count,
            "livestock_count": metadata.get("livestock_count", detection.animal_count),
            "total_detected": metadata.get("total_detected", detection.animal_count),

            # ✅ আলাদা আলাদা class count — {"cow": 3, "sheep": 1, "person": 2}
            "class_counts": class_counts,

            # ✅ Confidence & timing
            "confidence_score": detection.confidence_score,
            "processing_time_ms": detection.processing_time_ms,

            # ✅ Bounding boxes
            "bounding_boxes": detection.bounding_boxes,

            # ✅ Video এ extra stats
            "video_stats": {
                "frames_total": metadata.get("frames_total"),
                "frames_sampled": metadata.get("frames_sampled"),
                "sample_rate": metadata.get("sample_rate"),
                "avg_livestock_per_frame": metadata.get("avg_livestock_per_frame"),
                "class_avg": metadata.get("class_avg", {}),
            } if detection.detection_type == "video" else None,

            "created_at": detection.created_at.isoformat(),
            "updated_at": detection.updated_at.isoformat(),
        }


@router.post("/image", status_code=status.HTTP_201_CREATED)
async def detect_image(
    file: UploadFile = File(...),
    device_id: int = Form(...),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Upload image for livestock detection.

    Returns:
        Detection results with bounding boxes and per-class animal count.
    """
    user_id = current_user["user_id"]

    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise ValidationException(
                "File must be an image", details={"field": "file"}
            )

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name

        # Process detection
        detection = await DetectionService.process_image_detection(
            session=session,
            user_id=user_id,
            device_id=device_id,
            image_path=tmp_path,
        )

        # Record Prometheus metrics
        metadata = detection.device_metadata or {}
        class_counts = metadata.get("class_counts", {})

        record_detection("image", "success", detection.confidence_score)
        record_inference_time(detection.processing_time_ms)

        # ✅ প্রতিটা class আলাদাভাবে Prometheus এ record করো
        for cls, count in class_counts.items():
            record_animal_detection(cls, count)

        logger.info(
            f"Image detection completed: #{detection.id} "
            f"| livestock: {detection.animal_count} "
            f"| classes: {class_counts}"
        )

        return DetectionResponse.from_model(detection)

    except Exception as e:
        logger.error(f"Image detection failed: {e}")
        record_detection("image", "failed", 0.0)
        raise


@router.post("/video", status_code=status.HTTP_201_CREATED)
async def detect_video(
    file: UploadFile = File(...),
    device_id: int = Form(...),
    sample_rate: int = Form(default=10),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Upload video for livestock detection.

    Args:
        file: Video file
        device_id: Device/camera ID
        sample_rate: Process every Nth frame (10 = every 10th frame)

    Returns:
        Aggregated detection results with per-class counts.
    """
    user_id = current_user["user_id"]

    try:
        # Validate file type
        if not file.content_type.startswith("video/"):
            raise ValidationException(
                "File must be a video", details={"field": "file"}
            )

        # Check file size
        contents = await file.read()
        file_size_mb = len(contents) / (1024 * 1024)
        if file_size_mb > settings.MAX_UPLOAD_SIZE_MB:
            raise ValidationException(
                f"File size ({file_size_mb:.1f}MB) exceeds limit "
                f"({settings.MAX_UPLOAD_SIZE_MB}MB)",
            )

        # Save video temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        # Process detection
        detection = await DetectionService.process_video_detection(
            session=session,
            user_id=user_id,
            device_id=device_id,
            video_path=tmp_path,
            sample_rate=sample_rate,
        )

        # Record Prometheus metrics
        metadata = detection.device_metadata or {}
        class_counts = metadata.get("class_counts", {})

        record_detection("video", "success", detection.confidence_score)
        record_inference_time(detection.processing_time_ms)

        # ✅ প্রতিটা class আলাদাভাবে record
        for cls, count in class_counts.items():
            record_animal_detection(cls, count)

        logger.info(
            f"Video detection completed: #{detection.id} "
            f"| avg livestock/frame: {detection.animal_count} "
            f"| classes: {class_counts}"
        )

        return DetectionResponse.from_model(detection)

    except Exception as e:
        logger.error(f"Video detection failed: {e}")
        record_detection("video", "failed", 0.0)
        raise


@router.get("/results")
async def get_detections(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get user's detection history with class-wise counts."""
    user_id = current_user["user_id"]

    detections, total = await DetectionService.get_user_detections(
        session=session,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )

    return {
        "detections": [DetectionResponse.from_model(d) for d in detections],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/results/{detection_id}")
async def get_detection(
    detection_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get specific detection result with class-wise counts."""
    user_id = current_user["user_id"]

    detection = await DetectionService.get_detection(
        session=session,
        detection_id=detection_id,
        user_id=user_id,
    )

    if not detection:
        raise ResourceNotFoundException("Detection", detection_id)

    return DetectionResponse.from_model(detection)


@router.delete("/results/{detection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_detection(
    detection_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete detection result."""
    user_id = current_user["user_id"]

    detection = await DetectionService.get_detection(
        session=session,
        detection_id=detection_id,
        user_id=user_id,
    )

    if not detection:
        raise ResourceNotFoundException("Detection", detection_id)

    await session.delete(detection)
    await session.commit()

    logger.info(f"Detection deleted: #{detection_id}")


@router.post("/video/async", status_code=status.HTTP_202_ACCEPTED)
async def detect_video_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    device_id: int = Form(...),
    sample_rate: int = Form(default=10),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Upload video for async livestock detection.
    
    - Video upload হবে, job_id return করবে
    - WebSocket এ real-time progress আসবে
    - Video শেষে final result আসবে
    
    WebSocket: ws://localhost:8000/ws/detection/{user_id}?token=xxx
    """
    user_id = current_user["user_id"]

    # Validate
    if not file.content_type.startswith("video/"):
        raise ValidationException("File must be a video", details={"field": "file"})

    contents = await file.read()
    file_size_mb = len(contents) / (1024 * 1024)
    if file_size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise ValidationException(
            f"File size ({file_size_mb:.1f}MB) exceeds limit ({settings.MAX_UPLOAD_SIZE_MB}MB)"
        )

    # Save temporarily
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    # Upload to MinIO
    minio_path = await MinIOClient.upload_detection_file(
        file_path=tmp_path,
        bucket="livestock-videos",
        object_name=f"user_{user_id}/video_{datetime.now().timestamp()}.mp4",
    )

    # Job ID generate
    job_id = str(uuid.uuid4())

    # Session factory নাও
    from app.db.connection import get_session_factory
    session_factory = get_session_factory()

    # ✅ Background task start করো
    from app.services.video_job_service import process_video_background
    background_tasks.add_task(
        process_video_background,
        job_id=job_id,
        user_id=user_id,
        device_id=device_id,
        video_path=tmp_path,
        minio_path=minio_path,
        sample_rate=sample_rate,
        session_factory=session_factory,
    )

    logger.info(f"Async video job started: {job_id} for user {user_id}")

    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Video upload successful. Processing started.",
        "websocket_url": f"ws://localhost:8000/ws/detection/{user_id}",
        "status_url": f"/api/detection/video/job/{job_id}",
        "sample_rate": sample_rate,
    }


@router.get("/video/job/{job_id}")
async def get_video_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Get video processing job status.
    WebSocket ছাড়াও এখানে HTTP polling করে status দেখা যাবে।
    """
    from app.services.video_job_service import get_job_status
    return get_job_status(job_id)