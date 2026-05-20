"""
Background video processing with real-time WebSocket progress.
"""
import logging
import asyncio
import uuid
from typing import Dict, Any
from datetime import datetime
import cv2
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Detection
from app.ml.yolo_handler import YOLOHandler
from app.storage.minio_client import MinIOClient
from app.ws.manager import manager

logger = logging.getLogger(__name__)

# ✅ Active jobs track করার জন্য (memory store)
_active_jobs: Dict[str, Dict[str, Any]] = {}


def get_job_status(job_id: str) -> Dict[str, Any]:
    """Get current job status."""
    return _active_jobs.get(job_id, {"error": "Job not found"})


async def process_video_background(
    job_id: str,
    user_id: int,
    device_id: int,
    video_path: str,
    minio_path: str,
    sample_rate: int,
    session_factory,
) -> None:
    """
    Background task — video frame by frame process করে
    WebSocket এ real-time progress পাঠায়।
    """

    # ✅ Job initialize
    _active_jobs[job_id] = {
        "job_id": job_id,
        "status": "processing",
        "progress_percent": 0,
        "frames_total": 0,
        "frames_processed": 0,
        "class_counts": {},
        "livestock_count": 0,
        "total_detected": 0,
        "started_at": datetime.utcnow().isoformat(),
        "finished_at": None,
        "detection_id": None,
        "error": None,
    }

    try:
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError("Failed to open video file")

        # Total frame count
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        duration_seconds = round(total_frames / fps, 1)

        _active_jobs[job_id]["frames_total"] = total_frames
        _active_jobs[job_id]["duration_seconds"] = duration_seconds

        logger.info(
            f"[Job {job_id}] Starting video: "
            f"{total_frames} frames, {duration_seconds}s, "
            f"sample_rate={sample_rate}"
        )

        frame_count = 0
        sampled_frames = 0
        total_confidence = 0.0
        total_processing_ms = 0.0
        all_bounding_boxes = []
        aggregated_class_counts: Dict[str, int] = {}
        total_livestock = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            if frame_count % sample_rate != 0:
                continue

            sampled_frames += 1

            # ✅ YOLO detection
            result = await YOLOHandler.detect_frame(frame)

            # Aggregate results
            frame_class_counts = result.get("class_counts", {})
            for cls, count in frame_class_counts.items():
                aggregated_class_counts[cls] = (
                    aggregated_class_counts.get(cls, 0) + count
                )

            total_livestock += result["livestock_count"]
            total_confidence += result["confidence_score"]
            total_processing_ms += result["processing_time_ms"]

            for box in result["bounding_boxes"]:
                box["frame"] = frame_count
                all_bounding_boxes.append(box)

            # ✅ Progress calculate
            progress = round((frame_count / total_frames) * 100, 1)

            # ✅ Job status update
            _active_jobs[job_id].update({
                "progress_percent": progress,
                "frames_processed": sampled_frames,
                "class_counts": aggregated_class_counts,
                "livestock_count": total_livestock,
                "total_detected": sum(aggregated_class_counts.values()),
            })

            # ✅ WebSocket এ real-time progress পাঠাও
            await manager.send_to_user(
                user_id=user_id,
                message={
                    "type": "video_progress",
                    "job_id": job_id,
                    "progress_percent": progress,
                    "frames_processed": sampled_frames,
                    "current_frame": frame_count,
                    "frames_total": total_frames,
                    "class_counts": aggregated_class_counts,
                    "livestock_count": total_livestock,
                    "latest_frame_result": {
                        "class_counts": frame_class_counts,
                        "livestock_count": result["livestock_count"],
                        "confidence": result["confidence_score"],
                    },
                },
            )

            # ✅ Every 50 frames এ log করো
            if sampled_frames % 50 == 0:
                logger.info(
                    f"[Job {job_id}] Progress: {progress}% | "
                    f"Classes: {aggregated_class_counts}"
                )

        cap.release()

        # ✅ Final calculations
        if sampled_frames == 0:
            sampled_frames = 1

        avg_confidence = round(total_confidence / sampled_frames, 3)
        avg_livestock = round(total_livestock / sampled_frames, 2)
        class_avg = {
            cls: round(count / sampled_frames, 2)
            for cls, count in aggregated_class_counts.items()
        }

        # ✅ DB তে save
        async with session_factory() as session:
            detection = Detection(
                user_id=user_id,
                device_id=device_id,
                video_path=minio_path,
                detection_type="video",
                animal_count=int(avg_livestock),
                confidence_score=avg_confidence,
                processing_time_ms=round(total_processing_ms, 2),
                bounding_boxes=all_bounding_boxes,
                device_metadata={
                    "job_id": job_id,
                    "frames_total": total_frames,
                    "frames_sampled": sampled_frames,
                    "sample_rate": sample_rate,
                    "duration_seconds": duration_seconds,
                    "avg_livestock_per_frame": avg_livestock,
                    "class_counts": aggregated_class_counts,
                    "class_avg": class_avg,
                },
            )
            session.add(detection)
            await session.commit()
            await session.refresh(detection)

        # ✅ Job complete
        _active_jobs[job_id].update({
            "status": "completed",
            "progress_percent": 100,
            "detection_id": detection.id,
            "finished_at": datetime.utcnow().isoformat(),
            "avg_livestock_per_frame": avg_livestock,
            "class_avg": class_avg,
        })

        # ✅ WebSocket এ final result পাঠাও
        await manager.send_to_user(
            user_id=user_id,
            message={
                "type": "video_complete",
                "job_id": job_id,
                "detection_id": detection.id,
                "progress_percent": 100,
                "duration_seconds": duration_seconds,
                "frames_total": total_frames,
                "frames_sampled": sampled_frames,
                "class_counts": aggregated_class_counts,
                "class_avg": class_avg,
                "livestock_count": total_livestock,
                "avg_livestock_per_frame": avg_livestock,
                "confidence_score": avg_confidence,
                "processing_time_ms": round(total_processing_ms, 2),
            },
        )

        logger.info(
            f"[Job {job_id}] COMPLETED → detection #{detection.id} | "
            f"classes: {aggregated_class_counts}"
        )

    except Exception as e:
        logger.error(f"[Job {job_id}] FAILED: {e}")

        _active_jobs[job_id].update({
            "status": "failed",
            "error": str(e),
            "finished_at": datetime.utcnow().isoformat(),
        })

        # ✅ WebSocket এ error পাঠাও
        await manager.send_to_user(
            user_id=user_id,
            message={
                "type": "video_error",
                "job_id": job_id,
                "error": str(e),
            },
        )