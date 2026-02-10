"""
CrawlHub SDK - 爬虫数据上报 SDK

单文件，纯 stdlib，零依赖。被嵌入到爬虫工作目录中作为 crawlhub.py 使用。

用法:
    from crawlhub import save_item, report_progress, log, save_checkpoint, load_checkpoint, get_proxy, throttle

    save_item({"title": "...", "url": "..."})
    report_progress(50, "已处理50%")
    log("info", "开始抓取第2页")
    save_checkpoint({"page": 2})
    state = load_checkpoint()
"""

import atexit
import collections
import http.cookiejar
import json
import os
import random
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

# ─── Configuration from environment ───

_TASK_ID = os.environ.get("CRAWLHUB_TASK_ID", "")
_SPIDER_ID = os.environ.get("CRAWLHUB_SPIDER_ID", "")
_API_URL = os.environ.get("CRAWLHUB_API_URL", "").rstrip("/")
_PROXY_URL = os.environ.get("CRAWLHUB_PROXY_URL", "")
_RATE_LIMIT = os.environ.get("CRAWLHUB_RATE_LIMIT", "")
_MAX_ITEMS = int(os.environ.get("CRAWLHUB_MAX_ITEMS", "0")) or None
_OUTPUT_DIR = os.environ.get("CRAWLHUB_OUTPUT_DIR", "")
_DATASOURCES_JSON = os.environ.get("CRAWLHUB_DATASOURCES", "")

# ─── Internal state ───

_buffer: list[dict] = []
_buffer_lock = threading.Lock()
_FLUSH_SIZE = 50
_total_saved = 0
_total_saved_lock = threading.Lock()
_heartbeat_thread: threading.Thread | None = None
_heartbeat_stop = threading.Event()
_last_throttle = 0.0
_throttle_lock = threading.Lock()


def _is_configured() -> bool:
    return bool(_TASK_ID and _SPIDER_ID and _API_URL)


def _post(path: str, data: dict) -> dict | None:
    """Send a POST request to the internal API. Returns parsed JSON or None on failure."""
    if not _API_URL:
        return None
    url = f"{_API_URL}/crawlhub/internal{path}"
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        import sys
        body = e.read().decode("utf-8", errors="replace")[:200] if e.fp else ""
        print(f"[crawlhub:error] POST {url} → {e.code}: {body}", file=sys.stderr)
        return None
    except Exception as e:
        import sys
        print(f"[crawlhub:error] POST {url} failed: {e}", file=sys.stderr)
        return None


def _get(path: str) -> dict | None:
    """Send a GET request to the internal API."""
    if not _API_URL:
        return None
    url = f"{_API_URL}/crawlhub/internal{path}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        import sys
        print(f"[crawlhub:error] GET {url} → {e.code}", file=sys.stderr)
        return None
    except Exception as e:
        import sys
        print(f"[crawlhub:error] GET {url} failed: {e}", file=sys.stderr)
        return None


def _flush() -> None:
    """Flush buffered items to the API."""
    global _buffer
    with _buffer_lock:
        if not _buffer:
            return
        items = _buffer[:]
        _buffer = []

    if not _is_configured():
        return

    _post("/items", {
        "task_id": _TASK_ID,
        "spider_id": _SPIDER_ID,
        "items": items,
    })


def save_item(item: dict) -> None:
    """Save a single crawled item. Buffers locally and flushes in batches of 50."""
    global _total_saved

    if not isinstance(item, dict):
        return

    # Check max_items limit
    if _MAX_ITEMS is not None:
        with _total_saved_lock:
            if _total_saved >= _MAX_ITEMS:
                return
            _total_saved += 1

    with _buffer_lock:
        _buffer.append(item)
        should_flush = len(_buffer) >= _FLUSH_SIZE

    if should_flush:
        _flush()


def report_progress(percent: int, message: str | None = None) -> None:
    """Report task progress (0-100)."""
    if not _is_configured():
        return
    _post("/progress", {
        "task_id": _TASK_ID,
        "progress": max(0, min(100, percent)),
        "message": message,
    })


def log(level: str, message: str) -> None:
    """Send a structured log message. level: info/warn/error/debug."""
    # For now, just print. Could be extended to send to API.
    print(f"[crawlhub:{level}] {message}")


def save_checkpoint(data: dict) -> None:
    """Save checkpoint data for resume on failure."""
    if not _is_configured():
        return
    _post("/checkpoint", {
        "task_id": _TASK_ID,
        "checkpoint_data": data,
    })


def load_checkpoint() -> dict | None:
    """Load checkpoint from the most recent failed task of the same spider."""
    if not _is_configured():
        return None
    result = _get(f"/checkpoint?spider_id={_SPIDER_ID}")
    if result and isinstance(result, dict) and "data" in result:
        data = result["data"]
        if isinstance(data, dict) and data.get("checkpoint_data"):
            return data["checkpoint_data"]
    return None


def get_proxy() -> str | None:
    """Get the current proxy URL (may be updated by rotate_proxy)."""
    return _current_proxy


def throttle() -> None:
    """Wait based on rate limit setting. Call before each request."""
    global _last_throttle
    if not _RATE_LIMIT:
        return
    try:
        rps = float(_RATE_LIMIT)
        if rps <= 0:
            return
        interval = 1.0 / rps
    except (ValueError, ZeroDivisionError):
        return

    with _throttle_lock:
        now = time.monotonic()
        elapsed = now - _last_throttle
        if elapsed < interval:
            time.sleep(interval - elapsed)
        _last_throttle = time.monotonic()


def get_datasources() -> list[dict]:
    """返回所有配置的数据源连接信息。

    每个 dict 包含: id, name, type, host, port, username, password, database
    用户可使用这些信息直接连接数据库（需自行安装驱动）。
    """
    if not _DATASOURCES_JSON:
        return []
    try:
        ds_list = json.loads(_DATASOURCES_JSON)
        if isinstance(ds_list, list):
            return ds_list
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def get_datasource(name: str) -> dict | None:
    """按名称获取数据源连接信息。"""
    for ds in get_datasources():
        if ds.get("name") == name:
            return ds
    return None


# ─── Heartbeat background thread ───

_cancelled = False
_cancelled_lock = threading.Lock()


def is_cancelled() -> bool:
    """Check if the current task has been cancelled by the platform.

    Returns:
        True if the task has been cancelled.
    """
    with _cancelled_lock:
        return _cancelled


def _check_cancellation() -> None:
    """Poll the platform for task cancellation status."""
    global _cancelled
    if not _is_configured():
        return
    result = _get(f"/task/status?task_id={_TASK_ID}")
    if result and isinstance(result, dict):
        data = result.get("data", {})
        if isinstance(data, dict) and data.get("status") == "cancelled":
            with _cancelled_lock:
                _cancelled = True
            os._exit(130)


def _heartbeat_loop() -> None:
    """Background thread: send heartbeat every 30 seconds + check cancellation."""
    while not _heartbeat_stop.wait(30):
        if not _is_configured():
            continue
        with _total_saved_lock:
            count = _total_saved
        _post("/heartbeat", {
            "task_id": _TASK_ID,
            "items_count": count,
        })
        # Check for cancellation
        _check_cancellation()


def _start_heartbeat() -> None:
    global _heartbeat_thread
    if _heartbeat_thread is not None:
        return
    _heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    _heartbeat_thread.start()


# ─── Scrapy Pipeline ───

class CrawlHubPipeline:
    """Scrapy pipeline that sends items to CrawlHub.

    In Scrapy settings.py:
        ITEM_PIPELINES = {'crawlhub.CrawlHubPipeline': 300}
    """

    def process_item(self, item, spider):
        save_item(dict(item))
        return item

    def close_spider(self, spider):
        _flush()


# ─── 1.1 UA Rotation Pool ───

_UA_POOL: list[str] = [
    # Chrome (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Chrome (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Chrome (Linux)
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Firefox (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    # Firefox (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
    # Firefox (Linux)
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    # Safari (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Edge (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]


def get_random_ua() -> str:
    """Return a random User-Agent string from the built-in pool."""
    return random.choice(_UA_POOL)


def get_request_headers(extra: dict | None = None) -> dict:
    """Return a dict of common request headers with a random User-Agent.

    Args:
        extra: Optional dict of additional headers to merge in.

    Returns:
        A dict with User-Agent, Accept, Accept-Language, and Accept-Encoding
        headers, merged with any extra headers provided.
    """
    headers = {
        "User-Agent": get_random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
    }
    if extra:
        headers.update(extra)
    return headers


# ─── 1.2 Adaptive Throttle ───

_response_times: list[float] = []
_response_times_lock = threading.Lock()
_RESPONSE_TIMES_MAX = 50
_ADAPTIVE_MIN_SLEEP = 0.1   # seconds
_ADAPTIVE_MAX_SLEEP = 10.0  # seconds


def report_response_time(ms: float) -> None:
    """Record a response time (in milliseconds) for adaptive throttling.

    Keeps the most recent 50 entries.
    """
    with _response_times_lock:
        _response_times.append(ms)
        if len(_response_times) > _RESPONSE_TIMES_MAX:
            del _response_times[: len(_response_times) - _RESPONSE_TIMES_MAX]


def adaptive_throttle() -> None:
    """Sleep adaptively based on recent response times.

    - avg > 2000ms: sleep scales linearly from 2s up to 10s
    - avg 500ms-2000ms: sleep scales linearly from 0.1s to 2s
    - avg < 500ms: sleep the minimum (0.1s)

    If no response times have been recorded, sleeps the minimum.
    """
    with _response_times_lock:
        if not _response_times:
            avg = 0.0
        else:
            avg = sum(_response_times) / len(_response_times)

    if avg > 2000.0:
        # Scale linearly: 2000ms -> 2s sleep, 10000ms+ -> 10s sleep
        ratio = min((avg - 2000.0) / 8000.0, 1.0)
        sleep_time = 2.0 + ratio * (_ADAPTIVE_MAX_SLEEP - 2.0)
    elif avg >= 500.0:
        # Scale linearly: 500ms -> 0.1s sleep, 2000ms -> 2s sleep
        ratio = (avg - 500.0) / 1500.0
        sleep_time = _ADAPTIVE_MIN_SLEEP + ratio * (2.0 - _ADAPTIVE_MIN_SLEEP)
    else:
        sleep_time = _ADAPTIVE_MIN_SLEEP

    time.sleep(sleep_time)


# ─── 1.3 Cookie/Session Management ───

class SessionManager:
    """HTTP session manager with cookie persistence and optional proxy support.

    Uses stdlib http.cookiejar.CookieJar and urllib.request for zero-dependency
    cookie and session handling.

    Args:
        proxy: Optional proxy URL (e.g. "http://host:port"). If None, no proxy is used.
    """

    def __init__(self, proxy: str | None = None):
        self._cookie_jar = http.cookiejar.CookieJar()
        cookie_handler = urllib.request.HTTPCookieProcessor(self._cookie_jar)
        handlers: list = [cookie_handler]
        if proxy:
            proxy_handler = urllib.request.ProxyHandler({
                "http": proxy,
                "https": proxy,
            })
            handlers.append(proxy_handler)
        self._opener = urllib.request.build_opener(*handlers)

    @property
    def cookies(self) -> http.cookiejar.CookieJar:
        """Return the underlying CookieJar instance."""
        return self._cookie_jar

    def get(self, url: str, headers: dict | None = None, timeout: int = 30) -> bytes:
        """Perform an HTTP GET request with cookie handling.

        Args:
            url: The URL to fetch.
            headers: Optional dict of extra request headers.
            timeout: Request timeout in seconds.

        Returns:
            The response body as bytes.
        """
        req = urllib.request.Request(url, method="GET")
        if headers:
            for key, value in headers.items():
                req.add_header(key, value)
        with self._opener.open(req, timeout=timeout) as resp:
            return resp.read()

    def post(self, url: str, data: bytes | None = None, headers: dict | None = None,
             timeout: int = 30) -> bytes:
        """Perform an HTTP POST request with cookie handling.

        Args:
            url: The URL to post to.
            data: Optional request body as bytes.
            headers: Optional dict of extra request headers.
            timeout: Request timeout in seconds.

        Returns:
            The response body as bytes.
        """
        req = urllib.request.Request(url, data=data, method="POST")
        if headers:
            for key, value in headers.items():
                req.add_header(key, value)
        with self._opener.open(req, timeout=timeout) as resp:
            return resp.read()


# ─── 1.4 Retry with Exponential Backoff ───

def fetch_with_retry(
    url: str,
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    retry_on_status: tuple[int, ...] = (429, 500, 502, 503, 504),
    headers: dict | None = None,
    timeout: int = 30,
) -> bytes:
    """Fetch a URL with automatic retries and exponential backoff.

    Args:
        url: The URL to fetch.
        max_retries: Maximum number of retry attempts after the initial request.
        backoff_factor: Base factor for exponential backoff calculation.
        retry_on_status: HTTP status codes that should trigger a retry.
        headers: Optional dict of request headers.
        timeout: Request timeout in seconds.

    Returns:
        The response body as bytes.

    Raises:
        urllib.error.HTTPError: If the final attempt fails with an HTTP error.
        urllib.error.URLError: If the final attempt fails with a connection error.
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, method="GET")
            if headers:
                for key, value in headers.items():
                    req.add_header(key, value)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            last_exception = e
            if e.code not in retry_on_status or attempt == max_retries:
                raise
            # Read and discard the error body to free the connection
            if e.fp:
                e.read()
        except (urllib.error.URLError, OSError) as e:
            last_exception = e
            if attempt == max_retries:
                raise

        # Exponential backoff with random jitter
        delay = backoff_factor * (2 ** attempt) + random.uniform(0, 1)
        time.sleep(delay)

    # Should not reach here, but raise last exception as a safeguard
    if last_exception is not None:
        raise last_exception
    raise RuntimeError("fetch_with_retry: unexpected state")


# ─── 1.5 URL Queue/Dedup ───

def _normalize_url(url: str) -> str:
    """Normalize a URL for deduplication.

    Removes fragment, sorts query parameters, lowercases scheme and host.
    """
    parsed = urllib.parse.urlparse(url)
    # Lowercase scheme and host
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path
    # Sort query parameters
    query_params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query_params.sort()
    sorted_query = urllib.parse.urlencode(query_params)
    # Reconstruct without fragment
    return urllib.parse.urlunparse((scheme, netloc, path, parsed.params, sorted_query, ""))


class URLFrontier:
    """Thread-safe URL queue with deduplication.

    Uses a deque for FIFO ordering and a set for O(1) seen-URL lookups.
    URLs are normalized (fragment removed, query params sorted, scheme/host
    lowercased) before dedup checks.
    """

    def __init__(self):
        self._queue: collections.deque[tuple[str, dict | None]] = collections.deque()
        self._seen: set[str] = set()
        self._lock = threading.Lock()

    def add(self, url: str, meta: dict | None = None) -> bool:
        """Add a URL to the frontier.

        Args:
            url: The URL to add.
            meta: Optional metadata dict to associate with this URL.

        Returns:
            True if the URL was newly added, False if it was already seen.
        """
        normalized = _normalize_url(url)
        with self._lock:
            if normalized in self._seen:
                return False
            self._seen.add(normalized)
            self._queue.append((url, meta))
            return True

    def add_many(self, urls: list[str]) -> int:
        """Add multiple URLs to the frontier.

        Args:
            urls: List of URLs to add.

        Returns:
            The count of URLs that were newly added (not previously seen).
        """
        count = 0
        with self._lock:
            for url in urls:
                normalized = _normalize_url(url)
                if normalized not in self._seen:
                    self._seen.add(normalized)
                    self._queue.append((url, None))
                    count += 1
        return count

    def pop(self) -> tuple[str, dict | None]:
        """Pop the next URL from the frontier.

        Returns:
            A tuple of (url, meta) where meta may be None.

        Raises:
            IndexError: If the frontier is empty.
        """
        with self._lock:
            return self._queue.popleft()

    def is_empty(self) -> bool:
        """Return True if no URLs remain in the queue."""
        with self._lock:
            return len(self._queue) == 0

    def size(self) -> int:
        """Return the number of URLs remaining in the queue."""
        with self._lock:
            return len(self._queue)

    def seen_count(self) -> int:
        """Return the total number of unique URLs that have been added."""
        with self._lock:
            return len(self._seen)


# ─── 1.6 Incremental Crawl ───

class IncrementalCrawl:
    """Incremental crawl state manager with auto-save and URL deduplication.

    Builds on the existing save_checkpoint/load_checkpoint functions to provide
    a higher-level interface for managing crawl state across runs.

    Args:
        max_urls: Maximum number of seen URLs to retain in memory.
        auto_save_interval: Interval in seconds between automatic saves (0 to disable).
    """

    def __init__(self, max_urls: int = 10000, auto_save_interval: int = 60):
        self._max_urls = max_urls
        self._auto_save_interval = auto_save_interval
        self._seen_urls: set[str] = set()
        self._data: dict = {}
        self._lock = threading.Lock()
        self._auto_save_stop = threading.Event()
        self._auto_save_thread: threading.Thread | None = None

        # Attempt to load existing checkpoint
        checkpoint = load_checkpoint()
        if checkpoint and isinstance(checkpoint, dict):
            meta = checkpoint.get("_incremental_meta", {})
            if isinstance(meta, dict):
                saved_urls = meta.get("seen_urls", [])
                if isinstance(saved_urls, list):
                    self._seen_urls = set(saved_urls[-max_urls:])
            user_data = checkpoint.get("_incremental_data", {})
            if isinstance(user_data, dict):
                self._data = user_data

        # Start auto-save thread if configured
        if auto_save_interval > 0:
            self._auto_save_thread = threading.Thread(
                target=self._auto_save_loop, daemon=True
            )
            self._auto_save_thread.start()

    def _auto_save_loop(self) -> None:
        """Background thread that periodically saves state."""
        while not self._auto_save_stop.wait(self._auto_save_interval):
            self.save()

    def is_seen(self, url: str) -> bool:
        """Check whether a URL has been seen before.

        Args:
            url: The URL to check (normalized internally).

        Returns:
            True if the URL has been marked as seen.
        """
        normalized = _normalize_url(url)
        with self._lock:
            return normalized in self._seen_urls

    def mark_seen(self, url: str) -> None:
        """Mark a URL as seen.

        If the seen set exceeds max_urls, the oldest entries are discarded.

        Args:
            url: The URL to mark as seen (normalized internally).
        """
        normalized = _normalize_url(url)
        with self._lock:
            self._seen_urls.add(normalized)
            # Cap the set size by converting to list, trimming, and back
            if len(self._seen_urls) > self._max_urls:
                urls_list = list(self._seen_urls)
                self._seen_urls = set(urls_list[-self._max_urls:])

    def get(self, key: str, default=None):
        """Get a value from the incremental state store.

        Args:
            key: The key to look up.
            default: Value to return if key is not found.

        Returns:
            The stored value, or default if not found.
        """
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        """Set a value in the incremental state store.

        Args:
            key: The key to set.
            value: The value to store (must be JSON-serializable).
        """
        with self._lock:
            self._data[key] = value

    def save(self) -> None:
        """Persist the current state using save_checkpoint.

        Saves both the seen URLs and user-defined data to the CrawlHub checkpoint API.
        """
        with self._lock:
            checkpoint = {
                "_incremental_meta": {
                    "seen_urls": list(self._seen_urls)[-self._max_urls:],
                },
                "_incremental_data": dict(self._data),
            }
        save_checkpoint(checkpoint)

    def stop(self) -> None:
        """Stop the auto-save background thread."""
        self._auto_save_stop.set()
        if self._auto_save_thread is not None:
            self._auto_save_thread.join(timeout=5)

    def __del__(self):
        self._auto_save_stop.set()


# ─── 1.7 Request Middleware Chain ───

class RequestMiddleware:
    """Base class for request middleware.

    Subclass and override process_request and/or process_response
    to intercept and modify requests and responses in a middleware chain.
    """

    def process_request(self, url: str, headers: dict, meta: dict) -> tuple[str, dict, dict]:
        """Process an outgoing request before it is sent.

        Args:
            url: The target URL.
            headers: The request headers dict (mutable).
            meta: Arbitrary metadata dict (mutable).

        Returns:
            A tuple of (url, headers, meta), potentially modified.
        """
        return url, headers, meta

    def process_response(self, data: bytes, meta: dict) -> bytes:
        """Process an incoming response after it has been received.

        Args:
            data: The raw response body bytes.
            meta: The metadata dict from the request phase.

        Returns:
            The response data, potentially modified.
        """
        return data


class MiddlewareChain:
    """Executes a chain of RequestMiddleware instances around a fetch_with_retry call.

    Middlewares are executed in order for process_request, and in reverse order
    for process_response.
    """

    def __init__(self):
        self._middlewares: list[RequestMiddleware] = []

    def add(self, middleware: RequestMiddleware) -> None:
        """Add a middleware to the chain.

        Args:
            middleware: A RequestMiddleware instance.
        """
        self._middlewares.append(middleware)

    def execute(self, url: str, headers: dict | None = None, meta: dict | None = None,
                timeout: int = 30) -> bytes:
        """Execute the middleware chain: process_request -> fetch -> process_response.

        Args:
            url: The URL to fetch.
            headers: Optional initial request headers.
            meta: Optional metadata dict passed through all middlewares.
            timeout: Request timeout in seconds.

        Returns:
            The final response body as bytes after all middlewares have processed it.
        """
        if headers is None:
            headers = {}
        if meta is None:
            meta = {}

        # Forward pass: process_request in order
        current_url = url
        current_headers = headers
        current_meta = meta
        for mw in self._middlewares:
            current_url, current_headers, current_meta = mw.process_request(
                current_url, current_headers, current_meta
            )

        # Perform the actual HTTP fetch
        data = fetch_with_retry(
            current_url,
            headers=current_headers,
            timeout=timeout,
        )

        # Reverse pass: process_response in reverse order
        for mw in reversed(self._middlewares):
            data = mw.process_response(data, current_meta)

        return data


# ─── Proxy Runtime Rotation ───

_current_proxy: str | None = _PROXY_URL or None


def rotate_proxy(failed_proxy: str | None = None) -> str | None:
    """Request a new proxy from the platform, optionally reporting the failed one.

    Args:
        failed_proxy: The proxy URL that failed (optional).

    Returns:
        The new proxy URL, or None if no proxy is available.
    """
    global _current_proxy
    if not _is_configured():
        return _current_proxy

    params = f"?task_id={_TASK_ID}&spider_id={_SPIDER_ID}"
    if failed_proxy:
        params += f"&failed_proxy={urllib.parse.quote(failed_proxy)}"

    result = _get(f"/proxy/rotate{params}")
    if result and isinstance(result, dict):
        data = result.get("data", {})
        if isinstance(data, dict) and data.get("proxy_url"):
            _current_proxy = data["proxy_url"]
            return _current_proxy
    return _current_proxy


# ─── File Download Pipeline ───

def download_file(url: str, filename: str | None = None, upload: bool = True) -> str:
    """Download a file from URL and optionally upload to platform storage.

    Args:
        url: The URL to download from.
        filename: Local filename to save as. If None, derived from URL.
        upload: Whether to upload the file to platform storage.

    Returns:
        The local file path where the file was saved.
    """
    if not filename:
        # Derive filename from URL
        url_path = urllib.parse.urlparse(url).path
        filename = url_path.split("/")[-1] or "download"

    # Download to local output directory
    output_dir = _OUTPUT_DIR or "."
    os.makedirs(output_dir, exist_ok=True)
    local_path = os.path.join(output_dir, filename)

    req = urllib.request.Request(url)
    req.add_header("User-Agent", get_random_ua())
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    with open(local_path, "wb") as f:
        f.write(data)

    # Upload to platform storage
    if upload and _is_configured():
        _upload_file(local_path, filename)

    return local_path


def _upload_file(local_path: str, filename: str) -> None:
    """Upload a file to the platform using multipart form data (stdlib only)."""
    if not _API_URL:
        return

    url = f"{_API_URL}/crawlhub/internal/files/upload"

    with open(local_path, "rb") as f:
        file_data = f.read()

    # Build multipart form data manually
    boundary = f"----CrawlHubBoundary{int(time.time() * 1000)}"

    body_parts = []
    # task_id field
    body_parts.append(f"--{boundary}\r\n")
    body_parts.append('Content-Disposition: form-data; name="task_id"\r\n\r\n')
    body_parts.append(f"{_TASK_ID}\r\n")
    # spider_id field
    body_parts.append(f"--{boundary}\r\n")
    body_parts.append('Content-Disposition: form-data; name="spider_id"\r\n\r\n')
    body_parts.append(f"{_SPIDER_ID}\r\n")
    # filename field
    body_parts.append(f"--{boundary}\r\n")
    body_parts.append('Content-Disposition: form-data; name="filename"\r\n\r\n')
    body_parts.append(f"{filename}\r\n")
    # file field
    body_parts.append(f"--{boundary}\r\n")
    body_parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n')
    body_parts.append("Content-Type: application/octet-stream\r\n\r\n")

    body_bytes = "".join(body_parts).encode("utf-8") + file_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body_bytes,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
    except Exception as e:
        import sys
        print(f"[crawlhub:error] File upload failed: {e}", file=sys.stderr)


# ─── Auto-init on import ───

if _is_configured():
    _start_heartbeat()
    atexit.register(_flush)
    atexit.register(_heartbeat_stop.set)
