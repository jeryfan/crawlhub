import type { ApiResponse } from '@/types/app'

export type CommonResponse = {
  result: 'success' | 'fail'
}

export type FileDownloadResponse = {
  id: string
  name: string
  size: number
  extension: string
  url: string
  download_url: string
  mime_type: string
  created_by: string
  created_at: number
}

export type OauthResponse = {
  redirect_url: string
}

export type SetupStatusResponse = {
  step: 'finished' | 'not_started'
  setup_at?: Date
}

export type InitValidateStatusResponse = {
  status: 'finished' | 'not_started'
}

export type UserProfileResponse = {
  id: string
  name: string
  email: string
  avatar: string
  avatar_url: string | null
  is_password_set: boolean
  interface_language?: string
  interface_theme?: string
  timezone?: string
  last_login_at?: string
  last_active_at?: string
  last_login_ip?: string
  created_at?: string
}

export type UserProfileOriginResponse = {
  json: () => Promise<ApiResponse<UserProfileResponse>>
  bodyUsed: boolean
  headers: any
}

export type AppVersionResponse = {
  current_version: string
  latest_version: string
  version: string
  release_date: string
  release_notes: string
  can_auto_update: boolean
  current_env: string
}

export type Member = Pick<UserProfileResponse, 'id' | 'name' | 'email' | 'last_login_at' | 'last_active_at' | 'created_at' | 'avatar_url'> & {
  avatar: string
  status: 'pending' | 'active' | 'banned' | 'closed'
  role: 'owner' | 'admin' | 'editor' | 'normal'
}

export type AccountIntegrate = {
  provider: 'google' | 'github'
  created_at: number
  is_bound: boolean
  link: string
}

export type FileUploadConfigResponse = {
  batch_count_limit: number
  image_file_size_limit?: number | string
  file_size_limit: number
  audio_file_size_limit?: number
  video_file_size_limit?: number
  workflow_file_upload_limit?: number
  file_upload_limit: number
}

export type InvitationResult = {
  status: 'success'
  email: string
  url: string
} | {
  status: 'failed'
  email: string
  message: string
}

export type InvitationResponse = CommonResponse & {
  invitation_results: InvitationResult[]
}

export type MoreLikeThisConfig = {
  enabled: boolean
}

export type ApiBasedExtension = {
  id?: string
  name?: string
  api_endpoint?: string
  api_key?: string
  tenant_id?: string
}

export type ModerateResponse = {
  flagged: boolean
  text: string
}

export type ModerationService = (
  url: string,
  body: {
    app_id: string
    text: string
  },
) => Promise<ModerateResponse>
