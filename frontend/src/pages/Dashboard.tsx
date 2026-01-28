import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { api, ApiError } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useToast } from '@/hooks/use-toast'
import type { ChildProfile, CreateChildProfile } from '@/types'
import { Plus, Camera, User, Loader2, Trash2 } from 'lucide-react'

const GRADES = [
  { value: 'year_1', label: 'Year 1' },
  { value: 'year_2', label: 'Year 2' },
  { value: 'year_3', label: 'Year 3' },
  { value: 'year_4', label: 'Year 4' },
  { value: 'year_5', label: 'Year 5' },
  { value: 'year_6', label: 'Year 6' },
  { value: 'year_7', label: 'Year 7' },
  { value: 'year_8', label: 'Year 8' },
]

export default function Dashboard() {
  const [profiles, setProfiles] = useState<ChildProfile[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [newProfile, setNewProfile] = useState<CreateChildProfile>({
    nickname: '',
    grade: 'year_4',
  })
  const { token } = useAuth()
  const navigate = useNavigate()
  const { toast } = useToast()

  useEffect(() => {
    fetchProfiles()
  }, [token])

  const fetchProfiles = async () => {
    if (!token) return
    try {
      const data = await api.get<ChildProfile[]>('/profiles', { token })
      setProfiles(data)
    } catch (error) {
      console.error('Failed to fetch profiles:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateProfile = async () => {
    if (!token || !newProfile.grade) return
    setCreating(true)

    try {
      const profile = await api.post<ChildProfile>('/profiles', newProfile, { token })
      setProfiles([...profiles, profile])
      setDialogOpen(false)
      setNewProfile({ nickname: '', grade: 'year_4' })
      toast({
        title: 'Profile created',
        description: 'You can now start analyzing homework!',
      })
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Failed to create profile'
      toast({
        variant: 'destructive',
        title: 'Error',
        description: message,
      })
    } finally {
      setCreating(false)
    }
  }

  const handleDeleteProfile = async (profileId: string) => {
    if (!token) return

    try {
      await api.delete(`/profiles/${profileId}`, { token })
      setProfiles(profiles.filter((p) => p.id !== profileId))
      toast({
        title: 'Profile deleted',
        description: 'The child profile has been removed.',
      })
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Failed to delete profile'
      toast({
        variant: 'destructive',
        title: 'Error',
        description: message,
      })
    }
  }

  const getGradeLabel = (grade: string) => {
    return GRADES.find((g) => g.value === grade)?.label || grade
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold">Child Profiles</h1>
          <p className="text-muted-foreground mt-1">
            Select a child to analyze their homework
          </p>
        </div>

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Add Child
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Child Profile</DialogTitle>
              <DialogDescription>
                Create a profile for your child to personalize homework assistance.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="nickname">Nickname (optional)</Label>
                <Input
                  id="nickname"
                  placeholder="e.g., Emma"
                  value={newProfile.nickname}
                  onChange={(e) =>
                    setNewProfile({ ...newProfile, nickname: e.target.value })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="grade">Grade Level</Label>
                <Select
                  value={newProfile.grade}
                  onValueChange={(value) =>
                    setNewProfile({ ...newProfile, grade: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select grade" />
                  </SelectTrigger>
                  <SelectContent>
                    {GRADES.map((grade) => (
                      <SelectItem key={grade.value} value={grade.value}>
                        {grade.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDialogOpen(false)}
                disabled={creating}
              >
                Cancel
              </Button>
              <Button onClick={handleCreateProfile} disabled={creating}>
                {creating ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Profile'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Profile cards */}
      {profiles.length === 0 ? (
        <Card className="glass">
          <CardContent className="flex flex-col items-center justify-center py-16 space-y-4">
            <div className="w-20 h-20 rounded-full bg-muted flex items-center justify-center">
              <User className="w-10 h-10 text-muted-foreground" />
            </div>
            <div className="text-center">
              <h3 className="font-semibold text-lg">No profiles yet</h3>
              <p className="text-muted-foreground mt-1">
                Add your first child profile to get started
              </p>
            </div>
            <Button onClick={() => setDialogOpen(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Add Child
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {profiles.map((profile, index) => (
            <Card
              key={profile.id}
              className="glass hover:border-primary/50 transition-colors cursor-pointer group"
              style={{ animationDelay: `${index * 100}ms` }}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center text-white font-display font-semibold text-lg">
                    {profile.nickname?.[0]?.toUpperCase() || 'C'}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="opacity-0 group-hover:opacity-100 transition-opacity text-destructive hover:text-destructive"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDeleteProfile(profile.id)
                    }}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
                <CardTitle className="mt-3">
                  {profile.nickname || 'Child'}
                </CardTitle>
                <CardDescription>{getGradeLabel(profile.grade)}</CardDescription>
              </CardHeader>
              <CardContent>
                <Button
                  className="w-full"
                  onClick={() => navigate(`/capture/${profile.id}`)}
                >
                  <Camera className="w-4 h-4 mr-2" />
                  Analyze Homework
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
