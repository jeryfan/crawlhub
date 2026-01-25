'use client'

import type { Area } from 'react-easy-crop'
import type { OnImageInput } from '@/app/components/base/app-icon-picker/ImageInput'
import {
  RiCheckboxBlankCircleLine,
  RiCheckboxBlankLine,
  RiCloseLine,
  RiImage2Line,
  RiUpload2Line,
} from '@remixicon/react'
import { useCallback, useEffect, useState } from 'react'
import ImageInput from '@/app/components/base/app-icon-picker/ImageInput'
import getCroppedImg from '@/app/components/base/app-icon-picker/utils'
import Button from '@/app/components/base/button'
import Divider from '@/app/components/base/divider'
import Modal from '@/app/components/base/modal'
import { upload } from '@/service/base'
import { cn } from '@/utils/classnames'

type UploadFileResponse = {
  id: string
  file_url?: string
  source_url?: string
}

// 圆形裁剪函数
async function getCroppedCircleImg(
  imageSrc: string,
  pixelCrop: { x: number, y: number, width: number, height: number },
): Promise<Blob> {
  const image = await new Promise<HTMLImageElement>((resolve, reject) => {
    const img = new Image()
    img.addEventListener('load', () => resolve(img))
    img.addEventListener('error', error => reject(error))
    img.setAttribute('crossOrigin', 'anonymous')
    img.src = imageSrc
  })

  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')

  if (!ctx)
    throw new Error('Could not create a canvas context')

  const size = Math.min(pixelCrop.width, pixelCrop.height)
  canvas.width = size
  canvas.height = size

  // 创建圆形裁剪路径
  ctx.beginPath()
  ctx.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2)
  ctx.closePath()
  ctx.clip()

  // 绘制图片
  ctx.drawImage(
    image,
    pixelCrop.x,
    pixelCrop.y,
    pixelCrop.width,
    pixelCrop.height,
    0,
    0,
    size,
    size,
  )

  return new Promise((resolve, reject) => {
    canvas.toBlob((file) => {
      if (file)
        resolve(file)
      else reject(new Error('Could not create a blob'))
    }, 'image/png') // 使用 PNG 以支持透明度
  })
}

export type CroppedImageUploadFieldProps = {
  /** 字段标签 */
  label: string
  /** 字段描述 */
  description: string
  /** 当前图片 URL */
  value: string
  /** 值变化回调 */
  onChange: (url: string) => void
  /** 尺寸提示，如 "32×32px" */
  aspectHint?: string
  /** 默认裁剪形状 */
  cropShape?: 'rect' | 'round'
  /** 是否允许用户选择裁剪形状 */
  allowShapeSelection?: boolean
  /** 上传失败时的错误提示 */
  uploadErrorMessage?: string
  /** 自定义上传函数，返回图片 URL */
  customUpload?: (file: File) => Promise<string>
}

type InputImageInfo
  = | { file: File }
    | { tempUrl: string, croppedAreaPixels: Area, fileName: string }

const CroppedImageUploadField = ({
  label,
  description,
  value,
  onChange,
  aspectHint,
  cropShape: defaultCropShape = 'rect',
  allowShapeSelection = false,
  uploadErrorMessage = '图片上传失败，请重试',
  customUpload,
}: CroppedImageUploadFieldProps) => {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [inputImageInfo, setInputImageInfo] = useState<InputImageInfo>()
  const [isHovered, setIsHovered] = useState(false)
  const [selectedShape, setSelectedShape] = useState<'rect' | 'round'>(
    defaultCropShape,
  )
  const [uploadError, setUploadError] = useState<string>()

  // 当弹窗打开时重置为默认形状
  useEffect(() => {
    if (isModalOpen) {
      setSelectedShape(defaultCropShape)
      setUploadError(undefined)
    }
  }, [isModalOpen, defaultCropShape])

  const cropShape = allowShapeSelection ? selectedShape : defaultCropShape

  const uploadFile = useCallback(
    async (file: File) => {
      setIsUploading(true)
      setUploadError(undefined)

      try {
        let fileUrl: string

        if (customUpload) {
          fileUrl = await customUpload(file)
        }
        else {
          const formData = new FormData()
          formData.append('file', file)

          const res = (await upload({
            xhr: new XMLHttpRequest(),
            data: formData,
          })) as unknown as { data: UploadFileResponse }

          fileUrl = res.data?.file_url || res.data?.source_url || ''
        }

        onChange(fileUrl)
        setIsModalOpen(false)
        setInputImageInfo(undefined)
      }
      catch (error) {
        console.error('Upload failed:', error)
        setUploadError(uploadErrorMessage)
      }
      finally {
        setIsUploading(false)
      }
    },
    [onChange, customUpload, uploadErrorMessage],
  )

  const handleImageInput: OnImageInput = useCallback(
    async (
      isCropped: boolean,
      fileOrTempUrl: string | File,
      croppedAreaPixels?: Area,
      fileName?: string,
    ) => {
      setInputImageInfo(
        isCropped
          ? {
              tempUrl: fileOrTempUrl as string,
              croppedAreaPixels: croppedAreaPixels!,
              fileName: fileName!,
            }
          : { file: fileOrTempUrl as File },
      )
      setUploadError(undefined)
    },
    [],
  )

  const handleConfirm = useCallback(async () => {
    if (!inputImageInfo)
      return

    if ('file' in inputImageInfo) {
      await uploadFile(inputImageInfo.file)
      return
    }

    // 根据 cropShape 选择裁剪方式
    const blob
      = cropShape === 'round'
        ? await getCroppedCircleImg(
            inputImageInfo.tempUrl,
            inputImageInfo.croppedAreaPixels,
          )
        : await getCroppedImg(
            inputImageInfo.tempUrl,
            inputImageInfo.croppedAreaPixels,
            inputImageInfo.fileName,
          )

    const fileName
      = cropShape === 'round'
        ? inputImageInfo.fileName.replace(/\.[^.]+$/, '.png') // 圆形裁剪使用 PNG
        : inputImageInfo.fileName

    const file = new File([blob], fileName, { type: blob.type })
    await uploadFile(file)
  }, [inputImageInfo, uploadFile, cropShape])

  const handleClear = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      onChange('')
    },
    [onChange],
  )

  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false)
    setInputImageInfo(undefined)
    setUploadError(undefined)
  }, [])

  return (
    <>
      <div className="group">
        <div className="mb-2.5 flex items-start justify-between">
          <div>
            <p className="text-[13px] font-semibold text-text-primary">
              {label}
            </p>
            <p className="mt-0.5 text-xs text-text-tertiary">{description}</p>
          </div>
          {aspectHint && (
            <span className="bg-components-badge-bg-gray rounded-md px-1.5 py-0.5 text-[10px] font-medium text-text-quaternary">
              {aspectHint}
            </span>
          )}
        </div>

        <div
          className={cn(
            'relative flex h-28 cursor-pointer items-center justify-center overflow-hidden rounded-xl border-2 border-dashed transition-all duration-300',
            value
              ? 'to-background-default-dimm border-transparent bg-gradient-to-br from-background-default-subtle'
              : 'border-divider-regular bg-background-default-subtle hover:border-components-button-primary-bg hover:bg-state-accent-hover',
            isHovered
            && value
            && 'ring-2 ring-components-button-primary-bg ring-offset-2 ring-offset-background-body',
          )}
          onClick={() => setIsModalOpen(true)}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
        >
          {value
            ? (
                <>
                  <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(0,0,0,0.02)_0%,transparent_70%)]" />
                  <img
                    src={value}
                    alt={label}
                    className={cn(
                      'relative z-10 max-h-20 max-w-[85%] object-contain transition-transform duration-300',
                      isHovered && 'scale-105',
                    )}
                  />
                  <div
                    className={cn(
                      'bg-background-overlay-alt/80 absolute inset-0 z-20 flex items-center justify-center gap-2 backdrop-blur-sm transition-opacity duration-200',
                      isHovered ? 'opacity-100' : 'opacity-0',
                    )}
                  >
                    <button
                      type="button"
                      className="flex h-8 items-center gap-1.5 rounded-lg bg-white px-3 text-xs font-medium text-text-primary shadow-md transition-transform hover:scale-105"
                      onClick={(e) => {
                        e.stopPropagation()
                        setIsModalOpen(true)
                      }}
                    >
                      <RiUpload2Line className="h-3.5 w-3.5" />
                      更换
                    </button>
                    <button
                      type="button"
                      className="flex h-8 w-8 items-center justify-center rounded-lg bg-state-destructive-solid text-white shadow-md transition-transform hover:scale-105"
                      onClick={handleClear}
                    >
                      <RiCloseLine className="h-4 w-4" />
                    </button>
                  </div>
                </>
              )
            : (
                <div className="flex flex-col items-center gap-2 text-text-quaternary transition-colors group-hover:text-text-tertiary">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-background-default-burn">
                    <RiImage2Line className="h-5 w-5" />
                  </div>
                  <div className="text-center">
                    <span className="text-xs font-medium">点击上传图片</span>
                    <p className="mt-0.5 text-[10px] text-text-quaternary">
                      支持 PNG、JPG、SVG
                    </p>
                  </div>
                </div>
              )}
        </div>
      </div>

      <Modal
        isShow={isModalOpen}
        onClose={handleCloseModal}
        closable
        className="!w-[420px] overflow-hidden !rounded-2xl !p-0"
      >
        <div className="bg-gradient-to-b from-components-panel-bg to-background-body p-5 pb-4">
          <h3 className="text-base font-semibold text-text-primary">{label}</h3>
          <p className="mt-1 text-sm text-text-tertiary">{description}</p>
        </div>

        {/* 形状选择器 */}
        {allowShapeSelection && (
          <div className="flex items-center justify-center gap-2 border-b border-divider-subtle bg-background-default-subtle px-5 py-3">
            <span className="mr-2 text-xs text-text-tertiary">裁剪形状</span>
            <button
              type="button"
              className={cn(
                'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all',
                selectedShape === 'rect'
                  ? 'bg-components-button-primary-bg text-white'
                  : 'hover:bg-background-default-dimm bg-background-default-burn text-text-tertiary',
              )}
              onClick={() => setSelectedShape('rect')}
            >
              <RiCheckboxBlankLine className="h-3.5 w-3.5" />
              矩形
            </button>
            <button
              type="button"
              className={cn(
                'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all',
                selectedShape === 'round'
                  ? 'bg-components-button-primary-bg text-white'
                  : 'hover:bg-background-default-dimm bg-background-default-burn text-text-tertiary',
              )}
              onClick={() => setSelectedShape('round')}
            >
              <RiCheckboxBlankCircleLine className="h-3.5 w-3.5" />
              圆形
            </button>
          </div>
        )}

        <ImageInput
          key={selectedShape}
          className="flex-1 overflow-hidden"
          cropShape={cropShape}
          onImageInput={handleImageInput}
        />

        <Divider className="m-0" />

        <div className="flex items-center justify-between bg-background-body p-4">
          <div>
            {uploadError && (
              <p className="text-xs text-state-destructive-solid">
                {uploadError}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2.5">
            <Button onClick={handleCloseModal}>取消</Button>
            <Button
              variant="primary"
              disabled={!inputImageInfo || isUploading}
              loading={isUploading}
              onClick={handleConfirm}
            >
              确认上传
            </Button>
          </div>
        </div>
      </Modal>
    </>
  )
}

export default CroppedImageUploadField
