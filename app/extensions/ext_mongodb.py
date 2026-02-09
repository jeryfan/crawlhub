import logging
from typing import Any

from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

from configs import app_config

logger = logging.getLogger(__name__)


class MongoDBClient:
    """
    MongoDB client wrapper for async operations using Motor.

    Usage:
        from extensions.ext_mongodb import mongodb_client

        # Get database
        db = mongodb_client.db

        # Get collection
        collection = mongodb_client.get_collection("my_collection")

        # Insert document
        result = await collection.insert_one({"key": "value"})

        # Query documents
        cursor = collection.find({"status": "active"})
        async for doc in cursor:
            print(doc)

        # Create TTL index
        await mongodb_client.create_ttl_index("logs", "created_at", expire_seconds=86400 * 30)
    """

    def __init__(self) -> None:
        self._client: AsyncIOMotorClient | None = None
        self._db: AsyncIOMotorDatabase | None = None
        self._db_name: str = ""
        self._loop_id: int | None = None
        self._enabled: bool = False

    def init_app(self, app: FastAPI) -> None:
        """Initialize MongoDB client from app config."""
        if not app_config.MONGODB_ENABLED:
            logger.info("MongoDB is disabled, skipping initialization")
            return

        try:
            self._db_name = app_config.MONGODB_DATABASE
            self._client = self._create_client()
            self._db = self._client[self._db_name]
            self._enabled = True
            logger.info(f"MongoDB client initialized for database: {self._db_name}")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB client: {e}")
            raise

    def _create_client(self) -> AsyncIOMotorClient:
        """Create MongoDB client based on configuration."""
        return AsyncIOMotorClient(app_config.MONGODB_URI)

    def _ensure_current_loop(self) -> None:
        """在 Celery prefork worker 中，每次 asyncio.run() 会创建新的事件循环。
        Motor 客户端绑定到创建时的事件循环，循环关闭后会报 'Event loop is closed'。
        检测到事件循环变化时自动重建客户端。
        """
        if not self._enabled:
            return
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop_id = id(loop)
        if self._loop_id != loop_id:
            if self._client is not None:
                self._client.close()
            self._client = self._create_client()
            self._db = self._client[self._db_name]
            self._loop_id = loop_id

    @property
    def client(self) -> AsyncIOMotorClient:
        """Get the MongoDB client instance."""
        self._ensure_current_loop()
        if self._client is None:
            raise RuntimeError("MongoDB client not initialized. Call init_app() first.")
        return self._client

    @property
    def db(self) -> AsyncIOMotorDatabase:
        """Get the default database instance."""
        self._ensure_current_loop()
        if self._db is None:
            raise RuntimeError("MongoDB database not initialized. Call init_app() first.")
        return self._db

    def get_collection(self, name: str) -> AsyncIOMotorCollection:
        """Get a collection by name."""
        return self.db[name]

    def is_enabled(self) -> bool:
        """Check if MongoDB is enabled and initialized."""
        return self._enabled

    async def close(self) -> None:
        """Close the MongoDB client connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("MongoDB client closed")

    async def create_index(
        self,
        collection_name: str,
        keys: str | list[tuple[str, int]],
        **kwargs: Any,
    ) -> str:
        """
        Create an index on a collection.

        Args:
            collection_name: Name of the collection
            keys: Index keys (field name or list of (field, direction) tuples)
            **kwargs: Additional index options (unique, sparse, etc.)

        Returns:
            The name of the created index
        """
        collection = self.get_collection(collection_name)
        return await collection.create_index(keys, **kwargs)

    async def create_ttl_index(
        self,
        collection_name: str,
        field: str,
        expire_seconds: int,
        index_name: str | None = None,
    ) -> str:
        """
        Create a TTL (Time-To-Live) index for automatic document expiration.

        Args:
            collection_name: Name of the collection
            field: The datetime field to use for expiration
            expire_seconds: Number of seconds after which documents expire
            index_name: Optional custom index name

        Returns:
            The name of the created index
        """
        collection = self.get_collection(collection_name)
        name = index_name or f"{field}_ttl"
        return await collection.create_index(
            field,
            expireAfterSeconds=expire_seconds,
            name=name,
        )

    async def ensure_indexes(
        self,
        collection_name: str,
        indexes: list[dict[str, Any]],
    ) -> list[str]:
        """
        Ensure multiple indexes exist on a collection.

        Args:
            collection_name: Name of the collection
            indexes: List of index specifications, each containing:
                - keys: Index keys
                - Any additional index options

        Returns:
            List of created index names

        Example:
            await mongodb_client.ensure_indexes("users", [
                {"keys": "email", "unique": True},
                {"keys": [("created_at", -1)]},
                {"keys": "status", "sparse": True},
            ])
        """
        results = []
        for index_spec in indexes:
            keys = index_spec.pop("keys")
            name = await self.create_index(collection_name, keys, **index_spec)
            results.append(name)
        return results


mongodb_client = MongoDBClient()


def init_app(app: FastAPI) -> None:
    """Initialize MongoDB extension."""
    mongodb_client.init_app(app)


def is_enabled() -> bool:
    """Check if MongoDB is enabled in configuration."""
    return app_config.MONGODB_ENABLED
