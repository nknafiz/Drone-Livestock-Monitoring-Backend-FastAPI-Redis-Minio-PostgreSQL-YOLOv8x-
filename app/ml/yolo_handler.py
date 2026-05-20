"""
YOLOv8 model loading and inference handler.
Detects and counts animals/objects by class separately.
"""
import logging
import time
from typing import Optional, Dict, Any
import numpy as np
from ultralytics import YOLO

from config.settings import settings

logger = logging.getLogger(__name__)

_model_instance: Optional[YOLO] = None

# ✅ COCO dataset এর সব animal/livestock classes
LIVESTOCK_CLASSES = {
    "cow", "sheep", "horse", "dog", "cat",
    "bird", "elephant", "bear", "zebra", "giraffe",
    "pig", "goat",
}

# ✅ সব detectable classes (person সহ)
ALL_TRACKED_CLASSES = LIVESTOCK_CLASSES | {"person"}

MIN_BOX_AREA = 500  # pixel² এর কম হলে false positive skip


def _parse_boxes(result) -> Dict[str, Any]:
    """
    Parse YOLO result boxes into structured format.
    Returns class-wise counts and bounding boxes.
    """
    bounding_boxes = []
    total_confidence = 0.0
    class_counts: Dict[str, int] = {}

    if result.boxes is not None:
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            conf = float(box.conf[0])
            class_id = int(box.cls[0])
            class_name = result.names[class_id]

            # ✅ শুধু tracked classes রাখো
            if class_name not in ALL_TRACKED_CLASSES:
                continue

            w = int(x2 - x1)
            h = int(y2 - y1)

            # ✅ খুব ছোট box skip
            if w * h < MIN_BOX_AREA:
                continue

            bounding_boxes.append({
                "x": int(x1),
                "y": int(y1),
                "w": w,
                "h": h,
                "class": class_name,
                "confidence": round(conf, 3),
            })
            total_confidence += conf

            # ✅ class অনুযায়ী count
            class_counts[class_name] = class_counts.get(class_name, 0) + 1

    avg_confidence = total_confidence / len(bounding_boxes) if bounding_boxes else 0.0

    # ✅ livestock আলাদা count
    livestock_count = sum(
        count for cls, count in class_counts.items()
        if cls in LIVESTOCK_CLASSES
    )

    return {
        "total_count": len(bounding_boxes),
        "livestock_count": livestock_count,
        "class_counts": class_counts,       # {"cow": 3, "person": 2, "dog": 1}
        "confidence_score": round(avg_confidence, 3),
        "bounding_boxes": bounding_boxes,
    }


class YOLOHandler:
    """YOLOv8 model management and inference."""

    @staticmethod
    async def initialize_model() -> YOLO:
        """Initialize and cache YOLOv8 model."""
        global _model_instance

        if _model_instance is not None:
            return _model_instance

        try:
            logger.info(f"Loading YOLOv8 model: {settings.YOLO_MODEL}")
            model = YOLO(f"{settings.YOLO_MODEL}.pt")

            if settings.YOLO_DEVICE != "auto":
                model.to(settings.YOLO_DEVICE)

            logger.info(f"YOLOv8 model loaded successfully on device: {model.device}")
            _model_instance = model
            return model

        except Exception as e:
            logger.error(f"Failed to load YOLOv8 model: {e}")
            raise

    @staticmethod
    def get_model() -> YOLO:
        """Get cached model instance."""
        if _model_instance is None:
            raise RuntimeError("Model not initialized. Call initialize_model() first.")
        return _model_instance

    @staticmethod
    async def detect_image(
        image_path: str,
        conf: float = settings.YOLO_CONF_THRESHOLD,
        iou: float = settings.YOLO_IOU_THRESHOLD,
    ) -> Dict[str, Any]:
        """
        Detect and count objects in image by class.

        Returns:
            {
                "image_path": str,
                "total_count": int,          # সব detected object
                "livestock_count": int,       # শুধু animal
                "animal_count": int,          # DB compatibility
                "class_counts": {            # ✅ আলাদা আলাদা count
                    "cow": 5,
                    "sheep": 3,
                    "person": 2,
                    "dog": 1,
                },
                "confidence_score": float,
                "processing_time_ms": float,
                "bounding_boxes": [...],
            }
        """
        start_time = time.time()

        try:
            model = YOLOHandler.get_model()

            results = model.predict(
                source=image_path,
                conf=conf,
                iou=iou,
                device=settings.YOLO_DEVICE,
                verbose=False,
            )

            parsed = _parse_boxes(results[0])
            processing_time = (time.time() - start_time) * 1000

            # ✅ Class summary log
            class_summary = ", ".join(
                f"{cls}: {count}"
                for cls, count in sorted(parsed["class_counts"].items())
            )
            logger.info(
                f"Image detection — total: {parsed['total_count']} "
                f"| livestock: {parsed['livestock_count']} "
                f"| breakdown: [{class_summary}]"
            )

            return {
                "image_path": image_path,
                "total_count": parsed["total_count"],
                "livestock_count": parsed["livestock_count"],
                "animal_count": parsed["livestock_count"],  # DB compatibility
                "class_counts": parsed["class_counts"],
                "confidence_score": parsed["confidence_score"],
                "processing_time_ms": round(processing_time, 2),
                "bounding_boxes": parsed["bounding_boxes"],
            }

        except Exception as e:
            logger.error(f"Image detection failed: {e}")
            raise

    @staticmethod
    async def detect_frame(
        frame: np.ndarray,
        conf: float = settings.YOLO_CONF_THRESHOLD,
        iou: float = settings.YOLO_IOU_THRESHOLD,
    ) -> Dict[str, Any]:
        """
        Detect and count objects in a single video frame.

        Returns same structure as detect_image (without image_path).
        """
        start_time = time.time()

        try:
            model = YOLOHandler.get_model()

            results = model.predict(
                source=frame,
                conf=conf,
                iou=iou,
                device=settings.YOLO_DEVICE,
                verbose=False,
            )

            parsed = _parse_boxes(results[0])
            processing_time = (time.time() - start_time) * 1000

            return {
                "total_count": parsed["total_count"],
                "livestock_count": parsed["livestock_count"],
                "animal_count": parsed["livestock_count"],  # DB compatibility
                "class_counts": parsed["class_counts"],
                "confidence_score": parsed["confidence_score"],
                "processing_time_ms": round(processing_time, 2),
                "bounding_boxes": parsed["bounding_boxes"],
            }

        except Exception as e:
            logger.error(f"Frame detection failed: {e}")
            raise

    @staticmethod
    def get_model_info() -> Dict[str, Any]:
        """Get model information."""
        try:
            model = YOLOHandler.get_model()
            return {
                "model": settings.YOLO_MODEL,
                "device": str(model.device),
                "loaded": True,
                "conf_threshold": settings.YOLO_CONF_THRESHOLD,
                "iou_threshold": settings.YOLO_IOU_THRESHOLD,
                "tracked_classes": sorted(ALL_TRACKED_CLASSES),
                "livestock_classes": sorted(LIVESTOCK_CLASSES),
            }
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            return {
                "model": settings.YOLO_MODEL,
                "loaded": False,
                "error": str(e),
            }