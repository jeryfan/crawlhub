import type { FetchOptionType } from './fetch'
import type { ApiResponse, VisionFile } from '@/types/app'
import Cookies from 'js-cookie'
import Toast from '@/app/components/base/toast'
import { API_PREFIX, CSRF_COOKIE_NAME, CSRF_HEADER_NAME, IS_CE_EDITION } from '@/config'
import { ResponseCode } from '@/types/response-code'
import { asyncRunSafe } from '@/utils'
import { basePath } from '@/utils/var'
import { base, ContentType, getBaseOptions } from './fetch'
import { refreshAccessTokenOrRelogin } from './refresh-token'

const TIME_OUT = 100000

export type IOnDataMoreInfo = {
  conversationId?: string
  taskId?: string
  messageId: string
  errorMessage?: string
  errorCode?: string
}

export type IOnData = (message: string, isFirstMessage: boolean, moreInfo: IOnDataMoreInfo) => void
export type IOnFile = (file: VisionFile) => void
export type IOnCompleted = (hasError?: boolean, errorMessage?: string) => void
export type IOnError = (msg: string, code?: string) => void

export type IOnTTSChunk = (messageId: string, audioStr: string, audioType?: string) => void
export type IOnTTSEnd = (messageId: string, audioStr: string, audioType?: string) => void

export type IOtherOptions = {
  bodyStringify?: boolean
  needAllResponseContent?: boolean
  deleteContentType?: boolean
  silent?: boolean
  onData?: IOnData // for stream
  onFile?: IOnFile
  onError?: IOnError
  onCompleted?: IOnCompleted // for stream
  getAbortController?: (abortController: AbortController) => void
}

function jumpTo(url: string) {
  if (!url)
    return
  const targetPath = new URL(url, globalThis.location.origin).pathname
  if (targetPath === globalThis.location.pathname)
    return
  globalThis.location.href = url
}

function unicodeToChar(text: string) {
  if (!text)
    return ''

  return text.replace(/\\u([0-9a-f]{4})/g, (_match, p1) => {
    return String.fromCharCode(Number.parseInt(p1, 16))
  })
}

const WBB_APP_LOGIN_PATH = '/webapp-signin'
function requiredWebSSOLogin(message?: string, code?: number) {
  const params = new URLSearchParams()
  // prevent redirect loop
  if (globalThis.location.pathname === WBB_APP_LOGIN_PATH)
    return

  params.append('redirect_url', encodeURIComponent(`${globalThis.location.pathname}${globalThis.location.search}`))
  if (message)
    params.append('message', message)
  if (code)
    params.append('code', String(code))
  globalThis.location.href = `${globalThis.location.origin}${basePath}/${WBB_APP_LOGIN_PATH}?${params.toString()}`
}

export function format(text: string) {
  let res = text.trim()
  if (res.startsWith('\n'))
    res = res.replace('\n', '')

  return res.replaceAll('\n', '<br/>').replaceAll('```', '')
}

export const handleStream = (
  response: Response,
  onData: IOnData,
  onCompleted?: IOnCompleted,
  onFile?: IOnFile,

  onTTSChunk?: IOnTTSChunk,
  onTTSEnd?: IOnTTSEnd,

) => {
  if (!response.ok)
    throw new Error('Network response was not ok')

  const reader = response.body?.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let bufferObj: Record<string, any>
  let isFirstMessage = true
  function read() {
    let hasError = false
    reader?.read().then((result: ReadableStreamReadResult<Uint8Array>) => {
      if (result.done) {
        onCompleted?.()
        return
      }
      buffer += decoder.decode(result.value, { stream: true })
      const lines = buffer.split('\n')
      try {
        lines.forEach((message) => {
          if (message.startsWith('data: ')) { // check if it starts with data:
            try {
              bufferObj = JSON.parse(message.substring(6)) as Record<string, any>// remove data: and parse as json
            }
            catch {
              // mute handle message cut off
              onData('', isFirstMessage, {
                conversationId: bufferObj?.conversation_id,
                messageId: bufferObj?.message_id,
              })
              return
            }
            if (bufferObj.status === 400 || !bufferObj.event) {
              onData('', false, {
                conversationId: undefined,
                messageId: '',
                errorMessage: bufferObj?.message,
                errorCode: bufferObj?.code,
              })
              hasError = true
              onCompleted?.(true, bufferObj?.message)
              return
            }
            if (bufferObj.event === 'message' || bufferObj.event === 'agent_message') {
              // can not use format here. Because message is splitted.
              onData(unicodeToChar(bufferObj.answer), isFirstMessage, {
                conversationId: bufferObj.conversation_id,
                taskId: bufferObj.task_id,
                messageId: bufferObj.id,
              })
              isFirstMessage = false
            }
            else if (bufferObj.event === 'message_file') {
              onFile?.(bufferObj as VisionFile)
            }
            else if (bufferObj.event === 'tts_message') {
              onTTSChunk?.(bufferObj.message_id, bufferObj.audio, bufferObj.audio_type)
            }
            else if (bufferObj.event === 'tts_message_end') {
              onTTSEnd?.(bufferObj.message_id, bufferObj.audio)
            }
            else {
              console.warn(`Unknown event: ${bufferObj.event}`, bufferObj)
            }
          }
        })
        buffer = lines[lines.length - 1]
      }
      catch (e) {
        onData('', false, {
          conversationId: undefined,
          messageId: '',
          errorMessage: `${e}`,
        })
        hasError = true
        onCompleted?.(true, e as string)
        return
      }
      if (!hasError)
        read()
    })
  }
  read()
}

const baseFetch = base

type UploadOptions = {
  xhr: XMLHttpRequest
  method?: string
  url?: string
  headers?: Record<string, string>
  data: FormData
  onprogress?: (this: XMLHttpRequest, ev: ProgressEvent<EventTarget>) => void
}

type UploadResponse = {
  id: string
  [key: string]: unknown
}

export const upload = async (options: UploadOptions, _isPublicAPI?: boolean, url?: string, searchParams?: string): Promise<UploadResponse> => {
  const urlPrefix = API_PREFIX
  const defaultOptions = {
    method: 'POST',
    url: (url ? `${urlPrefix}${url}` : `${urlPrefix}/files/upload`) + (searchParams || ''),
    headers: {
      [CSRF_HEADER_NAME]: Cookies.get(CSRF_COOKIE_NAME()) || '',
    },
  }
  const mergedOptions = {
    ...defaultOptions,
    ...options,
    url: options.url || defaultOptions.url,
    headers: { ...defaultOptions.headers, ...options.headers } as Record<string, string>,
  }
  return new Promise((resolve, reject) => {
    const xhr = mergedOptions.xhr
    xhr.open(mergedOptions.method, mergedOptions.url)
    for (const key in mergedOptions.headers)
      xhr.setRequestHeader(key, mergedOptions.headers[key])

    xhr.withCredentials = true
    xhr.responseType = 'json'
    xhr.onreadystatechange = function () {
      if (xhr.readyState === 4) {
        if (xhr.status === 200 || xhr.status === 201) {
          // Handle API response format: { code, msg, data }
          const response = xhr.response
          if (response?.data)
            resolve(response.data)
          else
            resolve(response)
        }
        else {
          reject(xhr)
        }
      }
    }
    if (mergedOptions.onprogress)
      xhr.upload.onprogress = mergedOptions.onprogress
    xhr.send(mergedOptions.data)
  })
}

export const ssePost = async (
  url: string,
  fetchOptions: FetchOptionType,
  otherOptions: IOtherOptions,
) => {
  const {
    onData,
    onCompleted,
    onFile,
    onError,
    getAbortController,
  } = otherOptions
  const abortController = new AbortController()

  const baseOptions = getBaseOptions()
  const options = Object.assign({}, baseOptions, {
    method: 'POST',
    signal: abortController.signal,
    headers: new Headers({
      [CSRF_HEADER_NAME]: Cookies.get(CSRF_COOKIE_NAME()) || '',
    }),
  } as RequestInit, fetchOptions)

  const contentType = (options.headers as Headers).get('Content-Type')
  if (!contentType)
    (options.headers as Headers).set('Content-Type', ContentType.json)

  getAbortController?.(abortController)

  const urlWithPrefix = (url.startsWith('http://') || url.startsWith('https://'))
    ? url
    : `${API_PREFIX}${url.startsWith('/') ? url : `/${url}`}`

  const { body } = options
  if (body)
    options.body = JSON.stringify(body)

  globalThis.fetch(urlWithPrefix, options as RequestInit)
    .then((res) => {
      if (!/^[23]\d{2}$/.test(String(res.status))) {
        if (res.status === 401) {
          refreshAccessTokenOrRelogin(TIME_OUT).then(() => {
            ssePost(url, fetchOptions, otherOptions)
          }).catch((err) => {
            console.error(err)
          })
        }
        else {
          res.json().then((data) => {
            Toast.notify({ type: 'error', message: data.msg || 'Server Error' })
          })
          onError?.('Server Error')
        }
        return
      }
      return handleStream(
        res,
        (str: string, isFirstMessage: boolean, moreInfo: IOnDataMoreInfo) => {
          if (moreInfo.errorMessage) {
            onError?.(moreInfo.errorMessage, moreInfo.errorCode)
            // TypeError: Cannot assign to read only property ... will happen in page leave, so it should be ignored.
            if (moreInfo.errorMessage !== 'AbortError: The user aborted a request.' && !moreInfo.errorMessage.includes('TypeError: Cannot assign to read only property'))
              Toast.notify({ type: 'error', message: moreInfo.errorMessage })
            return
          }
          onData?.(str, isFirstMessage, moreInfo)
        },
        onCompleted,
        onFile,
      )
    })
    .catch((e) => {
      if (e.toString() !== 'AbortError: The user aborted a request.' && !e.toString().includes('TypeError: Cannot assign to read only property'))
        Toast.notify({ type: 'error', message: e })
      onError?.(e)
    })
}

// base request
export const request = async<T>(url: string, options = {}, otherOptions?: IOtherOptions) => {
  try {
    const otherOptionsForBaseFetch = otherOptions || {}
    const [err, resp] = await asyncRunSafe<T>(baseFetch(url, options, otherOptionsForBaseFetch))
    if (err === null)
      return resp
    const errResp: Response = err as any
    console.log('errResp', errResp)

    if (errResp.status === 401) {
      const [parseErr, errRespData] = await asyncRunSafe<ApiResponse>(errResp.json())
      const loginUrl = `${globalThis.location.origin}${basePath}/signin`
      if (parseErr) {
        globalThis.location.href = loginUrl
        return Promise.reject(err)
      }
      if (/\/login/.test(url))
        return Promise.reject(errRespData)
      // special code
      const { code, msg } = errRespData
      // webapp sso
      if (code === ResponseCode.WEB_APP_ACCESS_DENIED) {
        requiredWebSSOLogin(msg, 403)
        return Promise.reject(err)
      }
      if (code === ResponseCode.WEB_SSO_AUTH_REQUIRED) {
        requiredWebSSOLogin()
        return Promise.reject(err)
      }
      if (code === ResponseCode.UNAUTHORIZED_AND_FORCE_LOGOUT) {
        // Cookies will be cleared by the backend
        globalThis.location.reload()
        return Promise.reject(err)
      }
      const { silent } = otherOptionsForBaseFetch
      if (code === ResponseCode.INIT_VALIDATE_FAILED && IS_CE_EDITION && !silent) {
        Toast.notify({ type: 'error', message: msg, duration: 4000 })
        return Promise.reject(err)
      }
      if (code === ResponseCode.NOT_INIT_VALIDATED && IS_CE_EDITION) {
        jumpTo(`${globalThis.location.origin}${basePath}/init`)
        return Promise.reject(err)
      }
      if (code === ResponseCode.NOT_SETUP && IS_CE_EDITION) {
        jumpTo(`${globalThis.location.origin}${basePath}/install`)
        return Promise.reject(err)
      }

      // refresh token
      const [refreshErr] = await asyncRunSafe(refreshAccessTokenOrRelogin(TIME_OUT))
      if (refreshErr === null)
        return baseFetch<T>(url, options, otherOptionsForBaseFetch)
      if (location.pathname !== `${basePath}/signin` || !IS_CE_EDITION) {
        jumpTo(loginUrl)
        return Promise.reject(err)
      }
      if (!silent) {
        Toast.notify({ type: 'error', message: msg })
        return Promise.reject(err)
      }
      jumpTo(loginUrl)
      return Promise.reject(err)
    }
    else {
      return Promise.reject(err)
    }
  }
  catch (error) {
    console.error(error)
    return Promise.reject(error)
  }
}

// request methods
export const get = <T>(url: string, options = {}, otherOptions?: IOtherOptions) => {
  return request<T>(url, Object.assign({}, options, { method: 'GET' }), otherOptions)
}

export const post = <T>(url: string, options = {}, otherOptions?: IOtherOptions) => {
  return request<T>(url, Object.assign({}, options, { method: 'POST' }), otherOptions)
}

export const put = <T>(url: string, options = {}, otherOptions?: IOtherOptions) => {
  return request<T>(url, Object.assign({}, options, { method: 'PUT' }), otherOptions)
}

export const del = <T>(url: string, options = {}, otherOptions?: IOtherOptions) => {
  return request<T>(url, Object.assign({}, options, { method: 'DELETE' }), otherOptions)
}

export const patch = <T>(url: string, options = {}, otherOptions?: IOtherOptions) => {
  return request<T>(url, Object.assign({}, options, { method: 'PATCH' }), otherOptions)
}
