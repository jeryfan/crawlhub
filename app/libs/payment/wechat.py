"""微信支付服务"""

import json
import logging
import time
import uuid
from base64 import b64decode, b64encode
from datetime import datetime
from decimal import Decimal

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from configs import app_config

from .base import CreateOrderResult, PaymentProvider, PaymentResult

logger = logging.getLogger(__name__)


class WechatPayProvider(PaymentProvider):
    """微信支付服务"""

    API_BASE_URL = "https://api.mch.weixin.qq.com"

    def __init__(self):
        self.app_id = app_config.WECHAT_PAY_APP_ID
        self.mch_id = app_config.WECHAT_PAY_MCH_ID
        self.api_key = app_config.WECHAT_PAY_API_KEY
        self.serial_no = app_config.WECHAT_PAY_SERIAL_NO
        self.private_key_path = app_config.WECHAT_PAY_PRIVATE_KEY_PATH
        self._private_key: str | None = None

    @property
    def private_key(self) -> str:
        """加载私钥"""
        if self._private_key is None:
            if self.private_key_path:
                with open(self.private_key_path, "r") as f:
                    self._private_key = f.read()
            else:
                self._private_key = ""
        return self._private_key

    def _generate_nonce(self) -> str:
        """生成随机字符串"""
        return uuid.uuid4().hex

    def _generate_timestamp(self) -> str:
        """生成时间戳"""
        return str(int(time.time()))

    def _sign(self, message: str) -> str:
        """使用私钥签名"""
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding

        private_key = serialization.load_pem_private_key(self.private_key.encode(), password=None)
        signature = private_key.sign(
            message.encode(),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return b64encode(signature).decode()

    def _build_auth_header(self, method: str, url: str, body: str = "") -> str:
        """构建认证头"""
        timestamp = self._generate_timestamp()
        nonce = self._generate_nonce()

        # 构建签名串
        sign_str = f"{method}\n{url}\n{timestamp}\n{nonce}\n{body}\n"
        signature = self._sign(sign_str)

        return (
            f"WECHATPAY2-SHA256-RSA2048 "
            f'mchid="{self.mch_id}",'
            f'nonce_str="{nonce}",'
            f'signature="{signature}",'
            f'timestamp="{timestamp}",'
            f'serial_no="{self.serial_no}"'
        )

    def _decrypt_callback(self, resource: dict) -> dict:
        """解密回调数据"""
        ciphertext = b64decode(resource["ciphertext"])
        nonce = resource["nonce"].encode()
        associated_data = resource.get("associated_data", "").encode()

        aesgcm = AESGCM(self.api_key.encode())
        plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data)
        return json.loads(plaintext.decode())

    async def create_native_order(
        self,
        out_trade_no: str,
        amount: Decimal,
        description: str,
        notify_url: str,
    ) -> CreateOrderResult:
        """创建微信 Native 支付订单"""
        url_path = "/v3/pay/transactions/native"
        url = f"{self.API_BASE_URL}{url_path}"

        # 金额转换为分
        total_fee = int(amount * 100)

        body = {
            "appid": self.app_id,
            "mchid": self.mch_id,
            "description": description,
            "out_trade_no": out_trade_no,
            "notify_url": notify_url,
            "amount": {
                "total": total_fee,
                "currency": "CNY",
            },
        }

        body_str = json.dumps(body, ensure_ascii=False)
        auth_header = self._build_auth_header("POST", url_path, body_str)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    content=body_str,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": auth_header,
                    },
                    timeout=30,
                )

                if response.status_code == 200:
                    data = response.json()
                    return CreateOrderResult(
                        success=True,
                        out_trade_no=out_trade_no,
                        qr_code_url=data.get("code_url"),
                    )
                else:
                    error_data = response.json()
                    logger.error(f"微信支付创建订单失败: {error_data}")
                    return CreateOrderResult(
                        success=False,
                        out_trade_no=out_trade_no,
                        error_msg=error_data.get("message", "创建订单失败"),
                    )
        except Exception as e:
            logger.error(f"微信支付创建订单异常: {e}")
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
        """验证微信支付回调"""
        try:
            # TODO: 验证签名（需要获取微信平台证书）
            # 这里简化处理，实际应验证签名

            data = json.loads(body.decode())
            if data.get("event_type") != "TRANSACTION.SUCCESS":
                return PaymentResult(
                    success=False,
                    error_msg=f"非支付成功事件: {data.get('event_type')}",
                )

            # 解密回调数据
            resource = data.get("resource", {})
            decrypted = self._decrypt_callback(resource)

            # 检查交易状态
            if decrypted.get("trade_state") != "SUCCESS":
                return PaymentResult(
                    success=False,
                    error_msg=f"交易状态异常: {decrypted.get('trade_state')}",
                )

            # 金额转换（分转元）
            amount = Decimal(decrypted["amount"]["total"]) / 100

            return PaymentResult(
                success=True,
                out_trade_no=decrypted["out_trade_no"],
                trade_no=decrypted["transaction_id"],
                amount=amount,
            )
        except Exception as e:
            logger.error(f"微信支付回调验证异常: {e}")
            return PaymentResult(
                success=False,
                error_msg=str(e),
            )

    async def query_order(self, out_trade_no: str) -> PaymentResult:
        """查询微信支付订单"""
        url_path = f"/v3/pay/transactions/out-trade-no/{out_trade_no}?mchid={self.mch_id}"
        url = f"{self.API_BASE_URL}{url_path}"

        auth_header = self._build_auth_header("GET", url_path)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={"Authorization": auth_header},
                    timeout=30,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("trade_state") == "SUCCESS":
                        amount = Decimal(data["amount"]["total"]) / 100
                        return PaymentResult(
                            success=True,
                            out_trade_no=out_trade_no,
                            trade_no=data.get("transaction_id"),
                            amount=amount,
                        )
                    else:
                        return PaymentResult(
                            success=False,
                            out_trade_no=out_trade_no,
                            error_msg=f"交易状态: {data.get('trade_state')}",
                        )
                else:
                    error_data = response.json()
                    return PaymentResult(
                        success=False,
                        out_trade_no=out_trade_no,
                        error_msg=error_data.get("message", "查询失败"),
                    )
        except Exception as e:
            logger.error(f"微信支付查询订单异常: {e}")
            return PaymentResult(
                success=False,
                out_trade_no=out_trade_no,
                error_msg=str(e),
            )

    def get_callback_response(self, success: bool) -> dict:
        """生成微信支付回调响应"""
        if success:
            return {"code": "SUCCESS", "message": "成功"}
        else:
            return {"code": "FAIL", "message": "失败"}
