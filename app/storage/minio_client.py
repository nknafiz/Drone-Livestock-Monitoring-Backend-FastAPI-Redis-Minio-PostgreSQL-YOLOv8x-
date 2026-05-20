"""
MinIO S3-compatible object storage client.
"""
import logging
from datetime import timedelta
from minio import Minio
from minio.error import S3Error

from config.settings import settings

logger = logging.getLogger(__name__)

_minio_client = None


def get_minio_client() -> Minio:
    """Get or create MinIO client."""
    global _minio_client
    
    if _minio_client is None:
        _minio_client = Minio(
            endpoint=settings.MINIO_URL.replace("http://", "").replace("https://", ""),
            access_key=settings.MINIO_ROOT_USER,
            secret_key=settings.MINIO_ROOT_PASSWORD,
            secure=settings.MINIO_URL.startswith("https"),
        )
    
    return _minio_client


class MinIOClient:
    """MinIO storage operations."""
    
    @staticmethod
    async def ensure_buckets_exist() -> None:
        """Create buckets if they don't exist."""
        client = get_minio_client()
        buckets = [
            settings.MINIO_BUCKET_FRAMES,
            settings.MINIO_BUCKET_VIDEOS,
            settings.MINIO_BUCKET_RESULTS,
        ]
        
        try:
            for bucket in buckets:
                if not client.bucket_exists(bucket):
                    client.make_bucket(bucket)
                    logger.info(f"Created MinIO bucket: {bucket}")
        except S3Error as e:
            logger.error(f"MinIO bucket creation failed: {e}")
            raise
    
    @staticmethod
    async def upload_detection_file(
        file_path: str,
        bucket: str,
        object_name: str,
    ) -> str:
        """
        Upload detection file to MinIO.
        
        Returns:
            MinIO object path
        """
        client = get_minio_client()
        
        try:
            with open(file_path, "rb") as f:
                file_stat = __import__("os").stat(file_path)
                client.put_object(
                    bucket,
                    object_name,
                    f,
                    length=file_stat.st_size,
                )
            
            logger.info(f"Uploaded to MinIO: {bucket}/{object_name}")
            return f"{bucket}/{object_name}"
        except Exception as e:
            logger.error(f"MinIO upload failed: {e}")
            raise
    
    @staticmethod
    async def get_presigned_url(
        bucket: str,
        object_name: str,
        expires_days: int = 7,
    ) -> str:
        """
        Get presigned download URL for object.
        
        Returns:
            Presigned URL (valid for expires_days)
        """
        client = get_minio_client()
        
        try:
            url = client.get_presigned_download_url(
                bucket,
                object_name,
                expires=timedelta(days=expires_days),
            )
            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise
    
    @staticmethod
    async def delete_object(bucket: str, object_name: str) -> bool:
        """Delete object from MinIO."""
        client = get_minio_client()
        
        try:
            client.remove_object(bucket, object_name)
            logger.info(f"Deleted from MinIO: {bucket}/{object_name}")
            return True
        except S3Error as e:
            logger.error(f"MinIO delete failed: {e}")
            return False
    
    @staticmethod
    async def health_check() -> bool:
        """Check MinIO connectivity."""
        try:
            client = get_minio_client()
            client.bucket_exists(settings.MINIO_BUCKET_FRAMES)
            return True
        except Exception as e:
            logger.error(f"MinIO health check failed: {e}")
            return False
