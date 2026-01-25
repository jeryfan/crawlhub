import type {
  AccountIntegrate,
  ApiBasedExtension,
  CommonResponse,
  FileUploadConfigResponse,
  InitValidateStatusResponse,
  InvitationResponse,
  Member,
  OauthResponse,
  SetupStatusResponse,
  UserProfileOriginResponse,
} from '@/models/common'
import type { SystemFeatures } from '@/types/feature'
import { del, get, post, put } from './base'

type LoginSuccess = {
  code: number
  msg: string
  data: null
}
type LoginFail = {
  code: number
  msg: string
  data: null
}
type LoginResponse = LoginSuccess | LoginFail
export const login = ({ url, body }: { url: string, body: Record<string, any> }): Promise<LoginResponse> => {
  return post<LoginResponse>(url, { body })
}

export const setup = ({ body }: { body: Record<string, any> }): Promise<CommonResponse> => {
  return post<CommonResponse>('/setup', { body })
}

export const initValidate = ({ body }: { body: Record<string, any> }): Promise<CommonResponse> => {
  return post<CommonResponse>('/init', { body })
}

export const fetchInitValidateStatus = (): Promise<InitValidateStatusResponse> => {
  return get<InitValidateStatusResponse>('/init')
}

export const fetchSetupStatus = (): Promise<SetupStatusResponse> => {
  return get<SetupStatusResponse>('/setup')
}

export const fetchUserProfile = ({ url, params }: { url: string, params: Record<string, any> }): Promise<UserProfileOriginResponse> => {
  return get<UserProfileOriginResponse>(url, params, { needAllResponseContent: true })
}

export const updateUserProfile = ({ url, body }: { url: string, body: Record<string, any> }): Promise<CommonResponse> => {
  return post<CommonResponse>(url, { body })
}

export const oauth = ({ url, params }: { url: string, params: Record<string, any> }): Promise<OauthResponse> => {
  return get<OauthResponse>(url, { params })
}

export const oneMoreStep = ({ url, body }: { url: string, body: Record<string, any> }): Promise<CommonResponse> => {
  return post<CommonResponse>(url, { body })
}

export const fetchMembers = ({ url, params }: { url: string, params: Record<string, any> }): Promise<{ accounts: Member[] | null }> => {
  return get<{ accounts: Member[] | null }>(url, { params })
}

export const fetchAccountIntegrates = ({ url, params }: { url: string, params: Record<string, any> }): Promise<{ data: AccountIntegrate[] | null }> => {
  return get<{ data: AccountIntegrate[] | null }>(url, { params })
}

export const inviteMember = ({ url, body }: { url: string, body: Record<string, any> }): Promise<InvitationResponse> => {
  return post<InvitationResponse>(url, { body })
}

export const updateMemberRole = ({ url, body }: { url: string, body: Record<string, any> }): Promise<CommonResponse> => {
  return put<CommonResponse>(url, { body })
}

export const deleteMemberOrCancelInvitation = ({ url }: { url: string }): Promise<CommonResponse> => {
  return del<CommonResponse>(url)
}

export const invitationCheck = ({ url, params }: { url: string, params: { email?: string, token: string } }): Promise<CommonResponse & { is_valid: boolean, data: { email: string } }> => {
  return get<CommonResponse & { is_valid: boolean, data: { email: string } }>(url, { params })
}

export const activateMember = ({ url, body }: { url: string, body: any }): Promise<LoginResponse> => {
  return post<LoginResponse>(url, { body })
}

export const fetchFileUploadConfig = ({ url }: { url: string }): Promise<FileUploadConfigResponse> => {
  return get<FileUploadConfigResponse>(url)
}

export const getSystemFeatures = (): Promise<SystemFeatures> => {
  return get<SystemFeatures>('/system-features')
}

export const sendForgotPasswordEmail = ({ url, body }: { url: string, body: { email: string } }): Promise<{ token: string }> =>
  post<{ token: string }>(url, { body })

export const verifyForgotPasswordToken = ({ url, body }: { url: string, body: { token: string } }): Promise<CommonResponse & { is_valid: boolean, email: string }> => {
  return post<CommonResponse & { is_valid: boolean, email: string }>(url, { body })
}

export const changePasswordWithToken = ({ url, body }: { url: string, body: { token: string, new_password: string, password_confirm: string } }): Promise<CommonResponse> =>
  post<CommonResponse>(url, { body })

export const sendEMailLoginCode = (email: string, language = 'en-US'): Promise<{ token: string }> =>
  post<{ token: string }>('/email-code-login', { body: { email, language } })

export const emailLoginWithCode = (data: { email: string, code: string, token: string, language: string }): Promise<LoginResponse> =>
  post<LoginResponse>('/email-code-login/validity', { body: data })

export const sendResetPasswordCode = (email: string, language = 'en-US'): Promise<{ token: string, message?: string, code?: string }> =>
  post<{ token: string, message?: string, code?: string }>('/forgot-password', { body: { email, language } })

export const verifyResetPasswordCode = (body: { email: string, code: string, token: string }): Promise<CommonResponse & { is_valid: boolean, token: string }> =>
  post<CommonResponse & { is_valid: boolean, token: string }>('/forgot-password/validity', { body })

export const sendDeleteAccountCode = (): Promise<{ token: string }> =>
  get<{ token: string }>('/account/delete/verify')

export const verifyDeleteAccountCode = (body: { code: string, token: string }): Promise<CommonResponse & { is_valid: boolean }> =>
  post<CommonResponse & { is_valid: boolean }>('/account/delete', { body })

export const submitDeleteAccountFeedback = (body: { feedback: string, email: string }): Promise<CommonResponse> =>
  post<CommonResponse>('/account/delete/feedback', { body })

export const getDocDownloadUrl = (doc_name: string): Promise<{ url: string }> =>
  get<{ url: string }>('/compliance/download', { params: { doc_name } }, { silent: true })

export const sendVerifyCode = (body: { email: string, phase: string, token?: string }): Promise<CommonResponse & { data: string }> =>
  post<CommonResponse & { data: string }>('/account/change-email', { body })

export const verifyEmail = (body: { email: string, code: string, token: string }): Promise<CommonResponse & { is_valid: boolean, email: string, token: string }> =>
  post<CommonResponse & { is_valid: boolean, email: string, token: string }>('/account/change-email/validity', { body })

export const resetEmail = (body: { new_email: string, token: string }): Promise<CommonResponse> =>
  post<CommonResponse>('/account/change-email/reset', { body })

export const checkEmailExisted = (body: { email: string }): Promise<CommonResponse> =>
  post<CommonResponse>('/account/change-email/check-email-unique', { body }, { silent: true })

export const fetchApiBasedExtensionList = (url: string): Promise<ApiBasedExtension[]> => {
  return get<ApiBasedExtension[]>(url)
}

export const fetchApiBasedExtensionDetail = (url: string): Promise<ApiBasedExtension> => {
  return get<ApiBasedExtension>(url)
}

export const addApiBasedExtension = ({ url, body }: { url: string, body: ApiBasedExtension }): Promise<ApiBasedExtension> => {
  return post<ApiBasedExtension>(url, { body })
}

export const updateApiBasedExtension = ({ url, body }: { url: string, body: ApiBasedExtension }): Promise<ApiBasedExtension> => {
  return post<ApiBasedExtension>(url, { body })
}

export const deleteApiBasedExtension = (url: string): Promise<{ result: string }> => {
  return del<{ result: string }>(url)
}
