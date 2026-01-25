import type {
  AccountIntegrate,
  ApiBasedExtension,
  CommonResponse,
  FileUploadConfigResponse,
  Member,
  UserProfileResponse,
} from '@/models/common'
import { useMutation, useQuery } from '@tanstack/react-query'
import { get, post } from './base'

const NAME_SPACE = 'common'
export const commonQueryKeys = {
  fileUploadConfig: [NAME_SPACE, 'file-upload-config'] as const,
  userProfile: [NAME_SPACE, 'user-profile'] as const,
  members: [NAME_SPACE, 'members'] as const,
  filePreview: (fileID: string) => [NAME_SPACE, 'file-preview', fileID] as const,
  isLogin: [NAME_SPACE, 'is-login'] as const,
  accountIntegrates: [NAME_SPACE, 'account-integrates'] as const,
  invitationCheck: (params?: { email?: string, token?: string }) => [
    NAME_SPACE,
    'invitation-check',
    params?.email ?? '',
    params?.token ?? '',
  ] as const,
  forgotPasswordValidity: (token?: string | null) => [NAME_SPACE, 'forgot-password-validity', token] as const,
}

export const useFileUploadConfig = () => {
  return useQuery<FileUploadConfigResponse>({
    queryKey: [NAME_SPACE, 'file-upload-config'],
    queryFn: () => get<FileUploadConfigResponse>('/files/upload'),
  })
}

export type MailSendResponse = { token: string }
export const useSendMail = () => {
  return useMutation({
    mutationKey: [NAME_SPACE, 'mail-send'],
    mutationFn: (body: { email: string, language: string }) => {
      return post<MailSendResponse>('/email-register/send-email', { body })
    },
  })
}

export type MailValidityResponse = { is_valid: boolean, token: string }

export const useMailValidity = () => {
  return useMutation({
    mutationKey: [NAME_SPACE, 'mail-validity'],
    mutationFn: (body: { email: string, code: string, token: string }) => {
      return post<MailValidityResponse>('/email-register/validity', { body })
    },
  })
}

export type MailRegisterResponse = { token_pair: Record<string, any> }

export const useMailRegister = () => {
  return useMutation({
    mutationKey: [NAME_SPACE, 'mail-register'],
    mutationFn: (body: { token: string, new_password: string, password_confirm: string }) => {
      return post<MailRegisterResponse>('/email-register', { body })
    },
  })
}

export const useFileSupportTypes = () => {
  return useQuery<any>({
    queryKey: [NAME_SPACE, 'file-types'],
    queryFn: () => get<any>('/files/support-type'),
  })
}

type MemberResponse = {
  accounts: Member[] | null
}

export const useMembers = () => {
  return useQuery<MemberResponse>({
    queryKey: [NAME_SPACE, 'members'],
    queryFn: (params: Record<string, any>) => get<MemberResponse>('/platform/members', {
      params,
    }),
  })
}

type FilePreviewResponse = {
  content: string
}

export const useFilePreview = (fileID: string) => {
  return useQuery<FilePreviewResponse>({
    queryKey: [NAME_SPACE, 'file-preview', fileID],
    queryFn: () => get<FilePreviewResponse>(`/files/${fileID}/preview`),
    enabled: !!fileID,
  })
}

type isLogin = {
  logged_in: boolean
}

export const useIsLogin = () => {
  return useQuery<isLogin>({
    queryKey: [NAME_SPACE, 'is-login'],
    staleTime: 0,
    gcTime: 0,
    queryFn: async (): Promise<isLogin> => {
      try {
        await get('/account/profile', {}, {
          silent: true,
        })
      }
      catch (e: any) {
        if (e.status === 401)
          return { logged_in: false }
        return { logged_in: true }
      }
      return { logged_in: true }
    },
  })
}

export const useLogout = () => {
  return useMutation({
    mutationKey: [NAME_SPACE, 'logout'],
    mutationFn: () => post('/logout'),
  })
}

export const useInvitationCheck = (params?: { email?: string, token?: string }, enabled?: boolean) => {
  return useQuery({
    queryKey: commonQueryKeys.invitationCheck(params),
    queryFn: () => get<{
      is_valid: boolean
      data: { email: string }
      result: string
    }>('/activate/check', { params }),
    enabled: enabled ?? !!params?.token,
    retry: false,
  })
}

export const useAccountIntegrates = () => {
  return useQuery<{ data: AccountIntegrate[] | null }>({
    queryKey: commonQueryKeys.accountIntegrates,
    queryFn: () => get<{ data: AccountIntegrate[] | null }>('/account/integrates'),
  })
}

type OneMoreStepPayload = {
  invitation_code: string
  interface_language: string
  timezone: string
}
export const useOneMoreStep = () => {
  return useMutation({
    mutationKey: [NAME_SPACE, 'one-more-step'],
    mutationFn: (body: OneMoreStepPayload) => post<CommonResponse>('/account/init', { body }),
  })
}

type ForgotPasswordValidity = CommonResponse & { is_valid: boolean, email: string }
export const useVerifyForgotPasswordToken = (token?: string | null) => {
  return useQuery<ForgotPasswordValidity>({
    queryKey: commonQueryKeys.forgotPasswordValidity(token),
    queryFn: () => post<ForgotPasswordValidity>('/forgot-password/validity', { body: { token } }),
    enabled: !!token,
    staleTime: 0,
    gcTime: 0,
    retry: false,
  })
}

type UserProfileWithMeta = {
  profile: UserProfileResponse
  meta: {
    currentVersion: string | null
    currentEnv: string | null
  }
}

export const useUserProfile = () => {
  return useQuery<UserProfileWithMeta>({
    queryKey: commonQueryKeys.userProfile,
    queryFn: async () => {
      const response = await get<Response>('/account/profile', {}, { needAllResponseContent: true }) as Response
      const result = await response.clone().json() as { code: number, msg: string, data: UserProfileResponse }
      return {
        profile: result.data,
        meta: {
          currentVersion: response.headers.get('x-version'),
          currentEnv: process.env.NODE_ENV === 'development'
            ? 'DEVELOPMENT'
            : response.headers.get('x-env'),
        },
      }
    },
    staleTime: 0,
    gcTime: 0,
  })
}

export const useApiBasedExtensions = () => {
  return useQuery<ApiBasedExtension[]>({
    queryKey: [NAME_SPACE, 'api-based-extensions'],
    queryFn: () => get<ApiBasedExtension[]>('/api-based-extension'),
  })
}
