"""支付配置"""

from pydantic import Field
from pydantic_settings import BaseSettings


class PaymentConfig(BaseSettings):
    """支付相关配置"""

    # 微信支付配置
    WECHAT_PAY_APP_ID: str = Field(default="", description="微信支付 APP ID")
    WECHAT_PAY_MCH_ID: str = Field(default="", description="微信支付商户号")
    WECHAT_PAY_API_KEY: str = Field(default="", description="微信支付 API 密钥（V3）")
    WECHAT_PAY_SERIAL_NO: str = Field(default="", description="微信支付商户证书序列号")
    WECHAT_PAY_PRIVATE_KEY_PATH: str = Field(default="", description="微信支付商户私钥文件路径")
    WECHAT_PAY_NOTIFY_URL: str = Field(default="", description="微信支付回调通知地址")

    # 支付宝配置
    ALIPAY_APP_ID: str = Field(default="", description="支付宝应用 APP ID")
    ALIPAY_PRIVATE_KEY_PATH: str = Field(default="", description="支付宝应用私钥文件路径")
    ALIPAY_PUBLIC_KEY_PATH: str = Field(default="", description="支付宝公钥文件路径")
    ALIPAY_NOTIFY_URL: str = Field(default="", description="支付宝回调通知地址")
    ALIPAY_SANDBOX: bool = Field(default=False, description="是否使用支付宝沙箱环境")

    # 订单配置
    RECHARGE_ORDER_EXPIRE_MINUTES: int = Field(default=15, description="充值订单过期时间（分钟）")

    # 订阅计划价格配置（可被数据库配置覆盖）
    PLAN_PRO_PRICE: float = Field(default=99.0, description="Pro 计划月费（元）")
    PLAN_MAX_PRICE: float = Field(default=299.0, description="Max 计划月费（元）")

    @property
    def wechat_pay_enabled(self) -> bool:
        """判断微信支付是否配置完整"""
        return bool(self.WECHAT_PAY_APP_ID and self.WECHAT_PAY_MCH_ID and self.WECHAT_PAY_API_KEY)

    @property
    def alipay_enabled(self) -> bool:
        """判断支付宝支付是否配置完整"""
        return bool(
            self.ALIPAY_APP_ID and self.ALIPAY_PRIVATE_KEY_PATH and self.ALIPAY_PUBLIC_KEY_PATH
        )
