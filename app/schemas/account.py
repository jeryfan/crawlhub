from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from constants.languages import supported_language
from exceptions.common import PasswordMismatchError
from libs.helper import timezone


class AccountInitPayload(BaseModel):
    interface_language: str
    timezone: str
    invitation_code: str | None = None

    @field_validator("interface_language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        return supported_language(value)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        return timezone(value)


class AccountAvatarPayload(BaseModel):
    avatar: str


class AccountNamePayload(BaseModel):
    name: str = Field(min_length=3, max_length=30)


class AccountPasswordPayload(BaseModel):
    password: str | None = None
    new_password: str
    repeat_new_password: str

    @model_validator(mode="after")
    def check_passwords_match(self) -> "AccountPasswordPayload":
        if self.new_password != self.repeat_new_password:
            raise PasswordMismatchError()
        return self


class AccountTimezonePayload(BaseModel):
    timezone: str

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        return timezone(value)


class AccountInterfaceLanguagePayload(BaseModel):
    interface_language: str

    @field_validator("interface_language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        return supported_language(value)


class AccountDeletePayload(BaseModel):
    token: str
    code: str


class AccountDeletionFeedbackPayload(BaseModel):
    email: EmailStr
    feedback: str


class WorkspaceInfoPayload(BaseModel):
    name: str


class SwitchWorkspacePayload(BaseModel):
    tenant_id: str


class InitValidatePayload(BaseModel):
    password: str = Field(..., max_length=30)


class OAuthClientPayload(BaseModel):
    client_id: str


class OAuthProviderRequest(BaseModel):
    client_id: str
    redirect_uri: str


class OAuthTokenRequest(BaseModel):
    client_id: str
    grant_type: str
    code: str | None = None
    client_secret: str | None = None
    redirect_uri: str | None = None
    refresh_token: str | None = None
