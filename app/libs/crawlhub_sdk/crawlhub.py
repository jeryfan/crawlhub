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
import json
import os
import threading
import time
import urllib.error
import urllib.request

# ─── Configuration from environment ───

_TASK_ID = os.environ.get("CRAWLHUB_TASK_ID", "")
_SPIDER_ID = os.environ.get("CRAWLHUB_SPIDER_ID", "")
_API_URL = os.environ.get("CRAWLHUB_API_URL", "").rstrip("/")
_PROXY_URL = os.environ.get("CRAWLHUB_PROXY_URL", "")
_RATE_LIMIT = os.environ.get("CRAWLHUB_RATE_LIMIT", "")
_MAX_ITEMS = int(os.environ.get("CRAWLHUB_MAX_ITEMS", "0")) or None
_OUTPUT_DIR = os.environ.get("CRAWLHUB_OUTPUT_DIR", "")

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
    except (urllib.error.URLError, OSError, json.JSONDecodeError, Exception):
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
    except (urllib.error.URLError, OSError, json.JSONDecodeError, Exception):
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
    """Get the proxy URL injected by the platform."""
    return _PROXY_URL or None


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


# ─── Heartbeat background thread ───

def _heartbeat_loop() -> None:
    """Background thread: send heartbeat every 30 seconds."""
    while not _heartbeat_stop.wait(30):
        if not _is_configured():
            continue
        with _total_saved_lock:
            count = _total_saved
        _post("/heartbeat", {
            "task_id": _TASK_ID,
            "items_count": count,
        })


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


# ─── Auto-init on import ───

if _is_configured():
    _start_heartbeat()
    atexit.register(_flush)
    atexit.register(_heartbeat_stop.set)
