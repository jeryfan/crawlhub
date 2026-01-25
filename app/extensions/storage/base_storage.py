"""Abstract interface for file storage implementations."""

from abc import ABC, abstractmethod
from collections.abc import Generator
from datetime import timedelta
from typing import AsyncGenerator, Optional


class BaseStorage(ABC):
    """Interface for file storage."""

    @abstractmethod
    async def save(self, filename: str, data: bytes) -> None:
        """
        Save file data to storage.

        Args:
            filename: File path/key in storage
            data: File content as bytes
        """
        raise NotImplementedError

    @abstractmethod
    async def load_once(self, filename: str) -> bytes:
        """
        Load entire file content at once.

        Args:
            filename: File path/key in storage

        Returns:
            File content as bytes
        """
        raise NotImplementedError

    @abstractmethod
    def load_stream(self, filename: str) -> AsyncGenerator:
        """
        Load file content as stream (for large files).

        Args:
            filename: File path/key in storage

        Yields:
            File content chunks as bytes
        """
        raise NotImplementedError

    @abstractmethod
    async def download(self, filename: str, target_filepath: str) -> None:
        """
        Download file to local path.

        Args:
            filename: File path/key in storage
            target_filepath: Local file path to save
        """
        raise NotImplementedError

    @abstractmethod
    async def exists(self, filename: str) -> bool:
        """
        Check if file exists in storage.

        Args:
            filename: File path/key in storage

        Returns:
            True if file exists, False otherwise
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, filename: str) -> None:
        """
        Delete file from storage.

        Args:
            filename: File path/key in storage
        """
        raise NotImplementedError

    async def list(self, path: str, files: bool = True, directories: bool = False) -> list[str]:
        """
        Scan files and directories in the given path.
        This method is implemented only in some storage backends.
        If a storage backend doesn't support scanning, it will raise NotImplementedError.

        Args:
            path: Directory path to list
            files: Include files in results
            directories: Include directories in results

        Returns:
            List of file/directory paths
        """
        raise NotImplementedError("This storage backend doesn't support scanning")

    async def generate_presigned_url(
        self,
        filename: str,
        expires_in: timedelta = timedelta(hours=1),
        content_type: Optional[str] = None,
    ) -> str:
        """
        Generate a presigned URL for temporary access to a file.

        Args:
            filename: File path/key in storage
            expires_in: URL expiration time
            content_type: Content type for the response

        Returns:
            Presigned URL string
        """
        raise NotImplementedError("This storage backend doesn't support presigned URLs")

    async def generate_presigned_upload_url(
        self,
        filename: str,
        expires_in: timedelta = timedelta(hours=1),
        content_type: Optional[str] = None,
    ) -> str:
        """
        Generate a presigned URL for uploading a file.

        Args:
            filename: File path/key in storage
            expires_in: URL expiration time
            content_type: Expected content type

        Returns:
            Presigned upload URL string
        """
        raise NotImplementedError("This storage backend doesn't support presigned upload URLs")

    async def get_file_size(self, filename: str) -> int:
        """
        Get file size in bytes.

        Args:
            filename: File path/key in storage

        Returns:
            File size in bytes
        """
        raise NotImplementedError("This storage backend doesn't support getting file size")

    async def get_file_metadata(self, filename: str) -> dict:
        """
        Get file metadata (size, content type, last modified, etc).

        Args:
            filename: File path/key in storage

        Returns:
            Dictionary containing file metadata
        """
        raise NotImplementedError("This storage backend doesn't support getting file metadata")
