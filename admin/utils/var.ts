import { getMaxVarNameLength, MAX_VAR_KEY_LENGTH, VAR_ITEM_TEMPLATE } from '@/config'

const otherAllowedRegex = /^\w+$/

export const getNewVar = (key: string, type: string) => {
  const { ...rest } = VAR_ITEM_TEMPLATE
  if (type !== 'string') {
    return {
      ...rest,
      type: type || 'string',
      key,
      name: key.slice(0, getMaxVarNameLength(key)),
    }
  }
  return {
    ...VAR_ITEM_TEMPLATE,
    type: type || 'string',
    key,
    name: key.slice(0, getMaxVarNameLength(key)),
  }
}

export const checkKey = (key: string, canBeEmpty?: boolean, _keys?: string[]) => {
  if (key.length === 0 && !canBeEmpty)
    return 'canNoBeEmpty'

  if (canBeEmpty && key === '')
    return true

  if (key.length > MAX_VAR_KEY_LENGTH)
    return 'tooLong'

  if (otherAllowedRegex.test(key)) {
    if (/\d/.test(key[0]))
      return 'notStartWithNumber'

    return true
  }
  return 'notValid'
}

export const checkKeys = (keys: string[], canBeEmpty?: boolean) => {
  let isValid = true
  let errorKey = ''
  let errorMessageKey = ''
  keys.forEach((key) => {
    if (!isValid)
      return

    const res = checkKey(key, canBeEmpty)
    if (res !== true) {
      isValid = false
      errorKey = key
      errorMessageKey = res
    }
  })
  return { isValid, errorKey, errorMessageKey }
}

export const hasDuplicateStr = (strArr: string[]) => {
  const strObj: Record<string, number> = {}
  strArr.forEach((str) => {
    if (strObj[str])
      strObj[str] += 1
    else
      strObj[str] = 1
  })
  return !!Object.keys(strObj).find(key => strObj[key] > 1)
}

// Set the value of basePath
// example: /fastapi
export const basePath = process.env.NEXT_PUBLIC_BASE_PATH || ''

export const replaceSpaceWithUnderscoreInVarNameInput = (input: HTMLInputElement) => {
  const start = input.selectionStart
  const end = input.selectionEnd

  input.value = input.value.replaceAll(' ', '_')

  if (start !== null && end !== null)
    input.setSelectionRange(start, end)
}
