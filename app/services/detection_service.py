"""
Detection service for image and video processing.
Counts each animal/person class separately and saves to DB.
"""
import logging
import os
from typing import Optional, List, Tuple, Dict
from datetime import datetime
import cv2
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.models import Detection
from app.ml.yolo_handler import YOLOHandler
from app.storage.minio_client import MinIOClient
from app.core.exceptions import ValidationException

logger = logging.getLogger(__name__)


def _merge_class_counts(existing: Dict[str, int], new: Dict[str, int]) -> Dict[str, int]:
    """Merge two class count dicts by summing values."""
    merged = dict(existing)
    for cls, count in new.items():
        merged[cls] = merged.get(cls, 0) + count
    return merged


def _build_summary_log(
    detection_type: str,
    detection_id: int,
    class_counts: Dict[str, int],
    total: int,
    livestock: int,
) -> str:
    breakdown = " | ".join(
        f"{cls.upper()}: {count}"
        for cls, count in sorted(class_counts.items())
    )
    return (
        f"[{detection_type.upper()} #{detection_id}] "
        f"Total: {total} | Livestock: {livestock} | {breakdown}"
    )


class DetectionService:
    """Detection processing and storage service."""

    @staticmethod
    async def process_image_detection(
        session: AsyncSession,
        user_id: int,
        device_id: int,
        image_path: str,
    ) -> Detection:
        """
        Process image detection and store results with per-class counts.

        Returns:
            Detection record with class_counts in device_metadata
        """
        try:
            # ✅ Run YOLO inference
            detection_result = await YOLOHandler.detect_image(image_path)

            class_counts: Dict[str, int] = detection_result.get("class_counts", {})
            total_count: int = detection_result["total_count"]
            livestock_count: int = detection_result["livestock_count"]

            # ✅ Store image in MinIO
            minio_path = await MinIOClient.upload_detection_file(
                file_path=image_path,
                bucket="livestock-frames",
                object_name=f"user_{user_id}/image_{datetime.now().timestamp()}.jpg",
            )

            # ✅ Save to DB — class_counts device_metadata এ store হবে
            detection = Detection(
                user_id=user_id,
                device_id=device_id,
                image_path=minio_path,
                detection_type="image",
                animal_count=livestock_count,
                confidence_score=detection_result["confidence_score"],
                processing_time_ms=detection_result["processing_time_ms"],
                bounding_boxes=detection_result["bounding_boxes"],
                device_metadata={
                    "total_detected": total_count,
                    "livestock_count": livestock_count,
                    "class_counts": class_counts,   # ✅ {"cow": 3, "person": 2}
                },
            )

            session.add(detection)
            await session.commit()
            await session.refresh(detection)

            logger.info(
                _build_summary_log(
                    "image",
                    detection.id,
                    class_counts,
                    total_count,
                    livestock_count,
                )
            )

            return detection

        except Exception as e:
            logger.error(f"Image detection failed: {e}")
            raise

    @staticmethod
    async def process_video_detection(
        session: AsyncSession,
        user_id: int,
        device_id: int,
        video_path: str,
        sample_rate: int = 10,
    ) -> Detection:
        """
        Process video detection — aggregates per-class counts across all frames.

        Returns:
            Detection record with aggregated class_counts
        """
        try:
            cap = cv2.VideoCapture(video_path)

            if not cap.isOpened():
                raise ValidationException("Failed to open video file")

            frame_count = 0
            sampled_frames = 0
            total_confidence = 0.0
            total_processing_ms = 0.0
            all_bounding_boxes = []

            # ✅ Per-class aggregation across all frames
            aggregated_class_counts: Dict[str, int] = {}
            total_livestock_across_frames = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1

                if frame_count % sample_rate != 0:
                    continue

                sampled_frames += 1

                # ✅ Detect in frame
                result = await YOLOHandler.detect_frame(frame)

                frame_class_counts = result.get("class_counts", {})
                aggregated_class_counts = _merge_class_counts(
                    aggregated_class_counts, frame_class_counts
                )

                total_livestock_across_frames += result["livestock_count"]
                total_confidence += result["confidence_score"]
                total_processing_ms += result["processing_time_ms"]

                # Store bounding boxes with frame number
                for box in result["bounding_boxes"]:
                    box["frame"] = frame_count
                    all_bounding_boxes.append(box)

            cap.release()

            if sampled_frames == 0:
                sampled_frames = 1  # division by zero guard

            avg_confidence = round(total_confidence / sampled_frames, 3)
            avg_livestock = round(total_livestock_across_frames / sampled_frames, 2)

            # ✅ Store video in MinIO
            minio_path = await MinIOClient.upload_detection_file(
                file_path=video_path,
                bucket="livestock-videos",
                object_name=f"user_{user_id}/video_{datetime.now().timestamp()}.mp4",
            )

            # ✅ Save to DB
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
                    "frames_total": frame_count,
                    "frames_sampled": sampled_frames,
                    "sample_rate": sample_rate,
                    "avg_livestock_per_frame": avg_livestock,
                    "class_counts": aggregated_class_counts,  # ✅ সব frame এর total
                    "class_avg": {                             # ✅ per-frame average
                        cls: round(count / sampled_frames, 2)
                        for cls, count in aggregated_class_counts.items()
                    },
                },
            )

            session.add(detection)
            await session.commit()
            await session.refresh(detection)

            logger.info(
                _build_summary_log(
                    "video",
                    detection.id,
                    aggregated_class_counts,
                    sum(aggregated_class_counts.values()),
                    total_livestock_across_frames,
                )
            )

            return detection

        except Exception as e:
            logger.error(f"Video detection failed: {e}")
            raise

    @staticmethod
    async def get_detection(
        session: AsyncSession,
        detection_id: int,
        user_id: int,
    ) -> Optional[Detection]:
        """Get detection by ID (ownership check)."""
        result = await session.execute(
            select(Detection).where(
                Detection.id == detection_id,
                Detection.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_detections(
        session: AsyncSession,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Detection], int]:
        """Get user's detections with pagination."""
        total_result = await session.execute(
            select(func.count(Detection.id)).where(Detection.user_id == user_id)
        )
        total = total_result.scalar() or 0

        result = await session.execute(
            select(Detection)
            .where(Detection.user_id == user_id)
            .order_by(Detection.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        detections = result.scalars().all()

        return detections, total