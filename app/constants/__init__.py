IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp", "gif", "svg", "bmp", "ico"]
IMAGE_EXTENSIONS.extend([ext.upper() for ext in IMAGE_EXTENSIONS])

VIDEO_EXTENSIONS = ["mp4", "mov", "mpeg", "mpga", "avi", "flv", "wmv", "webm"]
VIDEO_EXTENSIONS.extend([ext.upper() for ext in VIDEO_EXTENSIONS])

AUDIO_EXTENSIONS = ["mp3", "m4a", "wav", "webm", "amr", "aac", "flac", "ogg"]
AUDIO_EXTENSIONS.extend([ext.upper() for ext in AUDIO_EXTENSIONS])

DOCUMENT_EXTENSIONS = [
    "txt",
    "markdown",
    "md",
    "mdx",
    "pdf",
    "html",
    "htm",
    "xlsx",
    "xls",
    "docx",
    "doc",
    "pptx",
    "ppt",
    "csv",
    "vtt",
    "properties",
    "json",
    "xml",
    "yaml",
    "yml",
]
DOCUMENT_EXTENSIONS.extend([ext.upper() for ext in DOCUMENT_EXTENSIONS])

# console (用户端)
COOKIE_NAME_ACCESS_TOKEN = "access_token"
COOKIE_NAME_REFRESH_TOKEN = "refresh_token"
COOKIE_NAME_CSRF_TOKEN = "csrf_token"

# admin (管理端) - 使用不同的cookie名称避免与用户端冲突
COOKIE_NAME_ADMIN_ACCESS_TOKEN = "admin_access_token"
COOKIE_NAME_ADMIN_REFRESH_TOKEN = "admin_refresh_token"
COOKIE_NAME_ADMIN_CSRF_TOKEN = "admin_csrf_token"

# webapp
COOKIE_NAME_WEBAPP_ACCESS_TOKEN = "webapp_access_token"
COOKIE_NAME_PASSPORT = "passport"

HEADER_NAME_CSRF_TOKEN = "X-CSRF-Token"
HEADER_NAME_APP_CODE = "X-App-Code"
HEADER_NAME_PASSPORT = "X-App-Passport"


SYSTEM_UUID = "ffffffff-ffff-ffff-ffff-ffffffffffff"
HIDDEN_VALUE = "[__HIDDEN__]"
