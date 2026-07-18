import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import get_settings

settings = get_settings()

_client = None


def get_s3_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            config=BotoConfig(signature_version="s3v4"),
        )
    return _client


def ensure_bucket_exists() -> None:
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
    except ClientError:
        client.create_bucket(Bucket=settings.S3_BUCKET_NAME)


def upload_object(key: str, fileobj, content_type: str) -> None:
    """Seção 17.2 — objetos ficam privados por padrão; o acesso é sempre via
    URL assinada e temporária (generate_presigned_url), nunca pública direta."""
    ensure_bucket_exists()
    get_s3_client().put_object(Bucket=settings.S3_BUCKET_NAME, Key=key, Body=fileobj, ContentType=content_type)


def generate_presigned_url(key: str, expires_seconds: int = 900) -> str:
    """Seção 17.2 — URLs de arquivos temporárias e assinadas."""
    return get_s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
        ExpiresIn=expires_seconds,
    )


def delete_object(key: str) -> None:
    get_s3_client().delete_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
