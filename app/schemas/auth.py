import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from configs import app_config
from constants.languages import supported_language
from libs.helper import timezone
from libs.password import valid_password
from models.account import TenantAccountRole


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool | None = False
    invite_token: str | None = None

    @field_validator("password")
    def validate_password(cls, v: str) -> str:
        if not re.match(app_config.PASSWORD_REGEX, v):
            raise ValueError(
                "Password must contain letters and numbers, and the length must be greater than 8."
            )
        return v


class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("password")
    def validate_password(cls, v: str) -> str:
        if not re.match(app_config.PASSWORD_REGEX, v):
            raise ValueError(
                "Password must contain letters and numbers, and the length must be greater than 8."
            )
        return v


class EmailRegisterSendPayload(BaseModel):
    email: EmailStr = Field(..., description="Email address")
    language: str | None = Field(default=None, description="Language code")


class EmailRegisterValidityPayload(BaseModel):
    email: EmailStr = Field(...)
    code: str = Field(...)
    token: str = Field(...)


class EmailRegisterResetPayload(BaseModel):
    token: str = Field(...)
    new_password: str = Field(...)
    password_confirm: str = Field(...)

    @field_validator("new_password", "password_confirm")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return valid_password(value)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    csrf_token: str


class AccountModel(BaseModel):
    id: str
    name: str
    email: EmailStr
    avatar: str | None = None
    avatar_url: str | None = None
    interface_language: str | None = None
    interface_theme: str | None = None
    timezone: str | None = None
    last_login_at: datetime | None = None
    last_login_ip: str | None = None
    last_active_at: datetime | None = None
    created_at: datetime
    is_password_set: bool
    role: str | None = None
    status: str | None = None  # pending, active, banned, closed
    model_config = ConfigDict(from_attributes=True)


class SetupInModel(BaseModel):
    email: EmailStr = Field(..., description="Admin email address")
    name: str = Field(..., max_length=30, description="Admin name (max 30 characters)")
    password: str = Field(..., description="Admin password")
    language: str | None = Field(default="zh-Hans", description="Admin language")


class MemberInvitePayload(BaseModel):
    emails: list[str] = Field(default_factory=list)
    role: TenantAccountRole
    language: str | None = None


class ActivateCheckQuery(BaseModel):
    workspace_id: str | None = Field(default=None)
    email: EmailStr | None = Field(default=None)
    token: str


class ActivatePayload(BaseModel):
    workspace_id: str | None = Field(default=None)
    email: EmailStr | None = Field(default=None)
    token: str
    name: str = Field(..., max_length=30)
    interface_language: str = Field(...)
    timezone: str = Field(...)

    @field_validator("interface_language")
    @classmethod
    def validate_lang(cls, value: str) -> str:
        return supported_language(value)

    @field_validator("timezone")
    @classmethod
    def validate_tz(cls, value: str) -> str:
        return timezone(value)


class MemberRoleUpdatePayload(BaseModel):
    role: str


class EmailPayload(BaseModel):
    email: EmailStr = Field(...)
    language: str | None = Field(default=None)


class EmailCodeLoginPayload(BaseModel):
    email: EmailStr = Field(...)
    code: str = Field(...)
    token: str = Field(...)
    language: str | None = Field(default=None)

    @field_validator("code")
    @classmethod
    def decode_base64_code(cls, value: str) -> str:
        from libs.encryption import FieldEncryption

        decoded = FieldEncryption.decrypt_verification_code(value)
        if decoded is None:
            raise ValueError("Invalid verification code format")
        return decoded


class AdminLoginIn(BaseModel):
    email: EmailStr = Field(...)
    password: str
    remember_me: bool | None = False


class AdminModel(BaseModel):
    id: str
    name: str
    email: str | None = None
    avatar: str | None = None
    avatar_url: str | None = None
    interface_language: str | None = None
    interface_theme: str | None = None
    timezone: str | None = None
    last_login_at: datetime | None = None
    last_login_ip: str | None = None
    last_active_at: datetime | None = None
    created_at: datetime
    role: str | None = None
    model_config = ConfigDict(from_attributes=True)
