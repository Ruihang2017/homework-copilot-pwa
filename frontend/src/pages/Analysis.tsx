import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { api, ApiError } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { useToast } from '@/hooks/use-toast'
import type { Question, FeedbackEventType } from '@/types'
import {
  ArrowLeft,
  Loader2,
  Lightbulb,
  AlertTriangle,
  Target,
  ThumbsUp,
  ThumbsDown,
  Minus,
  Check,
  HelpCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const FEEDBACK_OPTIONS: { type: FeedbackEventType; label: string; icon: React.ReactNode }[] = [
  { type: 'TOO_SIMPLE', label: 'Too Simple', icon: <ThumbsDown className="w-4 h-4" /> },
  { type: 'JUST_RIGHT', label: 'Just Right', icon: <Check className="w-4 h-4" /> },
  { type: 'TOO_ADVANCED', label: 'Too Hard', icon: <ThumbsUp className="w-4 h-4 rotate-180" /> },
  { type: 'UNDERSTOOD', label: 'Got It!', icon: <Lightbulb className="w-4 h-4" /> },
  { type: 'STILL_CONFUSED', label: 'Still Confused', icon: <HelpCircle className="w-4 h-4" /> },
]

export default function Analysis() {
  const { questionId } = useParams<{ questionId: string }>()
  const [question, setQuestion] = useState<Question | null>(null)
  const [loading, setLoading] = useState(true)
  const [submittingFeedback, setSubmittingFeedback] = useState<FeedbackEventType | null>(null)
  const [expandedHint, setExpandedHint] = useState<string>('hint-1')
  const { token } = useAuth()
  const navigate = useNavigate()
  const { toast } = useToast()

  useEffect(() => {
    fetchQuestion()
  }, [questionId, token])

  const fetchQuestion = async () => {
    if (!token || !questionId) return

    try {
      const data = await api.get<Question>(`/questions/${questionId}`, { token })
      setQuestion(data)
    } catch (error) {
      console.error('Failed to fetch question:', error)
      toast({
        variant: 'destructive',
        title: 'Error',
        description: 'Failed to load analysis results.',
      })
      navigate('/')
    } finally {
      setLoading(false)
    }
  }

  const submitFeedback = async (eventType: FeedbackEventType) => {
    if (!token || !questionId) return

    setSubmittingFeedback(eventType)

    try {
      await api.post(`/questions/${questionId}/feedback`, { event_type: eventType }, { token })
      toast({
        title: 'Feedback submitted',
        description: 'Thank you! This helps improve future explanations.',
      })
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Failed to submit feedback'
      toast({
        variant: 'destructive',
        title: 'Error',
        description: message,
      })
    } finally {
      setSubmittingFeedback(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-4">
          <Loader2 className="w-10 h-10 animate-spin text-primary mx-auto" />
          <p className="text-muted-foreground">Analyzing homework...</p>
        </div>
      </div>
    )
  }

  if (!question) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-muted-foreground">Question not found</p>
      </div>
    )
  }

  const { response_json: analysis } = question

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate('/')}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-xl font-display font-bold">Analysis Results</h1>
          <p className="text-sm text-muted-foreground">
            {analysis.subject} • {analysis.topic.split('.').pop()?.replace(/_/g, ' ')}
          </p>
        </div>
      </div>

      {/* Parent Context */}
      <Card className="glass border-primary/30">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2 text-primary">
            <Target className="w-5 h-5" />
            <CardTitle className="text-lg">What This Question Tests</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-sm text-muted-foreground mb-2">Key Skills:</p>
            <div className="flex flex-wrap gap-2">
              {analysis.parent_context.what_it_tests.map((skill, i) => (
                <span
                  key={i}
                  className="px-3 py-1 rounded-full bg-primary/10 text-primary text-sm"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-1">Key Idea:</p>
            <p className="font-medium">{analysis.parent_context.key_idea}</p>
          </div>
        </CardContent>
      </Card>

      {/* Progressive Hints */}
      <Card className="glass">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2 text-accent">
            <Lightbulb className="w-5 h-5" />
            <CardTitle className="text-lg">Progressive Hints</CardTitle>
          </div>
          <CardDescription>
            Reveal hints one at a time to guide without giving away the answer
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Accordion
            type="single"
            collapsible
            value={expandedHint}
            onValueChange={setExpandedHint}
          >
            {analysis.hints.map((hint, index) => (
              <AccordionItem key={hint.stage} value={`hint-${hint.stage}`}>
                <AccordionTrigger className="hover:no-underline">
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        'w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold',
                        index === 0
                          ? 'bg-accent text-accent-foreground'
                          : 'bg-muted text-muted-foreground'
                      )}
                    >
                      {hint.stage}
                    </div>
                    <span>Hint {hint.stage}</span>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="pl-11">
                  <p className="text-foreground">{hint.text}</p>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </CardContent>
      </Card>

      {/* Common Mistakes */}
      {analysis.common_mistakes.length > 0 && (
        <Card className="glass border-destructive/30">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="w-5 h-5" />
              <CardTitle className="text-lg">Common Mistakes to Watch</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {analysis.common_mistakes.map((mistake, i) => (
                <li key={i} className="flex items-start gap-2">
                  <Minus className="w-4 h-4 mt-1 text-destructive shrink-0" />
                  <span>{mistake}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Feedback */}
      <Card className="glass">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">How was this explanation?</CardTitle>
          <CardDescription>
            Your feedback helps personalize future explanations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {FEEDBACK_OPTIONS.map((option) => (
              <Button
                key={option.type}
                variant="outline"
                size="sm"
                onClick={() => submitFeedback(option.type)}
                disabled={submittingFeedback !== null}
                className={cn(
                  'flex items-center gap-2',
                  option.type === 'JUST_RIGHT' && 'border-accent hover:bg-accent/10',
                  option.type === 'UNDERSTOOD' && 'border-primary hover:bg-primary/10',
                  option.type === 'TOO_ADVANCED' && 'border-destructive hover:bg-destructive/10',
                  option.type === 'STILL_CONFUSED' && 'border-yellow-500 hover:bg-yellow-500/10'
                )}
              >
                {submittingFeedback === option.type ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  option.icon
                )}
                {option.label}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Action buttons */}
      <div className="flex gap-3 pb-6">
        <Button variant="outline" className="flex-1" onClick={() => navigate('/')}>
          Back to Profiles
        </Button>
        <Button
          className="flex-1"
          onClick={() => navigate(`/capture/${question.child_profile_id}`)}
        >
          Analyze Another
        </Button>
      </div>
    </div>
  )
}
