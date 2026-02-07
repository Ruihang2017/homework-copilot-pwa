import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { api, ApiError } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useToast } from '@/hooks/use-toast'
import type { ModelInfo, User } from '@/types'
import { ArrowLeft, Loader2, Cpu, Check } from 'lucide-react'

const TIER_LABELS: Record<string, string> = {
  premium: 'Premium',
  standard: 'Standard',
  budget: 'Budget',
}

const TIER_COLORS: Record<string, string> = {
  premium: 'text-amber-500',
  standard: 'text-blue-500',
  budget: 'text-green-500',
}

export default function Settings() {
  const [models, setModels] = useState<ModelInfo[]>([])
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [saving, setSaving] = useState(false)
  const [loadingModels, setLoadingModels] = useState(true)
  const { user, token, updateUser } = useAuth()
  const navigate = useNavigate()
  const { toast } = useToast()

  useEffect(() => {
    fetchModels()
  }, [token])

  useEffect(() => {
    if (user?.preferred_model) {
      setSelectedModel(user.preferred_model)
    }
  }, [user])

  const fetchModels = async () => {
    if (!token) return
    try {
      const data = await api.get<ModelInfo[]>('/models', { token })
      setModels(data)
    } catch (error) {
      console.error('Failed to fetch models:', error)
    } finally {
      setLoadingModels(false)
    }
  }

  const handleSave = async () => {
    if (!token || !selectedModel) return
    setSaving(true)

    try {
      const updated = await api.patch<User>('/auth/me', { preferred_model: selectedModel }, {
        token,
      })
      updateUser({ preferred_model: updated.preferred_model })
      toast({
        title: 'Settings saved',
        description: `Default model set to ${models.find(m => m.id === selectedModel)?.display_name || selectedModel}`,
      })
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Failed to save settings'
      toast({
        variant: 'destructive',
        title: 'Error',
        description: message,
      })
    } finally {
      setSaving(false)
    }
  }

  const hasChanges = selectedModel !== (user?.preferred_model || '')

  return (
    <div className="max-w-lg mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate('/')}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-xl font-display font-bold">Settings</h1>
          <p className="text-sm text-muted-foreground">
            Configure your AI preferences
          </p>
        </div>
      </div>

      {/* Account Info */}
      <Card className="glass">
        <CardHeader>
          <CardTitle className="text-base">Account</CardTitle>
          <CardDescription>{user?.email}</CardDescription>
        </CardHeader>
      </Card>

      {/* Default AI Model */}
      <Card className="glass">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Cpu className="w-4 h-4" />
            Default AI Model
          </CardTitle>
          <CardDescription>
            Choose which model to use for homework analysis. You can also override per question.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {loadingModels ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <>
              <div className="space-y-2">
                <Label htmlFor="model">Model</Label>
                <Select value={selectedModel} onValueChange={setSelectedModel}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a model" />
                  </SelectTrigger>
                  <SelectContent>
                    {models.map((model) => (
                      <SelectItem key={model.id} value={model.id}>
                        <span className="flex items-center gap-2">
                          {model.display_name}
                          <span className={`text-xs ${TIER_COLORS[model.tier] || 'text-muted-foreground'}`}>
                            {TIER_LABELS[model.tier] || model.tier}
                          </span>
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Model info cards */}
              <div className="space-y-2">
                {models.map((model) => (
                  <div
                    key={model.id}
                    className={`p-3 rounded-lg border text-sm transition-colors ${
                      selectedModel === model.id
                        ? 'border-primary bg-primary/5'
                        : 'border-transparent bg-muted/50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{model.display_name}</span>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs ${TIER_COLORS[model.tier] || ''}`}>
                          {TIER_LABELS[model.tier] || model.tier}
                        </span>
                        {selectedModel === model.id && (
                          <Check className="w-4 h-4 text-primary" />
                        )}
                      </div>
                    </div>
                    {model.description && (
                      <p className="text-xs text-muted-foreground mt-1">{model.description}</p>
                    )}
                  </div>
                ))}
              </div>

              <Button
                className="w-full"
                onClick={handleSave}
                disabled={saving || !hasChanges}
              >
                {saving ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : hasChanges ? (
                  'Save Changes'
                ) : (
                  'No Changes'
                )}
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
