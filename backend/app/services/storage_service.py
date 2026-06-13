import os
import boto3
from urllib.parse import urlparse
from app.core.config import settings

# Local storage fallback directory
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class StorageService:
    def __init__(self):
        self.storage_type = settings.STORAGE_TYPE.lower()
        self.s3_client = None
        
        if self.storage_type == "s3":
            # Initialize S3 boto3 client
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                region_name=settings.AWS_REGION_NAME
            )

    def _extract_s3_key(self, file_key_or_url: str) -> str:
        """Extracts S3 key from a full public URL or returns the key if it's already a key."""
        if "://" in file_key_or_url:
            parsed = urlparse(file_key_or_url)
            path = parsed.path
            bucket = settings.AWS_S3_BUCKET_NAME
            if bucket and bucket in path:
                # S3 URL might look like: /bucket/key or /storage/v1/s3/bucket/key
                return path.split(bucket + "/")[-1]
            return path.lstrip('/')
        return file_key_or_url

    def upload_file(self, file_content: bytes, filename: str, content_type: str = "application/pdf") -> str:
        """Uploads a file and returns the remote URL or local file path."""
        if self.storage_type == "s3":
            if not settings.AWS_S3_BUCKET_NAME:
                raise ValueError("AWS_S3_BUCKET_NAME is not configured in settings.")
            
            self.s3_client.put_object(
                Bucket=settings.AWS_S3_BUCKET_NAME,
                Key=filename,
                Body=file_content,
                ContentType=content_type
            )
            
            # Construct S3 public URL
            if settings.AWS_S3_ENDPOINT_URL:
                # e.g., custom S3 endpoint like Supabase Storage
                # Remove ending slash from endpoint if present
                endpoint = settings.AWS_S3_ENDPOINT_URL.rstrip('/')
                return f"{endpoint}/{settings.AWS_S3_BUCKET_NAME}/{filename}"
            else:
                # Standard AWS S3 URL
                return f"https://{settings.AWS_S3_BUCKET_NAME}.s3.{settings.AWS_REGION_NAME}.amazonaws.com/{filename}"
        else:
            # Local fallback
            file_path = os.path.join(UPLOAD_DIR, filename)
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
            return file_path

    def download_file(self, file_key_or_url: str) -> bytes:
        """Downloads a file and returns its raw binary content."""
        if self.storage_type == "s3":
            if not settings.AWS_S3_BUCKET_NAME:
                raise ValueError("AWS_S3_BUCKET_NAME is not configured in settings.")
            key = self._extract_s3_key(file_key_or_url)
            response = self.s3_client.get_object(
                Bucket=settings.AWS_S3_BUCKET_NAME,
                Key=key
            )
            return response['Body'].read()
        else:
            # Local fallback
            # In local mode, file_key_or_url is the absolute path to the local file
            if not os.path.exists(file_key_or_url):
                # Check if it exists relative to the uploads folder as well
                alt_path = os.path.join(UPLOAD_DIR, os.path.basename(file_key_or_url))
                if os.path.exists(alt_path):
                    file_key_or_url = alt_path
                else:
                    raise FileNotFoundError(f"Local file not found: {file_key_or_url}")
            
            with open(file_key_or_url, "rb") as f:
                return f.read()

    def delete_file(self, file_key_or_url: str) -> bool:
        """Deletes a file from local or cloud storage."""
        try:
            if self.storage_type == "s3":
                if not settings.AWS_S3_BUCKET_NAME:
                    raise ValueError("AWS_S3_BUCKET_NAME is not configured in settings.")
                key = self._extract_s3_key(file_key_or_url)
                self.s3_client.delete_object(
                    Bucket=settings.AWS_S3_BUCKET_NAME,
                    Key=key
                )
                return True
            else:
                # Local fallback
                if os.path.exists(file_key_or_url):
                    os.remove(file_key_or_url)
                    return True
                else:
                    alt_path = os.path.join(UPLOAD_DIR, os.path.basename(file_key_or_url))
                    if os.path.exists(alt_path):
                        os.remove(alt_path)
                        return True
                return False
        except Exception as e:
            print(f"Error deleting file {file_key_or_url}: {e}")
            return False

storage_service = StorageService()
