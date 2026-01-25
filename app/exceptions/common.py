from fastapi import HTTPException


class BaseHTTPException(HTTPException):
    status_code: int = 400
    detail: str = ""

    def __init__(self, detail: str | None = None):
        super().__init__(status_code=self.status_code, detail=detail or self.detail)


# =============================================================================
# 认证相关异常 (401)
# =============================================================================
class Unauthorized(BaseHTTPException):
    status_code = 401
    detail = "Unauthorized."


class UnauthorizedError(BaseHTTPException):
    status_code = 401
    detail = "Unauthorized."


class CSRFValidationError(BaseHTTPException):
    status_code = 403
    detail = "CSRF validation failed."


class AccountNotFoundError(BaseHTTPException):
    status_code = 401
    detail = "Account not found."


class AccountBannedError(BaseHTTPException):
    status_code = 401
    detail = "Account has been banned."


class InvalidCredentialsError(BaseHTTPException):
    status_code = 401
    detail = "Invalid credentials."


class TokenExpiredError(BaseHTTPException):
    status_code = 401
    detail = "Token has expired."


class InvalidTokenSignatureError(BaseHTTPException):
    status_code = 401
    detail = "Invalid token signature."


class InvalidTokenError(BaseHTTPException):
    status_code = 401
    detail = "Invalid token."


# =============================================================================
# 权限相关异常 (403)
# =============================================================================
class ForbiddenError(BaseHTTPException):
    status_code = 403
    detail = "Permission denied."


class AccountForbiddenError(BaseHTTPException):
    status_code = 403
    detail = "Account has been forbidden."


class RegistrationDisabledError(BaseHTTPException):
    status_code = 403
    detail = "Registration is disabled."


class WorkspaceCreationDisabledError(BaseHTTPException):
    status_code = 403
    detail = "Workspace creation is disabled."


class WorkspaceLimitExceededError(BaseHTTPException):
    status_code = 403
    detail = "Workspace limit exceeded."


class IpNotInWhitelistError(BaseHTTPException):
    status_code = 403
    detail = "IP address not in whitelist."


class AlreadyMemberError(BaseHTTPException):
    status_code = 403
    detail = "Account is already a member of the workspace."


# =============================================================================
# 资源不存在异常 (404)
# =============================================================================
class NotFoundError(BaseHTTPException):
    status_code = 404
    detail = "Resource not found."


class TenantNotFoundError(BaseHTTPException):
    status_code = 404
    detail = "Tenant not found."


class MemberNotFoundError(BaseHTTPException):
    status_code = 404
    detail = "Member not found."


class DocumentNotFoundError(BaseHTTPException):
    status_code = 404
    detail = "Document not found."


class FileNotFoundError(BaseHTTPException):
    status_code = 404
    detail = "File not found."


class InvalidSignatureError(BaseHTTPException):
    status_code = 404
    detail = "Invalid signature."


class OAuthProviderNotFoundError(BaseHTTPException):
    status_code = 404
    detail = "OAuth provider not found."


# =============================================================================
# 请求参数异常 (400)
# =============================================================================
class BadRequestError(BaseHTTPException):
    status_code = 400
    detail = "Bad request."


class AccountAlreadyInitedError(BaseHTTPException):
    detail = "The account has been initialized. Please refresh the page."
    status_code = 400


class InvalidInvitationCodeError(BaseHTTPException):
    detail = "Invalid invitation code."
    status_code = 400


class InvalidEmailError(BaseHTTPException):
    status_code = 400
    detail = "Invalid email address."


class EmailCodeError(BaseHTTPException):
    status_code = 400
    detail = "Email code is invalid or expired."


class PasswordMismatchError(BaseHTTPException):
    status_code = 400
    detail = "Passwords do not match."


class EmailAlreadyInUseError(BaseHTTPException):
    status_code = 400
    detail = "Email is already in use."


class InvalidRoleError(BaseHTTPException):
    status_code = 400
    detail = "Invalid role."


class SameRoleError(BaseHTTPException):
    status_code = 400
    detail = "New role is the same as the old role."


class CannotOperateSelfError(BaseHTTPException):
    status_code = 400
    detail = "Cannot operate on yourself."


class InvalidActionError(BaseHTTPException):
    status_code = 400
    detail = "Invalid action."


class InvalidFileTypeError(BaseHTTPException):
    status_code = 400
    detail = "Invalid file type."


class FileTypeNotSupportedError(BaseHTTPException):
    status_code = 400
    detail = "File type not supported."


class WorkspaceArchivedError(BaseHTTPException):
    status_code = 400
    detail = "Workspace is archived."


class AccountNotLinkedError(BaseHTTPException):
    status_code = 400
    detail = "Account not linked to tenant."


class RevokedApiKeyError(BaseHTTPException):
    status_code = 400
    detail = "Revoked API key cannot be enabled."


class InvalidRedirectUriError(BaseHTTPException):
    status_code = 400
    detail = "Invalid redirect URI."


class WeChatLoginDisabledError(BaseHTTPException):
    status_code = 400
    detail = "WeChat login is not enabled."


# =============================================================================
# 速率限制异常 (429)
# =============================================================================
class RateLimitError(BaseHTTPException):
    status_code = 429
    detail = "Rate limit exceeded."


class EmailSendIpLimitError(BaseHTTPException):
    status_code = 429
    detail = "Too many emails sent from this IP. Please try again later."


class EmailRegisterLimitError(BaseHTTPException):
    status_code = 429
    detail = "Too many register attempts. Please try again in 24 hours."


class LoginRateLimitError(BaseHTTPException):
    status_code = 429
    detail = "Too many login attempts."


class PasswordResetRateLimitError(BaseHTTPException):
    status_code = 429
    detail = "Password reset rate limit exceeded."


class EmailCodeRateLimitError(BaseHTTPException):
    status_code = 429
    detail = "Email verification code rate limit exceeded."


class ChangeEmailRateLimitError(BaseHTTPException):
    status_code = 429
    detail = "Change email rate limit exceeded."


class OwnerTransferRateLimitError(BaseHTTPException):
    status_code = 429
    detail = "Owner transfer rate limit exceeded."


class EmailCodeLoginRateLimitError(BaseHTTPException):
    status_code = 429
    detail = "Email code login rate limit exceeded."


# =============================================================================
# 服务器错误 (500)
# =============================================================================
class InternalServerError(BaseHTTPException):
    status_code = 500
    detail = "Internal server error."


class AccountLinkError(BaseHTTPException):
    status_code = 500
    detail = "Failed to link account."
