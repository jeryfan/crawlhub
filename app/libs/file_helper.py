"""文件处理工具类 - 参考 FastAPI Template 设计"""

import hashlib
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple

from constants import (
    AUDIO_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
)

# 支持的压缩文件扩展名
ARCHIVE_EXTENSIONS = ["zip", "rar", "7z", "tar", "gz", "bz2", "xz"]
ARCHIVE_EXTENSIONS.extend([ext.upper() for ext in ARCHIVE_EXTENSIONS])


class FileHelper:
    """文件处理助手类"""

    @staticmethod
    def generate_unique_filename(original_filename: str, use_hash: bool = False) -> str:
        """
        生成唯一的文件名

        Args:
            original_filename: 原始文件名
            use_hash: 是否使用哈希值（更短的文件名）

        Returns:
            唯一的文件名
        """
        extension = FileHelper.get_file_extension(original_filename)

        if use_hash:
            # 使用 MD5 哈希
            hash_obj = hashlib.md5(original_filename.encode())
            unique_name = hash_obj.hexdigest()[:12]
        else:
            # 使用 UUID
            unique_name = str(uuid.uuid4())

        return f"{unique_name}{extension}"

    @staticmethod
    def get_file_extension(filename: str) -> str:
        """
        获取文件扩展名（小写，带点）

        Args:
            filename: 文件名

        Returns:
            文件扩展名，例如: ".pdf"
        """
        return Path(filename).suffix.lower()

    @staticmethod
    def get_filename_without_extension(filename: str) -> str:
        """
        获取不带扩展名的文件名

        Args:
            filename: 文件名

        Returns:
            不带扩展名的文件名
        """
        return Path(filename).stem

    @staticmethod
    def detect_mime_type(filename: str, content: Optional[bytes] = None) -> str:
        """
        检测 MIME 类型

        Args:
            filename: 文件名
            content: 文件内容（可选，用于更准确的检测）

        Returns:
            MIME 类型字符串
        """
        # 首先尝试从文件名推断
        mime_type, _ = mimetypes.guess_type(filename)

        if mime_type:
            return mime_type

        # 如果有内容，尝试从内容检测（需要 python-magic）
        if content:
            try:
                import magic

                mime = magic.Magic(mime=True)
                return mime.from_buffer(content)
            except ImportError:
                pass

        # 默认返回二进制类型
        return "application/octet-stream"

    @staticmethod
    def is_image(filename: str) -> bool:
        """判断是否为图片文件"""
        extension = FileHelper.get_file_extension(filename).lstrip(".")
        return extension in IMAGE_EXTENSIONS or extension.upper() in IMAGE_EXTENSIONS

    @staticmethod
    def is_document(filename: str) -> bool:
        """判断是否为文档文件"""
        extension = FileHelper.get_file_extension(filename).lstrip(".")
        return extension in DOCUMENT_EXTENSIONS or extension.upper() in DOCUMENT_EXTENSIONS

    @staticmethod
    def is_audio(filename: str) -> bool:
        """判断是否为音频文件"""
        extension = FileHelper.get_file_extension(filename).lstrip(".")
        return extension in AUDIO_EXTENSIONS or extension.upper() in AUDIO_EXTENSIONS

    @staticmethod
    def is_video(filename: str) -> bool:
        """判断是否为视频文件"""
        extension = FileHelper.get_file_extension(filename).lstrip(".")
        return extension in VIDEO_EXTENSIONS or extension.upper() in VIDEO_EXTENSIONS

    @staticmethod
    def is_archive(filename: str) -> bool:
        """判断是否为压缩文件"""
        extension = FileHelper.get_file_extension(filename).lstrip(".")
        return extension in ARCHIVE_EXTENSIONS or extension.upper() in ARCHIVE_EXTENSIONS

    @staticmethod
    def get_file_type(filename: str) -> str:
        """
        获取文件类型分类

        Returns:
            文件类型: "image", "document", "audio", "video", "archive", "other"
        """
        if FileHelper.is_image(filename):
            return "image"
        elif FileHelper.is_document(filename):
            return "document"
        elif FileHelper.is_audio(filename):
            return "audio"
        elif FileHelper.is_video(filename):
            return "video"
        elif FileHelper.is_archive(filename):
            return "archive"
        else:
            return "other"

    @staticmethod
    def validate_filename(filename: str, max_length: int = 255) -> Tuple[bool, Optional[str]]:
        """
        验证文件名是否合法

        Args:
            filename: 文件名
            max_length: 最大长度限制

        Returns:
            (是否合法, 错误信息)
        """
        if not filename:
            return False, "文件名不能为空"

        if len(filename) > max_length:
            return False, f"文件名长度超过限制 ({max_length} 字符)"

        # 检查非法字符
        illegal_chars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|", "\0"]
        for char in illegal_chars:
            if char in filename:
                return False, f"文件名包含非法字符: {char}"

        # 检查是否以点开头或结尾
        if filename.startswith(".") or filename.endswith("."):
            return False, "文件名不能以点开头或结尾"

        return True, None

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        清理文件名，移除非法字符

        Args:
            filename: 原始文件名

        Returns:
            清理后的文件名
        """
        # 获取扩展名和名称
        name = FileHelper.get_filename_without_extension(filename)
        extension = FileHelper.get_file_extension(filename)

        # 移除非法字符
        illegal_chars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|", "\0"]
        for char in illegal_chars:
            name = name.replace(char, "_")

        # 移除开头和结尾的点和空格
        name = name.strip(". ")

        # 限制长度（保留扩展名空间）
        max_name_length = 250 - len(extension)
        if len(name) > max_name_length:
            name = name[:max_name_length]

        return f"{name}{extension}"

    @staticmethod
    def calculate_file_hash(content: bytes, algorithm: str = "md5") -> str:
        """
        计算文件哈希值

        Args:
            content: 文件内容
            algorithm: 哈希算法 ("md5", "sha1", "sha256")

        Returns:
            哈希值字符串
        """
        if algorithm == "md5":
            hash_obj = hashlib.md5(content)
        elif algorithm == "sha1":
            hash_obj = hashlib.sha1(content)
        elif algorithm == "sha256":
            hash_obj = hashlib.sha256(content)
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

        return hash_obj.hexdigest()

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        格式化文件大小为可读格式

        Args:
            size_bytes: 字节大小

        Returns:
            格式化的大小字符串，例如: "1.5 MB"
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    @staticmethod
    def generate_file_path(
        user_id: str, filename: str, subfolder: Optional[str] = None, date_based: bool = True
    ) -> str:
        """
        生成文件存储路径

        Args:
            user_id: 用户 ID
            filename: 文件名
            subfolder: 子文件夹（可选）
            date_based: 是否使用日期组织（年/月/日）

        Returns:
            文件存储路径
        """
        from datetime import datetime

        parts = ["upload_files", user_id]

        # 添加日期路径
        if date_based:
            now = datetime.now()
            parts.extend([str(now.year), f"{now.month:02d}", f"{now.day:02d}"])

        # 添加子文件夹
        if subfolder:
            parts.append(subfolder)

        # 添加文件名
        parts.append(filename)

        return "/".join(parts)


__all__ = [
    "FileHelper",
    "IMAGE_EXTENSIONS",
    "DOCUMENT_EXTENSIONS",
    "AUDIO_EXTENSIONS",
    "VIDEO_EXTENSIONS",
    "ARCHIVE_EXTENSIONS",
]
