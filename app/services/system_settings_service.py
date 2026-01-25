from sqlalchemy import select

from models.system_setting import SystemSetting
from schemas.settings import (
    AuthSettings,
    AuthSettingsUpdate,
    BrandingSettings,
    BrandingSettingsUpdate,
    GeneralSettingsConfig,
    GeneralSettingsConfigUpdate,
    GeneralSettingsTarget,
    OAuthProviderSettings,
    OAuthProviderSettingsUpdate,
    WechatOAuthSettings,
    WechatOAuthSettingsUpdate,
)
from services.base_service import BaseService


class SystemSettingsService(BaseService):
    """系统配置服务"""

    # 品牌配置默认值
    BRANDING_DEFAULTS = {
        "enabled": "false",
        "application_title": "FastAPI Template",
        "login_page_logo": "",
        "workspace_logo": "",
        "favicon": "",
        "theme_color": "#1570EF",
    }

    # OAuth 默认值
    OAUTH_DEFAULTS = {
        "enabled": "false",
        "client_id": "",
        "client_secret": "",
    }

    # 微信默认值
    WECHAT_DEFAULTS = {
        "enabled": "false",
        "app_id": "",
        "app_secret": "",
    }

    async def get_setting(self, key: str) -> str | None:
        """获取单个配置值"""
        result = await self.db.execute(select(SystemSetting).where(SystemSetting.key == key))
        setting = result.scalar_one_or_none()
        return setting.value if setting else None

    async def set_setting(self, key: str, value: str | None) -> None:
        """设置单个配置值"""
        result = await self.db.execute(select(SystemSetting).where(SystemSetting.key == key))
        setting = result.scalar_one_or_none()

        if setting:
            setting.value = value
        else:
            setting = SystemSetting(key=key, value=value)
            self.db.add(setting)

        await self.db.commit()

    async def _get_settings_by_prefix(self, prefix: str) -> dict[str, str]:
        """获取指定前缀的所有配置"""
        result = await self.db.execute(
            select(SystemSetting).where(SystemSetting.key.like(f"{prefix}%"))
        )
        return {s.key.replace(prefix, ""): s.value for s in result.scalars().all()}

    async def _get_branding_settings(self, target: GeneralSettingsTarget) -> BrandingSettings:
        """获取品牌配置"""
        prefix = f"general.{target.value}.branding."
        settings = await self._get_settings_by_prefix(prefix)

        # 兼容旧配置
        if not settings:
            old_prefix = f"branding.{target.value}."
            settings = await self._get_settings_by_prefix(old_prefix)

        def get_value(field: str) -> str:
            return settings.get(field) or self.BRANDING_DEFAULTS.get(field, "")

        return BrandingSettings(
            enabled=get_value("enabled").lower() == "true",
            application_title=get_value("application_title"),
            login_page_logo=get_value("login_page_logo"),
            workspace_logo=get_value("workspace_logo"),
            favicon=get_value("favicon"),
            theme_color=get_value("theme_color"),
        )

    async def _get_oauth_settings(
        self, target: GeneralSettingsTarget, provider: str
    ) -> OAuthProviderSettings:
        """获取 OAuth 提供商配置"""
        prefix = f"general.{target.value}.auth.{provider}."
        settings = await self._get_settings_by_prefix(prefix)

        def get_value(field: str) -> str:
            return settings.get(field) or self.OAUTH_DEFAULTS.get(field, "")

        return OAuthProviderSettings(
            enabled=get_value("enabled").lower() == "true",
            client_id=get_value("client_id"),
            client_secret=get_value("client_secret"),
        )

    async def _get_wechat_settings(self, target: GeneralSettingsTarget) -> WechatOAuthSettings:
        """获取微信登录配置"""
        prefix = f"general.{target.value}.auth.wechat."
        settings = await self._get_settings_by_prefix(prefix)

        def get_value(field: str) -> str:
            return settings.get(field) or self.WECHAT_DEFAULTS.get(field, "")

        return WechatOAuthSettings(
            enabled=get_value("enabled").lower() == "true",
            app_id=get_value("app_id"),
            app_secret=get_value("app_secret"),
        )

    async def _get_auth_settings(self, target: GeneralSettingsTarget) -> AuthSettings:
        """获取认证配置"""
        prefix = f"general.{target.value}.auth."
        settings = await self._get_settings_by_prefix(prefix)

        github = await self._get_oauth_settings(target, "github")
        google = await self._get_oauth_settings(target, "google")
        wechat = await self._get_wechat_settings(target)

        return AuthSettings(
            enable_login=settings.get("enable_login", "true").lower() == "true",
            enable_register=settings.get("enable_register", "true").lower() == "true",
            enable_email_code_login=settings.get("enable_email_code_login", "true").lower()
            == "true",
            github=github,
            google=google,
            wechat=wechat,
        )

    async def get_general_settings(
        self, target: GeneralSettingsTarget = GeneralSettingsTarget.WEB
    ) -> GeneralSettingsConfig:
        """获取基础配置"""
        branding = await self._get_branding_settings(target)
        auth = await self._get_auth_settings(target)

        return GeneralSettingsConfig(branding=branding, auth=auth)

    async def _update_settings_from_dict(
        self, prefix: str, updates: dict, exclude_keys: set | None = None
    ) -> None:
        """从字典更新配置"""
        exclude_keys = exclude_keys or set()
        for field, value in updates.items():
            if field in exclude_keys:
                continue
            key = f"{prefix}{field}"
            if isinstance(value, bool):
                value = "true" if value else "false"
            elif value is None:
                value = ""
            else:
                value = str(value)
            await self._upsert_setting(key, value)

    async def _update_branding_settings(
        self, config: BrandingSettingsUpdate, target: GeneralSettingsTarget
    ) -> None:
        """更新品牌配置"""
        prefix = f"general.{target.value}.branding."
        updates = config.model_dump(exclude_unset=True)
        await self._update_settings_from_dict(prefix, updates)

    async def _update_oauth_settings(
        self, config: OAuthProviderSettingsUpdate, target: GeneralSettingsTarget, provider: str
    ) -> None:
        """更新 OAuth 提供商配置"""
        prefix = f"general.{target.value}.auth.{provider}."
        updates = config.model_dump(exclude_unset=True)
        await self._update_settings_from_dict(prefix, updates)

    async def _update_wechat_settings(
        self,
        config: WechatOAuthSettingsUpdate,
        target: GeneralSettingsTarget,
    ) -> None:
        """更新微信登录配置"""
        prefix = f"general.{target.value}.auth.wechat."
        updates = config.model_dump(exclude_unset=True)
        await self._update_settings_from_dict(prefix, updates)

    async def _update_auth_settings(
        self, config: AuthSettingsUpdate, target: GeneralSettingsTarget
    ) -> None:
        """更新认证配置"""
        prefix = f"general.{target.value}.auth."
        updates = config.model_dump(exclude_unset=True)

        # 更新基础字段（排除嵌套对象）
        await self._update_settings_from_dict(
            prefix, updates, exclude_keys={"github", "google", "wechat"}
        )

        # 更新 OAuth 配置
        if config.github:
            await self._update_oauth_settings(config.github, target, "github")
        if config.google:
            await self._update_oauth_settings(config.google, target, "google")
        if config.wechat:
            await self._update_wechat_settings(config.wechat, target)

    async def update_general_settings(
        self,
        config: GeneralSettingsConfigUpdate,
        target: GeneralSettingsTarget = GeneralSettingsTarget.WEB,
    ) -> GeneralSettingsConfig:
        """更新基础配置"""
        if config.branding:
            await self._update_branding_settings(config.branding, target)

        if config.auth and target == GeneralSettingsTarget.WEB:
            await self._update_auth_settings(config.auth, target)

        await self.db.commit()
        return await self.get_general_settings(target)

    # 兼容旧方法
    async def get_branding_config(
        self, target: GeneralSettingsTarget = GeneralSettingsTarget.WEB
    ) -> BrandingSettings:
        """获取品牌配置（兼容旧方法）"""
        return await self._get_branding_settings(target)

    async def _upsert_setting(self, key: str, value: str) -> None:
        """更新或插入配置（不提交事务）"""
        result = await self.db.execute(select(SystemSetting).where(SystemSetting.key == key))
        setting = result.scalar_one_or_none()

        if setting:
            setting.value = value
        else:
            setting = SystemSetting(key=key, value=value)
            self.db.add(setting)
