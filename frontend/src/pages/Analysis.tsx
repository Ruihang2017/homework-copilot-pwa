import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { api, ApiError } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useToast } from '@/hooks/use-toast'
import DiagramRenderer from '@/components/DiagramRenderer'
import type { Question, FeedbackEventType } from '@/types'
import {
  ArrowLeft,
  Loader2,
  Lightbulb,
  AlertTriangle,
  Target,
  ThumbsUp,
  ThumbsDown,
  Check,
  HelpCircle,
  BookOpen,
  GraduationCap,
  Shapes,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import MathText from '@/components/MathText'

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
  const [activeStep, setActiveStep] = useState<number | null>(1) // Start with step 1 active
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
  const hasDiagram = analysis.diagram && analysis.diagram.elements.length > 0

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
            <p className="font-medium"><MathText>{analysis.parent_context.key_idea}</MathText></p>
          </div>
        </CardContent>
      </Card>

      {/* Interactive Diagram (if present) */}
      {hasDiagram && (
        <Card className="glass border-accent/30">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2 text-accent">
              <Shapes className="w-5 h-5" />
              <CardTitle className="text-lg">Interactive Diagram</CardTitle>
            </div>
            <CardDescription>
              Click on steps below to highlight related parts
            </CardDescription>
          </CardHeader>
          <CardContent>
            <DiagramRenderer
              diagram={analysis.diagram!}
              activeStep={activeStep}
              className="rounded-lg overflow-hidden"
            />
            {/* Step selector buttons */}
            <div className="flex flex-wrap gap-2 mt-4 justify-center">
              <Button
                variant={activeStep === null ? 'default' : 'outline'}
                size="sm"
                onClick={() => setActiveStep(null)}
                className="text-xs"
              >
                Show All
              </Button>
              {analysis.solution_steps.map((step) => (
                <Button
                  key={step.step}
                  variant={activeStep === step.step ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setActiveStep(step.step)}
                  className="text-xs"
                >
                  Step {step.step}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step-by-Step Solution */}
      <Card className="glass border-accent/30">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2 text-accent">
            <BookOpen className="w-5 h-5" />
            <CardTitle className="text-lg">Step-by-Step Solution</CardTitle>
          </div>
          <CardDescription>
            {hasDiagram ? 'Click a step to highlight it in the diagram above' : 'Follow these steps to solve the problem'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {analysis.solution_steps.map((step, index) => (
              <div
                key={step.step}
                className={cn(
                  'relative pl-10 cursor-pointer rounded-lg transition-all duration-200',
                  hasDiagram && 'hover:bg-accent/5 -mx-2 px-2 py-2',
                  hasDiagram && activeStep === step.step && 'bg-accent/10'
                )}
                onClick={() => hasDiagram && setActiveStep(step.step)}
              >
                {/* Step number */}
                <div
                  className={cn(
                    'absolute left-0 top-0 w-7 h-7 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-200',
                    hasDiagram && activeStep === step.step
                      ? 'bg-accent text-accent-foreground scale-110'
                      : 'bg-accent/70 text-accent-foreground'
                  )}
                  style={hasDiagram ? { left: '8px', top: '8px' } : undefined}
                >
                  {step.step}
                </div>
                {/* Connector line */}
                {index < analysis.solution_steps.length - 1 && (
                  <div
                    className={cn(
                      'absolute w-0.5 bg-accent/30',
                      hasDiagram
                        ? 'left-[21px] top-[36px] h-[calc(100%-12px)]'
                        : 'left-[13px] top-7 h-[calc(100%+0.5rem)]'
                    )}
                  />
                )}
                {/* Content */}
                <div className={hasDiagram ? 'pb-2 pl-2' : 'pb-4'}>
                  <h4 className="font-semibold text-foreground mb-1"><MathText>{step.title}</MathText></h4>
                  <p className="text-muted-foreground whitespace-pre-wrap"><MathText>{step.explanation}</MathText></p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Teaching Tips */}
      {analysis.teaching_tips && (
        <Card className="glass border-primary/30">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2 text-primary">
              <GraduationCap className="w-5 h-5" />
              <CardTitle className="text-lg">Teaching Tips for Parents</CardTitle>
            </div>
            <CardDescription>
              How to explain this concept to your child
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-start gap-3">
              <Lightbulb className="w-4 h-4 mt-1 text-primary shrink-0" />
              <p className="text-foreground"><MathText>{analysis.teaching_tips}</MathText></p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Common Mistakes */}
      {analysis.common_mistakes && (
        <Card className="glass border-destructive/30">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="w-5 h-5" />
              <CardTitle className="text-lg">Common Mistakes to Watch</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-4 h-4 mt-1 text-destructive shrink-0" />
              <p className="text-foreground"><MathText>{analysis.common_mistakes}</MathText></p>
            </div>
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
