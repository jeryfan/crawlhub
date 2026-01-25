from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class GeneralSettingsTarget(str, Enum):
    """基础配置目标"""

    WEB = "web"
    ADMIN = "admin"


# 品牌配置
class BrandingSettings(BaseModel):
    """品牌配置"""

    enabled: bool = False
    application_title: str = ""
    login_page_logo: str = ""
    workspace_logo: str = ""
    favicon: str = ""
    theme_color: str = "#1570EF"

    model_config = ConfigDict(from_attributes=True)


class BrandingSettingsUpdate(BaseModel):
    """品牌配置更新"""

    enabled: bool | None = None
    application_title: str | None = Field(None, max_length=100)
    login_page_logo: str | None = None
    workspace_logo: str | None = None
    favicon: str | None = None
    theme_color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


# OAuth 提供商配置
class OAuthProviderSettings(BaseModel):
    """OAuth 提供商配置"""

    enabled: bool = False
    client_id: str = ""
    client_secret: str = ""

    model_config = ConfigDict(from_attributes=True)


class OAuthProviderSettingsUpdate(BaseModel):
    """OAuth 提供商配置更新"""

    enabled: bool | None = None
    client_id: str | None = Field(None, max_length=200)
    client_secret: str | None = Field(None, max_length=200)


# 微信登录配置
class WechatOAuthSettings(BaseModel):
    """微信登录配置"""

    enabled: bool = False
    app_id: str = ""
    app_secret: str = ""

    model_config = ConfigDict(from_attributes=True)


class WechatOAuthSettingsUpdate(BaseModel):
    """微信登录配置更新"""

    enabled: bool | None = None
    app_id: str | None = Field(None, max_length=200)
    app_secret: str | None = Field(None, max_length=200)


# 认证配置（仅 web 端）
class AuthSettings(BaseModel):
    """认证配置"""

    enable_login: bool = True
    enable_register: bool = True
    enable_email_code_login: bool = True
    github: OAuthProviderSettings = OAuthProviderSettings()
    google: OAuthProviderSettings = OAuthProviderSettings()
    wechat: WechatOAuthSettings = WechatOAuthSettings()

    model_config = ConfigDict(from_attributes=True)


class AuthSettingsUpdate(BaseModel):
    """认证配置更新"""

    enable_login: bool | None = None
    enable_register: bool | None = None
    enable_email_code_login: bool | None = None
    github: OAuthProviderSettingsUpdate | None = None
    google: OAuthProviderSettingsUpdate | None = None
    wechat: WechatOAuthSettingsUpdate | None = None


# 基础配置（完整）
class GeneralSettingsConfig(BaseModel):
    """基础配置响应"""

    branding: BrandingSettings = BrandingSettings()
    auth: AuthSettings = AuthSettings()

    model_config = ConfigDict(from_attributes=True)


class GeneralSettingsConfigUpdate(BaseModel):
    """基础配置更新请求"""

    branding: BrandingSettingsUpdate | None = None
    auth: AuthSettingsUpdate | None = None


# 兼容旧类型
BrandingTarget = GeneralSettingsTarget
BrandingConfig = BrandingSettings
BrandingConfigUpdate = BrandingSettingsUpdate
