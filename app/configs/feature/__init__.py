from enum import StrEnum
from typing import Literal

from pydantic import (
    AliasChoices,
    Field,
    HttpUrl,
    NegativeInt,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    computed_field,
)
from pydantic_settings import BaseSettings


class SecurityConfig(BaseSettings):
    """
    Security-related configurations for the application
    """

    SECRET_KEY: str = Field(
        description="Secret key for secure session cookie signing."
        "Make sure you are changing this key for your deployment with a strong key."
        "Generate a strong key using `openssl rand -base64 42` or set via the `SECRET_KEY` environment variable.",
        default="+2vFXMcDT93epscqJLgnHjvRVnx8416fKfn8TJTVPnWz2P3jqV46MOAA",
    )

    RESET_PASSWORD_TOKEN_EXPIRY_MINUTES: PositiveInt = Field(
        description="Duration in minutes for which a password reset token remains valid",
        default=5,
    )

    EMAIL_REGISTER_TOKEN_EXPIRY_MINUTES: PositiveInt = Field(
        description="Duration in minutes for which a email register token remains valid",
        default=5,
    )

    CHANGE_EMAIL_TOKEN_EXPIRY_MINUTES: PositiveInt = Field(
        description="Duration in minutes for which a change email token remains valid",
        default=5,
    )

    OWNER_TRANSFER_TOKEN_EXPIRY_MINUTES: PositiveInt = Field(
        description="Duration in minutes for which a owner transfer token remains valid",
        default=5,
    )

    LOGIN_DISABLED: bool = Field(
        description="Whether to disable login checks",
        default=False,
    )

    ADMIN_API_KEY_ENABLE: bool = Field(
        description="Whether to enable admin api key for authentication",
        default=False,
    )

    ADMIN_API_KEY: str | None = Field(
        description="admin api key for authentication",
        default=None,
    )


class FileAccessConfig(BaseSettings):
    """
    Configuration for file access and handling
    """

    FILES_URL: str = Field(
        description="Base URL for file preview or download,"
        " used for frontend display and multi-model inputs"
        "Url is signed and has expiration time.",
        validation_alias=AliasChoices("FILES_URL", "CONSOLE_API_URL"),
        alias_priority=1,
        default="",
    )

    INTERNAL_FILES_URL: str = Field(
        description="Internal base URL for file access within Docker network,"
        " used for plugin daemon and internal service communication."
        " Falls back to FILES_URL if not specified.",
        default="",
    )

    FILES_ACCESS_TIMEOUT: int = Field(
        description="Expiration time in seconds for file access URLs",
        default=300,
    )


class FileUploadConfig(BaseSettings):
    """
    Configuration for file upload limitations
    """

    UPLOAD_FILE_SIZE_LIMIT: NonNegativeInt = Field(
        description="Maximum allowed file size for uploads in megabytes",
        default=15,
    )

    UPLOAD_FILE_BATCH_LIMIT: NonNegativeInt = Field(
        description="Maximum number of files allowed in a single upload batch",
        default=5,
    )

    UPLOAD_IMAGE_FILE_SIZE_LIMIT: NonNegativeInt = Field(
        description="Maximum allowed image file size for uploads in megabytes",
        default=10,
    )

    UPLOAD_VIDEO_FILE_SIZE_LIMIT: NonNegativeInt = Field(
        description="video file size limit in Megabytes for uploading files",
        default=100,
    )

    UPLOAD_AUDIO_FILE_SIZE_LIMIT: NonNegativeInt = Field(
        description="audio file size limit in Megabytes for uploading files",
        default=50,
    )

    BATCH_UPLOAD_LIMIT: NonNegativeInt = Field(
        description="Maximum number of files allowed in a batch upload operation",
        default=20,
    )

    inner_UPLOAD_FILE_EXTENSION_BLACKLIST: str = Field(
        description=(
            "Comma-separated list of file extensions that are blocked from upload. "
            "Extensions should be lowercase without dots (e.g., 'exe,bat,sh,dll'). "
            "Empty by default to allow all file types."
        ),
        validation_alias=AliasChoices("UPLOAD_FILE_EXTENSION_BLACKLIST"),
        default="",
    )

    @computed_field  # type: ignore[misc]
    @property
    def UPLOAD_FILE_EXTENSION_BLACKLIST(self) -> set[str]:
        """
        Parse and return the blacklist as a set of lowercase extensions.
        Returns an empty set if no blacklist is configured.
        """
        if not self.inner_UPLOAD_FILE_EXTENSION_BLACKLIST:
            return set()
        return {
            ext.strip().lower().strip(".")
            for ext in self.inner_UPLOAD_FILE_EXTENSION_BLACKLIST.split(",")
            if ext.strip()
        }


class RagEtlConfig(BaseSettings):
    """
    Configuration for RAG ETL processes
    """

    # TODO: This config is not only for rag etl, it is also for file upload, we should move it to file upload config
    ETL_TYPE: str = Field(
        description="RAG ETL type ('fastapi' or 'Unstructured'), default to 'fastapi'",
        default="fastapi",
    )

    KEYWORD_DATA_SOURCE_TYPE: str = Field(
        description="Data source type for keyword extraction"
        " ('database' or other supported types), default to 'database'",
        default="database",
    )

    UNSTRUCTURED_API_URL: str | None = Field(
        description="API URL for Unstructured.io service",
        default=None,
    )

    UNSTRUCTURED_API_KEY: str | None = Field(
        description="API key for Unstructured.io service",
        default="",
    )

    SCARF_NO_ANALYTICS: str | None = Field(
        description="This is about whether to disable Scarf analytics in Unstructured library.",
        default="false",
    )


class IndexingConfig(BaseSettings):
    """
    Configuration for indexing operations
    """

    INDEXING_MAX_SEGMENTATION_TOKENS_LENGTH: PositiveInt = Field(
        description="Maximum token length for text segmentation during indexing",
        default=4000,
    )

    CHILD_CHUNKS_PREVIEW_NUMBER: PositiveInt = Field(
        description="Maximum number of child chunks to preview",
        default=50,
    )


class CeleryBeatConfig(BaseSettings):
    CELERY_BEAT_SCHEDULER_TIME: int = Field(
        description="Interval in days for Celery Beat scheduler execution, default to 1 day",
        default=1,
    )


class LoggingConfig(BaseSettings):
    """
    Configuration for application logging
    """

    LOG_LEVEL: str = Field(
        description="Logging level, default to INFO. Set to ERROR for production environments.",
        default="INFO",
    )

    LOG_FILE: str | None = Field(
        description="File path for log output.",
        default=None,
    )

    LOG_FILE_MAX_SIZE: PositiveInt = Field(
        description="Maximum file size for file rotation retention, the unit is megabytes (MB)",
        default=20,
    )

    LOG_FILE_BACKUP_COUNT: PositiveInt = Field(
        description="Maximum file backup count file rotation retention",
        default=5,
    )

    LOG_FORMAT: str = Field(
        description="Format string for log messages",
        default=(
            "%(asctime)s.%(msecs)03d %(levelname)s [%(threadName)s] "
            "[%(filename)s:%(lineno)d] %(trace_id)s - %(message)s"
        ),
    )

    LOG_DATEFORMAT: str | None = Field(
        description="Date format string for log timestamps",
        default=None,
    )

    LOG_TZ: str | None = Field(
        description="Timezone for log timestamps (e.g., 'America/New_York')",
        default="UTC",
    )


class TemplateMode(StrEnum):
    # unsafe mode allows flexible operations in templates, but may cause security vulnerabilities
    UNSAFE = "unsafe"

    # sandbox mode restricts some unsafe operations like accessing __class__.
    # however, it is still not 100% safe, for example, cpu exploitation can happen.
    SANDBOX = "sandbox"

    # templating is disabled
    DISABLED = "disabled"


class MailConfig(BaseSettings):
    """
    Configuration for email services
    """

    MAIL_TEMPLATING_MODE: TemplateMode = Field(
        description="Template mode for email services",
        default=TemplateMode.SANDBOX,
    )

    MAIL_TEMPLATING_TIMEOUT: int = Field(
        description="""
        Timeout for email templating in seconds. Used to prevent infinite loops in malicious templates.
        Only available in sandbox mode.""",
        default=3,
    )

    MAIL_TYPE: str | None = Field(
        description="Email service provider type ('smtp' or 'resend' or 'sendGrid), default to None.",
        default=None,
    )

    MAIL_DEFAULT_SEND_FROM: str | None = Field(
        description="Default email address to use as the sender",
        default=None,
    )

    RESEND_API_KEY: str | None = Field(
        description="API key for Resend email service",
        default=None,
    )

    RESEND_API_URL: str | None = Field(
        description="API URL for Resend email service",
        default=None,
    )

    SMTP_SERVER: str | None = Field(
        description="SMTP server hostname",
        default=None,
    )

    SMTP_PORT: int | None = Field(
        description="SMTP server port number",
        default=465,
    )

    SMTP_USERNAME: str | None = Field(
        description="Username for SMTP authentication",
        default=None,
    )

    SMTP_PASSWORD: str | None = Field(
        description="Password for SMTP authentication",
        default=None,
    )

    SMTP_USE_TLS: bool = Field(
        description="Enable TLS encryption for SMTP connections",
        default=False,
    )

    SMTP_OPPORTUNISTIC_TLS: bool = Field(
        description="Enable opportunistic TLS for SMTP connections",
        default=False,
    )

    EMAIL_SEND_IP_LIMIT_PER_MINUTE: PositiveInt = Field(
        description="Maximum number of emails allowed to be sent from the same IP address in a minute",
        default=50,
    )

    SENDGRID_API_KEY: str | None = Field(
        description="API key for SendGrid service",
        default=None,
    )


class EndpointConfig(BaseSettings):
    """
    Configuration for various application endpoints and URLs
    """

    CONSOLE_API_URL: str = Field(
        description="Base URL for the console API,"
        "used for login authentication callback or notion integration callbacks",
        default="",
    )

    CONSOLE_WEB_URL: str = Field(
        description="Base URL for the console web interface,used for frontend references and CORS configuration",
        default="",
    )

    SERVICE_API_URL: str = Field(
        description="Base URL for the service API, displayed to users for API access",
        default="",
    )

    APP_WEB_URL: str = Field(
        description="Base URL for the web application, used for frontend references",
        default="",
    )

    ENDPOINT_URL_TEMPLATE: str = Field(
        description="Template url for endpoint plugin",
        default="http://localhost:5002/e/{hook_id}",
    )

    TRIGGER_URL: str = Field(
        description="Template url for triggers", default="http://localhost:8000"
    )


class BillingConfig(BaseSettings):
    """
    Configuration for platform billing features
    """

    BILLING_ENABLED: bool = Field(
        description="Enable or disable billing functionality",
        default=False,
    )


class AuthConfig(BaseSettings):
    """
    Configuration for authentication and OAuth
    """

    OAUTH_REDIRECT_PATH: str = Field(
        description="Redirect path for OAuth authentication callbacks",
        default="/console/api/oauth/authorize",
    )

    GITHUB_CLIENT_ID: str | None = Field(
        description="GitHub OAuth client ID",
        default=None,
    )

    GITHUB_CLIENT_SECRET: str | None = Field(
        description="GitHub OAuth client secret",
        default=None,
    )

    GOOGLE_CLIENT_ID: str | None = Field(
        description="Google OAuth client ID",
        default=None,
    )

    GOOGLE_CLIENT_SECRET: str | None = Field(
        description="Google OAuth client secret",
        default=None,
    )

    WECHAT_APP_ID: str | None = Field(
        description="WeChat OAuth app ID (微信开放平台)",
        default=None,
    )

    WECHAT_APP_SECRET: str | None = Field(
        description="WeChat OAuth app secret (微信开放平台)",
        default=None,
    )

    ACCESS_TOKEN_EXPIRE_MINUTES: PositiveInt = Field(
        description="Expiration time for access tokens in minutes",
        default=60,
    )

    REFRESH_TOKEN_EXPIRE_DAYS: PositiveFloat = Field(
        description="Expiration time for refresh tokens in days",
        default=30,
    )

    LOGIN_LOCKOUT_DURATION: PositiveInt = Field(
        description="Time (in seconds) a user must wait before retrying login after exceeding the rate limit.",
        default=86400,
    )

    FORGOT_PASSWORD_LOCKOUT_DURATION: PositiveInt = Field(
        description="Time (in seconds) a user must wait before retrying password reset after exceeding the rate limit.",
        default=86400,
    )

    CHANGE_EMAIL_LOCKOUT_DURATION: PositiveInt = Field(
        description="Time (in seconds) a user must wait before retrying change email after exceeding the rate limit.",
        default=86400,
    )

    OWNER_TRANSFER_LOCKOUT_DURATION: PositiveInt = Field(
        description="Time (in seconds) a user must wait before retrying owner transfer after exceeding the rate limit.",
        default=86400,
    )

    EMAIL_REGISTER_LOCKOUT_DURATION: PositiveInt = Field(
        description="Time (in seconds) a user must wait before retrying email register after exceeding the rate limit.",
        default=86400,
    )


class WorkspaceConfig(BaseSettings):
    """
    Configuration for workspace management
    """

    INVITE_EXPIRY_HOURS: PositiveInt = Field(
        description="Expiration time in hours for workspace invitation links",
        default=72,
    )


class LoginConfig(BaseSettings):
    ENABLE_EMAIL_CODE_LOGIN: bool = Field(
        description="whether to enable email code login",
        default=True,
    )
    ENABLE_EMAIL_PASSWORD_LOGIN: bool = Field(
        description="whether to enable email password login",
        default=True,
    )
    ENABLE_SOCIAL_OAUTH_LOGIN: bool = Field(
        description="whether to enable github/google oauth login",
        default=True,
    )
    EMAIL_CODE_LOGIN_TOKEN_EXPIRY_MINUTES: PositiveInt = Field(
        description="expiry time in minutes for email code login token",
        default=5,
    )
    ALLOW_REGISTER: bool = Field(
        description="whether to enable register",
        default=False,
    )
    ALLOW_CREATE_WORKSPACE: bool = Field(
        description="whether to enable create workspace",
        default=False,
    )


class AccountConfig(BaseSettings):
    ACCOUNT_DELETION_TOKEN_EXPIRY_MINUTES: PositiveInt = Field(
        description="Duration in minutes for which a account deletion token remains valid",
        default=5,
    )

    EDUCATION_ENABLED: bool = Field(
        description="whether to enable education identity",
        default=False,
    )


class HttpConfig(BaseSettings):
    """
    HTTP-related configurations for the application
    """

    COOKIE_DOMAIN: str = Field(
        description="Explicit cookie domain for console/service cookies when sharing across subdomains",
        default="",
    )

    API_COMPRESSION_ENABLED: bool = Field(
        description="Enable or disable gzip compression for HTTP responses",
        default=False,
    )

    inner_CONSOLE_CORS_ALLOW_ORIGINS: str = Field(
        description="Comma-separated list of allowed origins for CORS in the console",
        validation_alias=AliasChoices("CONSOLE_CORS_ALLOW_ORIGINS", "CONSOLE_WEB_URL"),
        default="",
    )

    @computed_field
    def CONSOLE_CORS_ALLOW_ORIGINS(self) -> list[str]:
        return self.inner_CONSOLE_CORS_ALLOW_ORIGINS.split(",")

    inner_WEB_API_CORS_ALLOW_ORIGINS: str = Field(
        description="",
        validation_alias=AliasChoices("WEB_API_CORS_ALLOW_ORIGINS"),
        default="*",
    )

    @computed_field
    def WEB_API_CORS_ALLOW_ORIGINS(self) -> list[str]:
        return self.inner_WEB_API_CORS_ALLOW_ORIGINS.split(",")

    HTTP_REQUEST_MAX_CONNECT_TIMEOUT: int = Field(
        ge=1,
        description="Maximum connection timeout in seconds for HTTP requests",
        default=10,
    )

    HTTP_REQUEST_MAX_READ_TIMEOUT: int = Field(
        ge=1,
        description="Maximum read timeout in seconds for HTTP requests",
        default=600,
    )

    HTTP_REQUEST_MAX_WRITE_TIMEOUT: int = Field(
        ge=1,
        description="Maximum write timeout in seconds for HTTP requests",
        default=600,
    )

    HTTP_REQUEST_NODE_MAX_BINARY_SIZE: PositiveInt = Field(
        description="Maximum allowed size in bytes for binary data in HTTP requests",
        default=10 * 1024 * 1024,
    )

    HTTP_REQUEST_NODE_MAX_TEXT_SIZE: PositiveInt = Field(
        description="Maximum allowed size in bytes for text data in HTTP requests",
        default=1 * 1024 * 1024,
    )

    HTTP_REQUEST_NODE_SSL_VERIFY: bool = Field(
        description="Enable or disable SSL verification for HTTP requests",
        default=True,
    )

    SSRF_DEFAULT_MAX_RETRIES: PositiveInt = Field(
        description="Maximum number of retries for network requests (SSRF)",
        default=3,
    )

    SSRF_PROXY_ALL_URL: str | None = Field(
        description="Proxy URL for HTTP or HTTPS requests to prevent Server-Side Request Forgery (SSRF)",
        default=None,
    )

    SSRF_PROXY_HTTP_URL: str | None = Field(
        description="Proxy URL for HTTP requests to prevent Server-Side Request Forgery (SSRF)",
        default=None,
    )

    SSRF_PROXY_HTTPS_URL: str | None = Field(
        description="Proxy URL for HTTPS requests to prevent Server-Side Request Forgery (SSRF)",
        default=None,
    )

    SSRF_DEFAULT_TIME_OUT: PositiveFloat = Field(
        description="The default timeout period used for network requests (SSRF)",
        default=5,
    )

    SSRF_DEFAULT_CONNECT_TIME_OUT: PositiveFloat = Field(
        description="The default connect timeout period used for network requests (SSRF)",
        default=5,
    )

    SSRF_DEFAULT_READ_TIME_OUT: PositiveFloat = Field(
        description="The default read timeout period used for network requests (SSRF)",
        default=5,
    )

    SSRF_DEFAULT_WRITE_TIME_OUT: PositiveFloat = Field(
        description="The default write timeout period used for network requests (SSRF)",
        default=5,
    )

    SSRF_POOL_MAX_CONNECTIONS: PositiveInt = Field(
        description="Maximum number of concurrent connections for the SSRF HTTP client",
        default=100,
    )

    SSRF_POOL_MAX_KEEPALIVE_CONNECTIONS: PositiveInt = Field(
        description="Maximum number of persistent keep-alive connections for the SSRF HTTP client",
        default=20,
    )

    SSRF_POOL_KEEPALIVE_EXPIRY: PositiveFloat | None = Field(
        description="Keep-alive expiry in seconds for idle SSRF connections (set to None to disable)",
        default=5.0,
    )

    RESPECT_XFORWARD_HEADERS_ENABLED: bool = Field(
        description="Enable handling of X-Forwarded-For, X-Forwarded-Proto, and X-Forwarded-Port headers"
        " when the app is behind a single trusted reverse proxy.",
        default=False,
    )


class ExtensionConfig(BaseSettings):
    """
    Configuration for code-based extensions
    """

    inner_POSITION_TOOL_PINS: str = Field(
        description="Comma-separated list of extension names to pin at the top of the list",
        validation_alias=AliasChoices("POSITION_TOOL_PINS"),
        default="",
    )

    @computed_field
    @property
    def POSITION_TOOL_PINS_LIST(self) -> list[str]:
        """
        Parse and return the pin list as a list of extension names.
        """
        if not self.inner_POSITION_TOOL_PINS:
            return []
        return [pin.strip() for pin in self.inner_POSITION_TOOL_PINS.split(",") if pin.strip()]


class ModerationConfig(BaseSettings):
    """
    Configuration for content moderation
    """

    MODERATION_BUFFER_SIZE: PositiveInt = Field(
        description="Size of the buffer for content moderation processing",
        default=300,
    )


class FeatureConfig(
    SecurityConfig,
    FileAccessConfig,
    FileUploadConfig,
    RagEtlConfig,
    IndexingConfig,
    CeleryBeatConfig,
    LoggingConfig,
    MailConfig,
    EndpointConfig,
    BillingConfig,
    AuthConfig,
    WorkspaceConfig,
    LoginConfig,
    AccountConfig,
    HttpConfig,
    ExtensionConfig,
    ModerationConfig,
):
    pass
