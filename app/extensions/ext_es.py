import functools
import logging
from collections.abc import Callable, Iterator
from typing import Any

from elasticsearch import ApiError, Elasticsearch, NotFoundError, TransportError
from elasticsearch.helpers import bulk, scan
from fastapi import FastAPI

from configs import app_config

logger = logging.getLogger(__name__)


class ESError(Exception):
    """Base exception for Elasticsearch operations."""

    pass


class IndexNotFoundError(ESError):
    """Raised when index does not exist."""

    pass


class DocumentNotFoundError(ESError):
    """Raised when document does not exist."""

    pass


class ESConnectionError(ESError):
    """Raised when connection to Elasticsearch fails."""

    pass


class ElasticsearchClient:
    """
    Elasticsearch client providing all ES operations.

    Usage:
        from extensions.ext_es import es_client

        # Index a document
        doc_id = es_client.index("my_index", {"title": "Hello"})

        # Search documents
        results = es_client.search("my_index", {"match": {"title": "Hello"}})

        # Bulk index
        es_client.bulk_index("my_index", [{"title": "Doc1"}, {"title": "Doc2"}])
    """

    def __init__(self) -> None:
        self._client: Elasticsearch | None = None

    def init_app(self, app: FastAPI) -> None:
        """Initialize ES client from app config."""
        try:
            self._client = self._create_client()
        except TransportError as e:
            raise ESConnectionError(f"Failed to connect to Elasticsearch: {e}") from e

    def _create_client(self) -> Elasticsearch | None:
        """Create Elasticsearch client based on configuration."""
        # Common arguments
        es_kwargs: dict[str, Any] = {
            "request_timeout": app_config.ELASTICSEARCH_REQUEST_TIMEOUT / 1000.0,
            "max_retries": app_config.ELASTICSEARCH_MAX_RETRIES,
            "retry_on_timeout": app_config.ELASTICSEARCH_RETRY_ON_TIMEOUT,
        }

        # SSL/TLS arguments
        ssl_kwargs: dict[str, Any] = {
            "verify_certs": app_config.ELASTICSEARCH_VERIFY_CERTS,
        }
        if app_config.ELASTICSEARCH_CA_CERTS:
            ssl_kwargs["ca_certs"] = app_config.ELASTICSEARCH_CA_CERTS

        # Elastic Cloud mode
        if app_config.ELASTICSEARCH_USE_CLOUD:
            if not app_config.ELASTICSEARCH_CLOUD_URL:
                raise ValueError("ELASTICSEARCH_CLOUD_URL is required when using Elastic Cloud")
            if not app_config.ELASTICSEARCH_API_KEY:
                raise ValueError("ELASTICSEARCH_API_KEY is required when using Elastic Cloud")

            return Elasticsearch(
                hosts=[app_config.ELASTICSEARCH_CLOUD_URL],
                api_key=app_config.ELASTICSEARCH_API_KEY,
                **es_kwargs,
                **ssl_kwargs,
            )

        # Self-hosted mode
        host = app_config.ELASTICSEARCH_HOST
        port = app_config.ELASTICSEARCH_PORT
        if not host:
            return None

        # Determine scheme
        if "://" not in host:
            use_ssl = bool(
                app_config.ELASTICSEARCH_CA_CERTS or app_config.ELASTICSEARCH_VERIFY_CERTS
            )
            scheme = "https" if use_ssl else "http"
            url = f"{scheme}://{host}:{port}"
        else:
            url = host if host.endswith(str(port)) else f"{host}:{port}"

        # Only add SSL kwargs for HTTPS
        if url.lower().startswith("https://"):
            es_kwargs.update(ssl_kwargs)

        # Only add basic_auth if credentials are configured
        if app_config.ELASTICSEARCH_USERNAME and app_config.ELASTICSEARCH_PASSWORD:
            es_kwargs["basic_auth"] = (
                app_config.ELASTICSEARCH_USERNAME,
                app_config.ELASTICSEARCH_PASSWORD,
            )

        return Elasticsearch(hosts=[url], **es_kwargs)

    @property
    def client(self) -> Elasticsearch:
        """Get the ES client, raise if not initialized."""
        if self._client is None:
            raise RuntimeError("Elasticsearch client is not initialized. Call init_app first.")
        return self._client

    def create_index(
        self,
        name: str,
        mappings: dict | None = None,
        settings: dict | None = None,
        ignore_existing: bool = False,
    ) -> bool:
        """
        Create an index.

        Args:
            name: Index name
            mappings: Field mappings definition
            settings: Index settings (shards, replicas, etc.)
            ignore_existing: If True, don't raise error if index exists

        Returns:
            True if index was created, False if already existed (when ignore_existing=True)

        Raises:
            ESError: If creation fails
        """
        try:
            body: dict[str, Any] = {}
            if mappings:
                body["mappings"] = mappings
            if settings:
                body["settings"] = settings

            self.client.indices.create(index=name, body=body if body else None)
            return True
        except ApiError as e:
            if e.error == "resource_already_exists_exception" and ignore_existing:
                return False
            raise ESError(f"Failed to create index {name}: {e}") from e

    def delete_index(self, name: str, ignore_missing: bool = False) -> bool:
        """
        Delete an index.

        Args:
            name: Index name
            ignore_missing: If True, don't raise error if index doesn't exist

        Returns:
            True if index was deleted, False if didn't exist (when ignore_missing=True)

        Raises:
            IndexNotFoundError: If index doesn't exist and ignore_missing=False
        """
        try:
            self.client.indices.delete(index=name)
            return True
        except NotFoundError as e:
            if ignore_missing:
                return False
            raise IndexNotFoundError(f"Index not found: {name}") from e
        except ApiError as e:
            raise ESError(f"Failed to delete index {name}: {e}") from e

    def index_exists(self, name: str) -> bool:
        """Check if index exists."""
        return self.client.indices.exists(index=name).body

    def get_index_info(self, name: str) -> dict:
        """
        Get index settings and mappings.

        Args:
            name: Index name

        Returns:
            Dict with index settings and mappings

        Raises:
            IndexNotFoundError: If index doesn't exist
        """
        try:
            result = self.client.indices.get(index=name)
            return result.body.get(name, {})
        except NotFoundError as e:
            raise IndexNotFoundError(f"Index not found: {name}") from e
        except ApiError as e:
            raise ESError(f"Failed to get index info for {name}: {e}") from e

    def index(
        self,
        index_name: str,
        document: dict,
        doc_id: str | None = None,
        refresh: bool = False,
    ) -> str:
        """
        Index a document.

        Args:
            index_name: Target index name
            document: Document to index
            doc_id: Optional document ID (auto-generated if not provided)
            refresh: If True, refresh index immediately after indexing

        Returns:
            Document ID
        """
        try:
            result = self.client.index(
                index=index_name,
                id=doc_id,
                document=document,
                refresh=refresh,
            )
            return result["_id"]
        except ApiError as e:
            raise ESError(f"Failed to index document: {e}") from e

    def get(self, index_name: str, doc_id: str) -> dict | None:
        """
        Get document by ID.

        Args:
            index_name: Index name
            doc_id: Document ID

        Returns:
            Document source dict, or None if not found
        """
        try:
            result = self.client.get(index=index_name, id=doc_id)
            return result["_source"]
        except NotFoundError:
            return None
        except ApiError as e:
            raise ESError(f"Failed to get document: {e}") from e

    def update(
        self,
        index_name: str,
        doc_id: str,
        partial_doc: dict,
        refresh: bool = False,
    ) -> bool:
        """
        Update document fields.

        Args:
            index_name: Index name
            doc_id: Document ID
            partial_doc: Fields to update
            refresh: If True, refresh index immediately after update

        Returns:
            True if updated successfully

        Raises:
            DocumentNotFoundError: If document doesn't exist
        """
        try:
            self.client.update(
                index=index_name,
                id=doc_id,
                doc=partial_doc,
                refresh=refresh,
            )
            return True
        except NotFoundError as e:
            raise DocumentNotFoundError(f"Document not found: {doc_id}") from e
        except ApiError as e:
            raise ESError(f"Failed to update document: {e}") from e

    def delete(
        self,
        index_name: str,
        doc_id: str,
        refresh: bool = False,
    ) -> bool:
        """
        Delete document by ID.

        Args:
            index_name: Index name
            doc_id: Document ID
            refresh: If True, refresh index immediately after deletion

        Returns:
            True if deleted successfully

        Raises:
            DocumentNotFoundError: If document doesn't exist
        """
        try:
            self.client.delete(index=index_name, id=doc_id, refresh=refresh)
            return True
        except NotFoundError as e:
            raise DocumentNotFoundError(f"Document not found: {doc_id}") from e
        except ApiError as e:
            raise ESError(f"Failed to delete document: {e}") from e

    def exists(self, index_name: str, doc_id: str) -> bool:
        """Check if document exists."""
        return self.client.exists(index=index_name, id=doc_id).body

    def search(
        self,
        index_name: str,
        query: dict | None = None,
        size: int = 10,
        from_: int = 0,
        sort: list | None = None,
        source: list | bool | None = None,
    ) -> dict:
        """
        Search documents.

        Args:
            index_name: Index name
            query: Elasticsearch query DSL
            size: Number of results to return
            from_: Offset for pagination
            sort: Sort specification
            source: Fields to include/exclude in results

        Returns:
            Dict with "hits" (list of documents) and "total" (total count)
        """
        try:
            body: dict[str, Any] = {"size": size, "from": from_}
            if query:
                body["query"] = query
            if sort:
                body["sort"] = sort
            if source is not None:
                body["_source"] = source

            result = self.client.search(index=index_name, body=body)

            hits = [
                {
                    "_id": hit["_id"],
                    "_source": hit["_source"],
                    "_score": hit.get("_score"),
                }
                for hit in result["hits"]["hits"]
            ]

            total = result["hits"]["total"]
            total_count = total["value"] if isinstance(total, dict) else total

            return {"hits": hits, "total": total_count}
        except NotFoundError as e:
            raise IndexNotFoundError(f"Index not found: {index_name}") from e
        except ApiError as e:
            raise ESError(f"Search failed: {e}") from e

    def count(self, index_name: str, query: dict | None = None) -> int:
        """
        Count documents matching query.

        Args:
            index_name: Index name
            query: Optional query to filter documents

        Returns:
            Document count
        """
        try:
            body = {"query": query} if query else None
            result = self.client.count(index=index_name, body=body)
            return result["count"]
        except NotFoundError as e:
            raise IndexNotFoundError(f"Index not found: {index_name}") from e
        except ApiError as e:
            raise ESError(f"Count failed: {e}") from e

    def scroll(
        self,
        index_name: str,
        query: dict | None = None,
        size: int = 100,
        scroll_time: str = "5m",
    ) -> Iterator[dict]:
        """
        Iterate through large result sets using scroll API.

        Args:
            index_name: Index name
            query: Optional query to filter documents
            size: Batch size per scroll request
            scroll_time: How long to keep scroll context alive

        Yields:
            Document dicts with _id and _source
        """
        try:
            body = {"query": query} if query else {"query": {"match_all": {}}}

            for hit in scan(
                self.client,
                index=index_name,
                query=body,
                size=size,
                scroll=scroll_time,
            ):
                yield {"_id": hit["_id"], "_source": hit["_source"]}
        except NotFoundError as e:
            raise IndexNotFoundError(f"Index not found: {index_name}") from e
        except ApiError as e:
            raise ESError(f"Scroll failed: {e}") from e

    def bulk_index(
        self,
        index_name: str,
        documents: list[dict],
        id_field: str | None = None,
        chunk_size: int = 500,
        refresh: bool = False,
    ) -> dict:
        """
        Bulk index documents.

        Args:
            index_name: Target index name
            documents: List of documents to index
            id_field: Field name to use as document ID (optional)
            chunk_size: Number of documents per bulk request
            refresh: If True, refresh index after bulk operation

        Returns:
            Dict with "success", "failed", and "errors" keys
        """
        if not documents:
            return {"success": 0, "failed": 0, "errors": []}

        actions = []
        for doc in documents:
            action = {"_index": index_name, "_source": doc}
            if id_field and id_field in doc:
                action["_id"] = doc[id_field]
            actions.append(action)

        try:
            success, errors = bulk(
                self.client,
                actions,
                chunk_size=chunk_size,
                refresh=refresh,
                raise_on_error=False,
                raise_on_exception=False,
            )

            error_list = []
            if errors:
                for error in errors:
                    error_info = error.get("index", error.get("create", {}))
                    error_list.append(
                        {
                            "id": error_info.get("_id"),
                            "error": error_info.get("error", {}).get("reason", str(error)),
                        }
                    )

            return {
                "success": success,
                "failed": len(error_list),
                "errors": error_list,
            }
        except ApiError as e:
            raise ESError(f"Bulk index failed: {e}") from e

    def bulk_delete(
        self,
        index_name: str,
        doc_ids: list[str],
        chunk_size: int = 500,
        refresh: bool = False,
    ) -> dict:
        """
        Bulk delete documents.

        Args:
            index_name: Index name
            doc_ids: List of document IDs to delete
            chunk_size: Number of deletions per bulk request
            refresh: If True, refresh index after bulk operation

        Returns:
            Dict with "success", "failed", and "errors" keys
        """
        if not doc_ids:
            return {"success": 0, "failed": 0, "errors": []}

        actions = [
            {"_op_type": "delete", "_index": index_name, "_id": doc_id} for doc_id in doc_ids
        ]

        try:
            success, errors = bulk(
                self.client,
                actions,
                chunk_size=chunk_size,
                refresh=refresh,
                raise_on_error=False,
                raise_on_exception=False,
            )

            error_list = []
            if errors:
                for error in errors:
                    error_info = error.get("delete", {})
                    error_list.append(
                        {
                            "id": error_info.get("_id"),
                            "error": error_info.get("error", {}).get("reason", str(error)),
                        }
                    )

            return {
                "success": success,
                "failed": len(error_list),
                "errors": error_list,
            }
        except ApiError as e:
            raise ESError(f"Bulk delete failed: {e}") from e


es_client: ElasticsearchClient = ElasticsearchClient()


def is_enabled() -> bool:
    """Check if Elasticsearch is enabled in configuration."""
    return bool(app_config.ELASTICSEARCH_HOST)


def init_app(app: FastAPI) -> None:
    """Initialize Elasticsearch extension."""
    es_client.init_app(app)
    app.state.elasticsearch = es_client


def es_fallback(default_return: Any = None):
    """
    Decorator to handle Elasticsearch operation exceptions and return a default value.

    Usage:
        @es_fallback(default_return=[])
        def get_documents():
            return es_client.search("my_index", {"match_all": {}})["hits"]

    Args:
        default_return: Value to return when ES operation fails. Defaults to None.
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (ApiError, TransportError, ESError) as e:
                func_name = getattr(func, "__name__", "Unknown")
                logger.warning(
                    "Elasticsearch operation failed in %s: %s",
                    func_name,
                    str(e),
                    exc_info=True,
                )
                return default_return

        return wrapper

    return decorator
