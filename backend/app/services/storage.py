import io
import logging
from datetime import timedelta
from typing import Optional

from minio import Minio
from minio.error import S3Error

from app.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket = settings.minio_bucket

    def init_bucket(self):
        """Create the bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info("Created bucket: %s", self.bucket)
        except S3Error as e:
            logger.error("Failed to create bucket: %s", e)

    def upload_audio(self, call_id: str, file_bytes: bytes, content_type: str = "audio/mpeg") -> str:
        """Upload audio file to MinIO. Returns the object path."""
        object_name = f"audio/{call_id}.mp3"
        self.client.put_object(
            self.bucket,
            object_name,
            io.BytesIO(file_bytes),
            length=len(file_bytes),
            content_type=content_type,
        )
        logger.info("Uploaded audio: %s", object_name)
        return object_name

    def get_audio_url(self, object_name: str, expires: int = 3600) -> Optional[str]:
        """Get presigned URL for audio file."""
        try:
            url = self.client.presigned_get_object(
                self.bucket,
                object_name,
                expires=timedelta(seconds=expires),
            )
            return url
        except S3Error as e:
            logger.error("Failed to get presigned URL for %s: %s", object_name, e)
            return None

    def download_audio(self, object_name: str) -> Optional[bytes]:
        """Download audio file from MinIO."""
        try:
            response = self.client.get_object(self.bucket, object_name)
            data = response.read()
            response.close()
            return data
        except S3Error as e:
            logger.error("Failed to download %s: %s", object_name, e)
            return None

    def upload_report(self, job_id: int, file_bytes: bytes) -> str:
        """Upload Excel report to MinIO."""
        object_name = f"reports/report_{job_id}.xlsx"
        self.client.put_object(
            self.bucket,
            object_name,
            io.BytesIO(file_bytes),
            length=len(file_bytes),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        return object_name

    def get_report_url(self, object_name: str, expires: int = 3600) -> Optional[str]:
        """Get presigned URL for report file."""
        return self.get_audio_url(object_name, expires)


storage_service = StorageService()
