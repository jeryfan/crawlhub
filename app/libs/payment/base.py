"""支付服务基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass
class CreateOrderResult:
    """创建支付订单结果"""

    success: bool
    out_trade_no: str  # 商户订单号
    qr_code_url: str | None = None  # 支付二维码链接
    prepay_id: str | None = None  # 预支付ID
    error_msg: str | None = None


@dataclass
class PaymentResult:
    """支付回调验证结果"""

    success: bool
    out_trade_no: str | None = None  # 商户订单号
    trade_no: str | None = None  # 平台交易号
    amount: Decimal | None = None  # 支付金额
    error_msg: str | None = None


class PaymentProvider(ABC):
    """支付服务提供者基类"""

    @abstractmethod
    async def create_native_order(
        self,
        out_trade_no: str,
        amount: Decimal,
        description: str,
        notify_url: str,
    ) -> CreateOrderResult:
        """
        创建 Native 支付订单（扫码支付）

        Args:
            out_trade_no: 商户订单号
            amount: 支付金额（元）
            description: 订单描述
            notify_url: 支付回调地址

        Returns:
            CreateOrderResult: 包含二维码链接的创建结果
        """
        pass

    @abstractmethod
    async def verify_callback(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> PaymentResult:
        """
        验证支付回调

        Args:
            headers: 请求头
            body: 请求体原始数据

        Returns:
            PaymentResult: 验证结果
        """
        pass

    @abstractmethod
    async def query_order(self, out_trade_no: str) -> PaymentResult:
        """
        查询订单状态

        Args:
            out_trade_no: 商户订单号

        Returns:
            PaymentResult: 查询结果
        """
        pass

    @abstractmethod
    def get_callback_response(self, success: bool) -> Any:
        """
        生成回调响应

        Args:
            success: 是否处理成功

        Returns:
            响应内容（不同支付平台格式不同）
        """
        pass
