"""支付宝支付服务"""

import asyncio
import logging
from decimal import Decimal

from alipay import AliPay
from alipay.utils import AliPayConfig

from configs import app_config

from .base import CreateOrderResult, PaymentProvider, PaymentResult

logger = logging.getLogger(__name__)


class AlipayProvider(PaymentProvider):
    """支付宝支付服务 (基于 python-alipay-sdk)"""

    def __init__(self):
        self.app_id = app_config.ALIPAY_APP_ID
        self.sandbox = app_config.ALIPAY_SANDBOX

        # Key paths
        self.private_key_path = app_config.ALIPAY_PRIVATE_KEY_PATH
        self.public_key_path = app_config.ALIPAY_PUBLIC_KEY_PATH

        # Cache
        self._private_key: str | None = None
        self._public_key: str | None = None
        self._client: AliPay | None = None

    @property
    def private_key(self) -> str:
        """获取应用私钥"""
        if self._private_key is not None:
            return self._private_key

        if self.private_key_path:
            try:
                with open(self.private_key_path, "r") as f:
                    self._private_key = f.read().strip()
            except Exception as e:
                logger.error(f"读取支付宝私钥文件失败: {e}")
                self._private_key = ""
        else:
            self._private_key = ""

        return self._private_key

    @property
    def alipay_public_key(self) -> str:
        """获取支付宝公钥"""
        if self._public_key is not None:
            return self._public_key

        if self.public_key_path:
            try:
                with open(self.public_key_path, "r") as f:
                    self._public_key = f.read().strip()
            except Exception as e:
                logger.error(f"读取支付宝公钥文件失败: {e}")
                self._public_key = ""
        else:
            self._public_key = ""

        return self._public_key

    @property
    def client(self) -> AliPay:
        """获取 Alipay 客户端实例"""
        if self._client is None:
            # 确保证书内容存在
            if not self.private_key or not self.alipay_public_key:
                raise ValueError("支付宝密钥配置不完整")
            self._client = AliPay(
                appid=self.app_id,
                app_notify_url=app_config.ALIPAY_NOTIFY_URL,
                app_private_key_string=self.private_key,
                alipay_public_key_string=self.alipay_public_key,
                sign_type="RSA2",
                debug=self.sandbox,
                verbose=False,
                config=AliPayConfig(timeout=30),
            )
        return self._client

    async def create_native_order(
        self,
        out_trade_no: str,
        amount: Decimal,
        description: str,
        notify_url: str,
    ) -> CreateOrderResult:
        """创建支付宝当面付订单（扫码支付）"""
        try:
            logger.info(
                f"创建支付宝订单: out_trade_no={out_trade_no}, amount={amount}, "
                f"sandbox={self.sandbox}, app_id={self.app_id}"
            )

            # 使用 run_in_executor 执行同步 SDK 方法
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.api_alipay_trade_precreate(
                    out_trade_no=out_trade_no,
                    total_amount=str(amount),
                    subject=description,
                    notify_url=notify_url,
                ),
            )

            logger.info(f"支付宝返回结果: {result}")

            # 检查结果
            # python-alipay-sdk 如果请求失败通常会抛出异常，或者返回包含 code 的字典
            code = result.get("code")
            if code == "10000":
                return CreateOrderResult(
                    success=True,
                    out_trade_no=out_trade_no,
                    qr_code_url=result.get("qr_code"),
                )
            else:
                msg = result.get("msg", "Unknown Error")
                sub_msg = result.get("sub_msg", "")
                logger.error(f"支付宝创建订单失败: code={code}, msg={msg}, sub_msg={sub_msg}")
                return CreateOrderResult(
                    success=False,
                    out_trade_no=out_trade_no,
                    error_msg=f"{msg}: {sub_msg}",
                )

        except Exception as e:
            logger.exception(f"支付宝创建订单异常: {e}")
            return CreateOrderResult(
                success=False,
                out_trade_no=out_trade_no,
                error_msg=str(e),
            )

    async def verify_callback(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> PaymentResult:
        """验证支付宝回调"""
        try:
            from urllib.parse import parse_qs

            # 解析表单数据
            data = {k: v[0] for k, v in parse_qs(body.decode()).items()}

            # 获取并移除签名
            signature = data.pop("sign", None)

            if not signature:
                return PaymentResult(success=False, error_msg="缺少签名参数")

            # 验证签名 (run_in_executor)
            loop = asyncio.get_running_loop()
            success = await loop.run_in_executor(None, lambda: self.client.verify(data, signature))

            if not success:
                return PaymentResult(success=False, error_msg="签名验证失败")

            # 检查交易状态
            trade_status = data.get("trade_status")
            if trade_status not in ("TRADE_SUCCESS", "TRADE_FINISHED"):
                return PaymentResult(
                    success=False,
                    error_msg=f"交易状态异常: {trade_status}",
                )

            return PaymentResult(
                success=True,
                out_trade_no=data.get("out_trade_no"),
                trade_no=data.get("trade_no"),
                amount=Decimal(data.get("total_amount", "0")),
            )

        except Exception as e:
            logger.exception(f"支付宝回调验证异常: {e}")
            return PaymentResult(success=False, error_msg=str(e))

    async def query_order(self, out_trade_no: str) -> PaymentResult:
        """查询支付宝订单"""
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.api_alipay_trade_query(out_trade_no=out_trade_no),
            )

            code = result.get("code")
            if code == "10000":
                trade_status = result.get("trade_status")
                if trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED"):
                    return PaymentResult(
                        success=True,
                        out_trade_no=out_trade_no,
                        trade_no=result.get("trade_no"),
                        amount=Decimal(result.get("total_amount", "0")),
                    )
                else:
                    return PaymentResult(
                        success=False,
                        out_trade_no=out_trade_no,
                        error_msg=f"交易状态: {trade_status}",
                    )
            else:
                return PaymentResult(
                    success=False,
                    out_trade_no=out_trade_no,
                    error_msg=result.get("sub_msg", "查询失败"),
                )

        except Exception as e:
            logger.exception(f"支付宝查询订单异常: {e}")
            return PaymentResult(
                success=False,
                out_trade_no=out_trade_no,
                error_msg=str(e),
            )

    def get_callback_response(self, success: bool) -> str:
        """生成支付宝回调响应"""
        return "success" if success else "fail"
