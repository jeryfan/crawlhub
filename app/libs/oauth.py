import urllib.parse
from dataclasses import dataclass

import httpx


@dataclass
class OAuthUserInfo:
    id: str
    name: str
    email: str


class OAuth:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self):
        raise NotImplementedError()

    def get_access_token(self, code: str):
        raise NotImplementedError()

    def get_raw_user_info(self, token: str):
        raise NotImplementedError()

    def get_user_info(self, token: str) -> OAuthUserInfo:
        raw_info = self.get_raw_user_info(token)
        return self._transform_user_info(raw_info)

    def _transform_user_info(self, raw_info: dict) -> OAuthUserInfo:
        raise NotImplementedError()


class GitHubOAuth(OAuth):
    _AUTH_URL = "https://github.com/login/oauth/authorize"
    _TOKEN_URL = "https://github.com/login/oauth/access_token"
    _USER_INFO_URL = "https://api.github.com/user"
    _EMAIL_INFO_URL = "https://api.github.com/user/emails"

    def get_authorization_url(self, invite_token: str | None = None):
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "user:email",  # Request only basic user information
        }
        if invite_token:
            params["state"] = invite_token
        return f"{self._AUTH_URL}?{urllib.parse.urlencode(params)}"

    def get_access_token(self, code: str):
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        headers = {"Accept": "application/json"}
        response = httpx.post(self._TOKEN_URL, data=data, headers=headers)

        response_json = response.json()
        access_token = response_json.get("access_token")

        if not access_token:
            raise ValueError(f"Error in GitHub OAuth: {response_json}")

        return access_token

    def get_raw_user_info(self, token: str):
        headers = {"Authorization": f"token {token}"}
        response = httpx.get(self._USER_INFO_URL, headers=headers)
        response.raise_for_status()
        user_info = response.json()

        email_response = httpx.get(self._EMAIL_INFO_URL, headers=headers)
        email_info = email_response.json()
        primary_email: dict = next((email for email in email_info if email["primary"] == True), {})

        return {**user_info, "email": primary_email.get("email", "")}

    def _transform_user_info(self, raw_info: dict) -> OAuthUserInfo:
        email = raw_info.get("email")
        if not email:
            email = f"{raw_info['id']}+{raw_info['login']}@users.noreply.github.com"
        return OAuthUserInfo(id=str(raw_info["id"]), name=raw_info["name"], email=email)


class GoogleOAuth(OAuth):
    _AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    _TOKEN_URL = "https://oauth2.googleapis.com/token"
    _USER_INFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

    def get_authorization_url(self, invite_token: str | None = None):
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": "openid email",
        }
        if invite_token:
            params["state"] = invite_token
        return f"{self._AUTH_URL}?{urllib.parse.urlencode(params)}"

    def get_access_token(self, code: str):
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        headers = {"Accept": "application/json"}
        response = httpx.post(self._TOKEN_URL, data=data, headers=headers)

        response_json = response.json()
        access_token = response_json.get("access_token")

        if not access_token:
            raise ValueError(f"Error in Google OAuth: {response_json}")

        return access_token

    def get_raw_user_info(self, token: str):
        headers = {"Authorization": f"Bearer {token}"}
        response = httpx.get(self._USER_INFO_URL, headers=headers)
        response.raise_for_status()
        return response.json()

    def _transform_user_info(self, raw_info: dict) -> OAuthUserInfo:
        return OAuthUserInfo(id=str(raw_info["sub"]), name="", email=raw_info["email"])


class WechatOAuth(OAuth):
    """微信开放平台 OAuth（网站应用扫码登录）

    文档：https://developers.weixin.qq.com/doc/oplatform/Website_App/WeChat_Login/Wechat_Login.html
    """

    _AUTH_URL = "https://open.weixin.qq.com/connect/qrconnect"
    _TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
    _USER_INFO_URL = "https://api.weixin.qq.com/sns/userinfo"

    def __init__(self, app_id: str, app_secret: str, redirect_uri: str):
        # 微信使用 app_id/app_secret 而非 client_id/client_secret
        super().__init__(client_id=app_id, client_secret=app_secret, redirect_uri=redirect_uri)
        self.app_id = app_id
        self.app_secret = app_secret

    def get_authorization_url(self, invite_token: str | None = None):
        """获取微信扫码登录授权 URL"""
        params = {
            "appid": self.app_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "snsapi_login",  # 网站应用使用 snsapi_login
        }
        if invite_token:
            params["state"] = invite_token
        else:
            params["state"] = "wechat_login"
        return f"{self._AUTH_URL}?{urllib.parse.urlencode(params)}#wechat_redirect"

    def get_qrcode_url(self, invite_token: str | None = None):
        """获取内嵌二维码的参数（用于前端 JS SDK 生成二维码）"""
        return {
            "appid": self.app_id,
            "redirect_uri": self.redirect_uri,
            "scope": "snsapi_login",
            "state": invite_token or "wechat_login",
        }

    def get_access_token(self, code: str):
        """通过 code 获取 access_token"""
        params = {
            "appid": self.app_id,
            "secret": self.app_secret,
            "code": code,
            "grant_type": "authorization_code",
        }
        response = httpx.get(self._TOKEN_URL, params=params)
        response_json = response.json()

        if "errcode" in response_json:
            raise ValueError(f"Error in WeChat OAuth: {response_json}")

        # 返回包含 access_token 和 openid 的字典
        return {
            "access_token": response_json["access_token"],
            "openid": response_json["openid"],
            "unionid": response_json.get("unionid", ""),
        }

    def get_raw_user_info(self, token: str | dict):
        """获取用户信息

        token 可以是字符串（access_token）或字典（包含 access_token 和 openid）
        """
        if isinstance(token, dict):
            access_token = token["access_token"]
            openid = token["openid"]
        else:
            raise ValueError("WeChat OAuth requires both access_token and openid")

        params = {"access_token": access_token, "openid": openid, "lang": "zh_CN"}
        response = httpx.get(self._USER_INFO_URL, params=params)
        response_json = response.json()

        if "errcode" in response_json:
            raise ValueError(f"Error getting WeChat user info: {response_json}")

        return response_json

    def _transform_user_info(self, raw_info: dict) -> OAuthUserInfo:
        """转换微信用户信息

        微信不返回邮箱，使用 unionid 或 openid 生成虚拟邮箱
        """
        # 优先使用 unionid（跨应用唯一），否则使用 openid
        user_id = raw_info.get("unionid") or raw_info["openid"]
        nickname = raw_info.get("nickname", "微信用户")
        # 生成虚拟邮箱（微信不提供真实邮箱）
        email = f"{raw_info['openid']}@wechat.placeholder"

        return OAuthUserInfo(id=user_id, name=nickname, email=email)
