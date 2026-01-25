"""文件 URL 生成器 - 参考 FastAPI Template 实现"""

from datetime import timedelta
from typing import Optional

from configs import app_config
from extensions.ext_storage import storage
import logging


logger = logging.getLogger(__name__)


class FileUrlGenerator:
    """
    文件 URL 生成器

    根据不同的存储类型，生成对应的文件访问 URL。
    参考 FastAPI Template 的设计：
    - 云存储：返回预签名 URL（临时访问）或 CDN URL（永久访问）
    - 本地存储：返回应用代理 URL
    - MinIO：根据配置返回直接 URL 或预签名 URL
    """

    @staticmethod
    async def generate_url(
        file_key: str, expires_in: timedelta = timedelta(hours=1), use_cdn: bool = False
    ) -> str:
        """
        生成文件访问 URL

        Args:
            file_key: 文件在存储中的路径/键
            expires_in: 预签名 URL 过期时间（默认1小时）
            use_cdn: 是否使用 CDN URL（如果配置了）

        Returns:
            str: 文件访问 URL
        """
        storage_type = app_config.STORAGE_TYPE.lower()

        # 1. 优先使用 CDN（如果配置了）
        if use_cdn and hasattr(app_config, "CDN_DOMAIN") and app_config.CDN_DOMAIN:
            cdn_url = f"{app_config.CDN_DOMAIN.rstrip('/')}/{file_key}"
            logger.info(f"Generated CDN URL for {file_key}: {cdn_url}")
            return cdn_url

        # 2. 根据存储类型生成 URL
        try:
            if storage_type == "local":
                # 本地存储：通过应用服务器代理访问
                url = f"{app_config.FILES_URL.rstrip('/')}/console/api/files/local/{file_key}"
                logger.info(f"Generated local proxy URL for {file_key}")
                return url

            elif storage_type in [
                "s3",
                "aws-s3",
                "aliyun-oss",
                "oss",
                "tencent-cos",
                "cos",
                "huawei-obs",
                "obs",
            ]:
                # 云存储：使用预签名 URL
                url = await storage.storage_runner.generate_presigned_url(
                    file_key, expires_in=expires_in
                )
                logger.info(f"Generated {storage_type} presigned URL for {file_key}")
                return url

            elif storage_type in ["azure-blob", "google-cloud", "gcs"]:
                # 国际云存储：使用预签名 URL
                url = await storage.storage_runner.generate_presigned_url(
                    file_key, expires_in=expires_in
                )
                logger.info(f"Generated {storage_type} presigned URL for {file_key}")
                return url

            else:
                # 默认：尝试使用预签名 URL
                logger.warning(f"Unknown storage type: {storage_type}, using presigned URL")
                url = await storage.storage_runner.generate_presigned_url(
                    file_key, expires_in=expires_in
                )
                return url

        except Exception as e:
            logger.error(f"Failed to generate URL for {file_key}: {e}")
            # 降级方案：返回代理 URL
            fallback_url = (
                f"{app_config.FILES_URL.rstrip('/')}/console/api/files/download/{file_key}"
            )
            logger.info(f"Using fallback URL for {file_key}: {fallback_url}")
            return fallback_url

    @staticmethod
    async def generate_upload_url(
        file_key: str,
        expires_in: timedelta = timedelta(minutes=30),
        content_type: Optional[str] = None,
    ) -> str:
        """
        生成文件上传 URL（用于客户端直传）

        Args:
            file_key: 文件在存储中的路径/键
            expires_in: 预签名 URL 过期时间（默认30分钟）
            content_type: 文件 MIME 类型

        Returns:
            str: 上传 URL
        """
        storage_type = app_config.STORAGE_TYPE.lower()

        try:
            if storage_type in ["local"]:
                # 本地存储不支持直传，返回上传接口
                url = f"{app_config.FILES_URL.rstrip('/')}/console/api/files/upload"
                logger.info(f"Local storage does not support direct upload, using API endpoint")
                return url

            else:
                # 云存储和 MinIO：使用预签名上传 URL
                url = await storage.storage_runner.generate_presigned_upload_url(
                    file_key, expires_in=expires_in, content_type=content_type
                )
                logger.info(f"Generated presigned upload URL for {file_key}")
                return url

        except Exception as e:
            logger.error(f"Failed to generate upload URL for {file_key}: {e}")
            # 降级方案：返回上传接口
            fallback_url = f"{app_config.FILES_URL.rstrip('/')}/console/api/files/upload"
            return fallback_url

    @staticmethod
    def get_access_type() -> str:
        """
        获取当前存储的访问类型

        Returns:
            str: "presigned" | "proxy" | "direct" | "cdn"
        """
        storage_type = app_config.STORAGE_TYPE.lower()

        if hasattr(app_config, "CDN_DOMAIN") and app_config.CDN_DOMAIN:
            return "cdn"
        elif storage_type == "local":
            return "proxy"
        elif storage_type == "minio" and getattr(app_config, "MINIO_PUBLIC", False):
            return "direct"
        else:
            return "presigned"


# 全局实例
file_url_generator = FileUrlGenerator()


__all__ = ["FileUrlGenerator", "file_url_generator"]
