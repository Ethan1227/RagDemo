"""MinIO 对象存储服务：保存上传的原件（文档/证据）。

minio SDK 为同步实现，公开接口包装到线程池。懒连接 + 自动建桶。
"""
from __future__ import annotations

import asyncio
import io
import threading
import uuid
from pathlib import Path

from loguru import logger
from minio import Minio

from backend.app.core.config import get_settings

_client: Minio | None = None
_lock = threading.Lock()


def _get_client() -> Minio:
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                settings = get_settings()
                client = Minio(
                    settings.minio.endpoint,
                    access_key=settings.minio.access_key,
                    secret_key=settings.minio.secret_key,
                    secure=settings.minio.secure,
                )
                if not client.bucket_exists(settings.minio.bucket):
                    client.make_bucket(settings.minio.bucket)
                    logger.info("MinIO 桶 {} 创建完成", settings.minio.bucket)
                _client = client
    return _client


def _put_sync(object_name: str, data: bytes, content_type: str) -> None:
    settings = get_settings()
    _get_client().put_object(
        settings.minio.bucket,
        object_name,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )


def _remove_sync(object_name: str) -> None:
    settings = get_settings()
    _get_client().remove_object(settings.minio.bucket, object_name)


async def save_file(
    prefix: str, filename: str, data: bytes, content_type: str = "application/octet-stream"
) -> str:
    """保存文件，返回对象名（prefix/uuid+后缀）。"""
    object_name = f"{prefix}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"
    await asyncio.to_thread(_put_sync, object_name, data, content_type)
    logger.debug("MinIO 已保存：{}（{} 字节）", object_name, len(data))
    return object_name


async def remove_file(object_name: str) -> None:
    if not object_name:
        return
    await asyncio.to_thread(_remove_sync, object_name)
