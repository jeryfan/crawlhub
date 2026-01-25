from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from configs import app_config
from enums.cloud_plan import CloudPlan
from models.account import TenantAccountJoin
from models.billing import SubscriptionPlan

# from services.billing_service import BillingService
# from services.enterprise.enterprise_service import EnterpriseService


class SubscriptionModel(BaseModel):
    plan: str = CloudPlan.SANDBOX
    interval: str = ""


class BillingModel(BaseModel):
    enabled: bool = True  # 默认开启 billing
    subscription: SubscriptionModel = SubscriptionModel()


class LimitationModel(BaseModel):
    size: int = 0
    limit: int = 0


class LicenseLimitationModel(BaseModel):
    """
    - enabled: whether this limit is enforced
    - size: current usage count
    - limit: maximum allowed count; 0 means unlimited
    """

    enabled: bool = Field(False, description="Whether this limit is currently active")
    size: int = Field(0, description="Number of resources already consumed")
    limit: int = Field(0, description="Maximum number of resources allowed; 0 means no limit")

    def is_available(self, required: int = 1) -> bool:
        """
        Determine whether the requested amount can be allocated.

        Returns True if:
         - this limit is not active, or
         - the limit is zero (unlimited), or
         - there is enough remaining quota.
        """
        if not self.enabled or self.limit == 0:
            return True

        return (self.limit - self.size) >= required


class Quota(BaseModel):
    usage: int = 0
    limit: int = 0
    reset_date: int = -1


class LicenseStatus(StrEnum):
    NONE = "none"
    INACTIVE = "inactive"
    ACTIVE = "active"
    EXPIRING = "expiring"
    EXPIRED = "expired"
    LOST = "lost"


class LicenseModel(BaseModel):
    status: LicenseStatus = LicenseStatus.NONE
    expired_at: str = ""
    workspaces: LicenseLimitationModel = LicenseLimitationModel(enabled=False, size=0, limit=0)


class BrandingModel(BaseModel):
    enabled: bool = False
    application_title: str = ""
    login_page_logo: str = ""
    workspace_logo: str = ""
    favicon: str = ""


class OAuthProviderModel(BaseModel):
    """OAuth 提供商配置（返回给前端，不包含 secret）"""

    enabled: bool = False
    client_id: str = ""


class WechatOAuthModel(BaseModel):
    """微信登录配置（返回给前端，不包含 secret）"""

    enabled: bool = False
    app_id: str = ""


class OAuthModel(BaseModel):
    """OAuth 配置"""

    github: OAuthProviderModel = OAuthProviderModel()
    google: OAuthProviderModel = OAuthProviderModel()
    wechat: WechatOAuthModel = WechatOAuthModel()


class WebAppAuthSSOModel(BaseModel):
    protocol: str = ""


class WebAppAuthModel(BaseModel):
    enabled: bool = True
    allow_sso: bool = False
    sso_config: WebAppAuthSSOModel = WebAppAuthSSOModel()
    allow_email_code_login: bool = False
    allow_email_password_login: bool = False


class FeatureModel(BaseModel):
    billing: BillingModel = BillingModel()
    members: LimitationModel = LimitationModel(size=0, limit=1)
    apps: LimitationModel = LimitationModel(size=0, limit=10)

    webapp_copyright_enabled: bool = False
    workspace_members: LicenseLimitationModel = LicenseLimitationModel(
        enabled=False, size=0, limit=0
    )
    is_allow_transfer_workspace: bool = True
    api_rate_limit: Quota = Quota(usage=0, limit=5000, reset_date=0)
    # pydantic configs
    model_config = ConfigDict(protected_namespaces=())


class SystemFeatureModel(BaseModel):
    sso_enforced_for_signin: bool = False
    sso_enforced_for_signin_protocol: str = ""
    enable_email_code_login: bool = False
    enable_email_password_login: bool = True
    enable_social_oauth_login: bool = False
    is_allow_register: bool = False
    is_allow_create_workspace: bool = False
    is_email_setup: bool = False
    license: LicenseModel = LicenseModel()
    branding: BrandingModel = BrandingModel()
    oauth: OAuthModel = OAuthModel()
    webapp_auth: WebAppAuthModel = WebAppAuthModel()
    enable_change_email: bool = True


class FeatureService:
    @classmethod
    def get_features(cls, tenant_id: str | None) -> FeatureModel:
        """获取特性配置（同步版本，仅用于向后兼容）"""
        features = FeatureModel()

        cls._fulfill_params_from_env(features)

        features.billing.enabled = True
        features.webapp_copyright_enabled = True

        return features

    @classmethod
    async def get_features_async(
        cls, db: AsyncSession, tenant_id: str | None, tenant_plan: str | None = None
    ) -> FeatureModel:
        """获取特性配置（异步版本，从数据库读取订阅计划配置）"""
        from models.account import Tenant

        features = FeatureModel()

        cls._fulfill_params_from_env(features)

        features.billing.enabled = True
        features.webapp_copyright_enabled = True

        if not tenant_id:
            return features

        # 获取租户信息
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            return features

        plan_id = tenant_plan or tenant.plan or "basic"

        # 设置订阅计划
        features.billing.subscription.plan = plan_id

        # 从数据库获取订阅计划配置
        plan = await db.get(SubscriptionPlan, plan_id)
        if plan:
            await cls._fulfill_params_from_plan(db, features, tenant, plan)
        else:
            # 如果计划不存在，使用默认配置
            await cls._fulfill_default_params(db, features, tenant)

        return features

    @classmethod
    async def _fulfill_params_from_plan(
        cls,
        db: AsyncSession,
        features: FeatureModel,
        tenant,
        plan: SubscriptionPlan,
    ):
        """从订阅计划填充参数"""
        # 获取租户成员数量
        member_count = (
            await db.scalar(select(func.count()).where(TenantAccountJoin.tenant_id == tenant.id))
            or 0
        )

        # 成员限制
        features.members.size = member_count
        features.members.limit = plan.team_members  # 0 表示无限

        # 应用限制
        features.apps.size = 0  # TODO: 从实际数据获取
        features.apps.limit = plan.apps_limit

        # API 速率限制
        features.api_rate_limit.limit = plan.api_rate_limit
        features.api_rate_limit.usage = 0  # TODO: 从实际使用数据获取

        # workspace_members 使用与 members 相同的数据
        features.workspace_members.enabled = True
        features.workspace_members.size = member_count
        features.workspace_members.limit = plan.team_members

    @classmethod
    async def _fulfill_default_params(
        cls,
        db: AsyncSession,
        features: FeatureModel,
        tenant,
    ):
        """使用默认参数（当计划不存在时）"""
        # 获取租户成员数量
        member_count = (
            await db.scalar(select(func.count()).where(TenantAccountJoin.tenant_id == tenant.id))
            or 0
        )

        # 使用默认值
        features.members.size = member_count
        features.members.limit = 1

        features.apps.limit = 10
        features.api_rate_limit.limit = 100

        features.workspace_members.enabled = True
        features.workspace_members.size = member_count
        features.workspace_members.limit = 1

    @classmethod
    def get_system_features(cls) -> SystemFeatureModel:
        """获取系统特性（同步版本，使用默认品牌配置）"""
        system_features = SystemFeatureModel()

        cls._fulfill_system_params_from_env(system_features)

        system_features.branding.enabled = True
        system_features.webapp_auth.enabled = True
        system_features.enable_change_email = False
        # cls._fulfill_params_from_enterprise(system_features)

        return system_features

    @classmethod
    async def get_system_features_async(cls, db: AsyncSession) -> SystemFeatureModel:
        """获取系统特性（异步版本，从数据库加载基础配置）

        OAuth 优先级逻辑：
        - 后台配置关闭 -> 不展示
        - 后台配置开启 -> 使用后台配置的 client_id
        - 后台未配置（enabled=False 且无 client_id）-> 使用环境变量
        """
        from schemas.settings import GeneralSettingsTarget
        from services.system_settings_service import SystemSettingsService

        system_features = SystemFeatureModel()

        cls._fulfill_system_params_from_env(system_features)

        # 从数据库加载 Web 端基础配置
        settings_service = SystemSettingsService(db)
        general_config = await settings_service.get_general_settings(GeneralSettingsTarget.WEB)

        # 品牌配置
        system_features.branding.enabled = general_config.branding.enabled
        system_features.branding.application_title = general_config.branding.application_title
        system_features.branding.login_page_logo = general_config.branding.login_page_logo
        system_features.branding.workspace_logo = general_config.branding.workspace_logo
        system_features.branding.favicon = general_config.branding.favicon

        # 认证配置
        system_features.is_allow_register = general_config.auth.enable_register

        # 验证码登录 - 后台配置优先
        system_features.enable_email_code_login = general_config.auth.enable_email_code_login

        # OAuth 配置 - 优先级：后台配置 > 环境变量
        # GitHub
        db_github = general_config.auth.github
        if db_github.client_id:
            # 后台有配置，以后台为准
            if db_github.enabled:
                system_features.oauth.github.enabled = True
                system_features.oauth.github.client_id = db_github.client_id
            # else: 后台关闭，不展示
        else:
            # 后台未配置，使用环境变量
            if app_config.GITHUB_CLIENT_ID and app_config.GITHUB_CLIENT_SECRET:
                system_features.oauth.github.enabled = True
                system_features.oauth.github.client_id = app_config.GITHUB_CLIENT_ID

        # Google
        db_google = general_config.auth.google
        if db_google.client_id:
            # 后台有配置，以后台为准
            if db_google.enabled:
                system_features.oauth.google.enabled = True
                system_features.oauth.google.client_id = db_google.client_id
            # else: 后台关闭，不展示
        else:
            # 后台未配置，使用环境变量
            if app_config.GOOGLE_CLIENT_ID and app_config.GOOGLE_CLIENT_SECRET:
                system_features.oauth.google.enabled = True
                system_features.oauth.google.client_id = app_config.GOOGLE_CLIENT_ID

        # 微信 - 优先级：后台配置 > 环境变量
        db_wechat = general_config.auth.wechat
        if db_wechat.app_id:
            # 后台有配置，以后台为准
            if db_wechat.enabled:
                system_features.oauth.wechat.enabled = True
                system_features.oauth.wechat.app_id = db_wechat.app_id
            # else: 后台关闭，不展示
        else:
            # 后台未配置，使用环境变量
            if app_config.WECHAT_APP_ID and app_config.WECHAT_APP_SECRET:
                system_features.oauth.wechat.enabled = True
                system_features.oauth.wechat.app_id = app_config.WECHAT_APP_ID

        # 更新 enable_social_oauth_login
        system_features.enable_social_oauth_login = (
            system_features.oauth.github.enabled
            or system_features.oauth.google.enabled
            or system_features.oauth.wechat.enabled
        )

        system_features.webapp_auth.enabled = True
        system_features.enable_change_email = False

        return system_features

    @classmethod
    def _fulfill_system_params_from_env(cls, system_features: SystemFeatureModel):
        system_features.enable_email_code_login = app_config.ENABLE_EMAIL_CODE_LOGIN
        system_features.enable_email_password_login = app_config.ENABLE_EMAIL_PASSWORD_LOGIN
        system_features.enable_social_oauth_login = app_config.ENABLE_SOCIAL_OAUTH_LOGIN
        system_features.is_allow_register = app_config.ALLOW_REGISTER
        system_features.is_allow_create_workspace = app_config.ALLOW_CREATE_WORKSPACE
        system_features.is_email_setup = (
            app_config.MAIL_TYPE is not None and app_config.MAIL_TYPE != ""
        )

    @classmethod
    def _fulfill_params_from_env(cls, features: FeatureModel):
        pass  # 当前无需从环境变量填充参数

    # @classmethod
    # def _fulfill_params_from_billing_api(cls, features: FeatureModel, tenant_id: str):
    #     billing_info = BillingService.get_info(tenant_id)

    #     features_usage_info = BillingService.get_tenant_feature_plan_usage_info(tenant_id)

    #     features.billing.enabled = billing_info["enabled"]
    #     features.billing.subscription.plan = billing_info["subscription"]["plan"]
    #     features.billing.subscription.interval = billing_info["subscription"]["interval"]
    #     features.education.activated = billing_info["subscription"].get("education", False)

    #     features.webapp_copyright_enabled = True

    #     if "api_rate_limit" in features_usage_info:
    #         features.api_rate_limit.usage = features_usage_info["api_rate_limit"]["usage"]
    #         features.api_rate_limit.limit = features_usage_info["api_rate_limit"]["limit"]
    #         features.api_rate_limit.reset_date = features_usage_info["api_rate_limit"].get("reset_date", -1)

    #     if "members" in billing_info:
    #         features.members.size = billing_info["members"]["size"]
    #         features.members.limit = billing_info["members"]["limit"]

    #     if "can_replace_logo" in billing_info:
    #         features.can_replace_logo = billing_info["can_replace_logo"]

    #     if "model_load_balancing_enabled" in billing_info:
    #         features.model_load_balancing_enabled = billing_info["model_load_balancing_enabled"]
    # @classmethod
    # def _fulfill_params_from_enterprise(cls, features: SystemFeatureModel):
    #     enterprise_info = EnterpriseService.get_info()

    #     if "SSOEnforcedForSignin" in enterprise_info:
    #         features.sso_enforced_for_signin = enterprise_info["SSOEnforcedForSignin"]

    #     if "SSOEnforcedForSigninProtocol" in enterprise_info:
    #         features.sso_enforced_for_signin_protocol = enterprise_info["SSOEnforcedForSigninProtocol"]

    #     if "EnableEmailCodeLogin" in enterprise_info:
    #         features.enable_email_code_login = enterprise_info["EnableEmailCodeLogin"]

    #     if "EnableEmailPasswordLogin" in enterprise_info:
    #         features.enable_email_password_login = enterprise_info["EnableEmailPasswordLogin"]

    #     if "IsAllowRegister" in enterprise_info:
    #         features.is_allow_register = enterprise_info["IsAllowRegister"]

    #     if "IsAllowCreateWorkspace" in enterprise_info:
    #         features.is_allow_create_workspace = enterprise_info["IsAllowCreateWorkspace"]

    #     if "Branding" in enterprise_info:
    #         features.branding.application_title = enterprise_info["Branding"].get("applicationTitle", "")
    #         features.branding.login_page_logo = enterprise_info["Branding"].get("loginPageLogo", "")
    #         features.branding.workspace_logo = enterprise_info["Branding"].get("workspaceLogo", "")
    #         features.branding.favicon = enterprise_info["Branding"].get("favicon", "")

    #     if "WebAppAuth" in enterprise_info:
    #         features.webapp_auth.allow_sso = enterprise_info["WebAppAuth"].get("allowSso", False)
    #         features.webapp_auth.allow_email_code_login = enterprise_info["WebAppAuth"].get(
    #             "allowEmailCodeLogin", False
    #         )
    #         features.webapp_auth.allow_email_password_login = enterprise_info["WebAppAuth"].get(
    #             "allowEmailPasswordLogin", False
    #         )
    #         features.webapp_auth.sso_config.protocol = enterprise_info.get("SSOEnforcedForWebProtocol", "")

    #     if "License" in enterprise_info:
    #         license_info = enterprise_info["License"]

    #         if "status" in license_info:
    #             features.license.status = LicenseStatus(license_info.get("status", LicenseStatus.INACTIVE))

    #         if "expiredAt" in license_info:
    #             features.license.expired_at = license_info["expiredAt"]

    #         if "workspaces" in license_info:
    #             features.license.workspaces.enabled = license_info["workspaces"]["enabled"]
    #             features.license.workspaces.limit = license_info["workspaces"]["limit"]
    #             features.license.workspaces.size = license_info["workspaces"]["used"]
