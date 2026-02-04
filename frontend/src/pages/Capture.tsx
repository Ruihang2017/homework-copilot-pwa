import { useState, useRef, useCallback, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { api, ApiError } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useToast } from '@/hooks/use-toast'
import type { Question } from '@/types'
import { Camera, Upload, X, Loader2, RotateCcw, ArrowLeft } from 'lucide-react'

export default function Capture() {
  const { profileId } = useParams<{ profileId: string }>()
  const [mode, setMode] = useState<'select' | 'camera' | 'preview'>('select')
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [imageData, setImageData] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { token } = useAuth()
  const navigate = useNavigate()
  const { toast } = useToast()

  // Assign stream to video element when both are available
  useEffect(() => {
    if (mode === 'camera' && stream && videoRef.current) {
      videoRef.current.srcObject = stream
    }
  }, [mode, stream])

  const startCamera = useCallback(async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      })
      setStream(mediaStream)
      setMode('camera')
    } catch (error) {
      console.error('Camera error:', error)
      toast({
        variant: 'destructive',
        title: 'Camera Error',
        description: 'Could not access camera. Please check permissions or use file upload.',
      })
    }
  }, [toast])

  const stopCamera = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop())
      setStream(null)
    }
  }, [stream])

  const capturePhoto = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return

    const video = videoRef.current
    const canvas = canvasRef.current
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight

    const ctx = canvas.getContext('2d')
    if (ctx) {
      ctx.drawImage(video, 0, 0)
      const dataUrl = canvas.toDataURL('image/jpeg', 0.85)
      setImageData(dataUrl)
      stopCamera()
      setMode('preview')
    }
  }, [stopCamera])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast({
        variant: 'destructive',
        title: 'Invalid file',
        description: 'Please select an image file.',
      })
      return
    }

    // Compress and convert to data URL
    const reader = new FileReader()
    reader.onload = (event) => {
      const img = new Image()
      img.onload = () => {
        const canvas = document.createElement('canvas')
        const maxSize = 1920

        let { width, height } = img
        if (width > maxSize || height > maxSize) {
          if (width > height) {
            height = (height / width) * maxSize
            width = maxSize
          } else {
            width = (width / height) * maxSize
            height = maxSize
          }
        }

        canvas.width = width
        canvas.height = height
        const ctx = canvas.getContext('2d')
        if (ctx) {
          ctx.drawImage(img, 0, 0, width, height)
          const dataUrl = canvas.toDataURL('image/jpeg', 0.85)
          setImageData(dataUrl)
          setMode('preview')
        }
      }
      img.src = event.target?.result as string
    }
    reader.readAsDataURL(file)
  }, [toast])

  const resetCapture = useCallback(() => {
    setImageData(null)
    setMode('select')
  }, [])

  const uploadAndAnalyze = async () => {
    if (!imageData || !token || !profileId) return

    setUploading(true)

    try {
      // Convert data URL to blob
      const response = await fetch(imageData)
      const blob = await response.blob()

      const formData = new FormData()
      formData.append('image', blob, 'homework.jpg')
      formData.append('child_profile_id', profileId)

      const question = await api.upload<Question>('/questions/analyze', formData, { token })
      navigate(`/analysis/${question.id}`)
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Failed to analyze image'
      toast({
        variant: 'destructive',
        title: 'Analysis Error',
        description: message,
      })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="max-w-lg mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate('/')}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-xl font-display font-bold">Capture Homework</h1>
          <p className="text-sm text-muted-foreground">
            Take a photo or upload an image
          </p>
        </div>
      </div>

      {/* Hidden elements */}
      <canvas ref={canvasRef} className="hidden" />
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileSelect}
      />

      {/* Mode: Select */}
      {mode === 'select' && (
        <Card className="glass">
          <CardContent className="p-8 space-y-4">
            <Button
              className="w-full h-32 flex-col gap-3"
              onClick={startCamera}
            >
              <Camera className="w-10 h-10" />
              <span>Take Photo</span>
            </Button>

            <Button
              variant="outline"
              className="w-full h-32 flex-col gap-3"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="w-10 h-10" />
              <span>Upload Image</span>
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Mode: Camera */}
      {mode === 'camera' && (
        <div className="relative rounded-xl overflow-hidden bg-black">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            className="w-full aspect-[3/4] object-cover"
          />

          <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/80 to-transparent">
            <div className="flex items-center justify-center gap-4">
              <Button
                variant="outline"
                size="icon"
                className="h-12 w-12 rounded-full bg-white/10 border-white/20 text-white"
                onClick={() => {
                  stopCamera()
                  setMode('select')
                }}
              >
                <X className="w-6 h-6" />
              </Button>

              <Button
                size="icon"
                className="h-16 w-16 rounded-full bg-white text-black hover:bg-white/90"
                onClick={capturePhoto}
              >
                <div className="w-12 h-12 rounded-full border-4 border-black/50" />
              </Button>

              <div className="w-12" /> {/* Spacer for symmetry */}
            </div>
          </div>
        </div>
      )}

      {/* Mode: Preview */}
      {mode === 'preview' && imageData && (
        <div className="space-y-4">
          <div className="relative rounded-xl overflow-hidden">
            <img
              src={imageData}
              alt="Captured homework"
              className="w-full"
            />
          </div>

          <div className="flex gap-3">
            <Button
              variant="outline"
              className="flex-1"
              onClick={resetCapture}
              disabled={uploading}
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              Retake
            </Button>

            <Button
              className="flex-1"
              onClick={uploadAndAnalyze}
              disabled={uploading}
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Analyzing...
                </>
              ) : (
                'Analyze'
              )}
            </Button>
          </div>
        </div>
      )}

      {/* Tips */}
      {mode === 'select' && (
        <div className="text-sm text-muted-foreground space-y-2">
          <p className="font-medium text-foreground">Tips for best results:</p>
          <ul className="list-disc list-inside space-y-1">
            <li>Ensure good lighting</li>
            <li>Keep the text in focus</li>
            <li>Capture the entire question</li>
            <li>Avoid shadows and glare</li>
          </ul>
        </div>
      )}
    </div>
  )
}
