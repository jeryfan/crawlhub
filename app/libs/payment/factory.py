"""支付服务工厂"""

from models.billing import PaymentMethod

from .alipay import AlipayProvider
from .base import PaymentProvider
from .wechat import WechatPayProvider


_providers: dict[str, PaymentProvider] = {}


def get_payment_provider(method: str | PaymentMethod) -> PaymentProvider:
    """
    获取支付服务提供者

    Args:
        method: 支付方式 (wechat/alipay)

    Returns:
        PaymentProvider: 支付服务提供者实例
    """
    method_str = method.value if isinstance(method, PaymentMethod) else method

    if method_str not in _providers:
        if method_str == PaymentMethod.WECHAT:
            _providers[method_str] = WechatPayProvider()
        elif method_str == PaymentMethod.ALIPAY:
            _providers[method_str] = AlipayProvider()
        else:
            raise ValueError(f"不支持的支付方式: {method_str}")

    return _providers[method_str]
