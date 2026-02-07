// Auth types
export interface User {
  id: string
  email: string
  preferred_model: string | null
  created_at: string
}

// Model types
export interface ModelInfo {
  id: string
  display_name: string
  tier: string
  supports_vision: boolean
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterCredentials extends LoginCredentials {
  confirm_password: string
}

// Profile types
export interface ChildProfile {
  id: string
  user_id: string
  nickname: string | null
  grade: string
  created_at: string
  global_state?: GlobalState
}

export interface GlobalState {
  child_profile_id: string
  grade_alignment: string
  curriculum: string
  language: string
  default_explanation_style: string
  no_direct_answer: boolean
}

export interface TopicState {
  id: string
  child_profile_id: string
  subject: string
  topic_key: string
  mastery: number
  confidence: number
  preferred_abstraction: 'more_concrete' | 'balanced' | 'more_abstract'
  preferred_hint_depth: 'light_hints' | 'moderate' | 'step_by_step'
  updated_at: string
}

// Question types
export interface SolutionStep {
  step: number
  title: string
  explanation: string
}

export interface TeachingTip {
  tip: string
}

export interface ParentContext {
  what_it_tests: string[]
  key_idea: string
}

// Diagram types for geometry questions
export interface DiagramLabel {
  text: string
  position: 'top' | 'bottom' | 'left' | 'right' | 'center'
}

export interface DiagramViewBox {
  width: number
  height: number
  padding: number
}

export type DiagramElementType = 'polygon' | 'circle' | 'arc' | 'line' | 'point' | 'angle' | 'label'

export interface DiagramElement {
  id: string
  type: DiagramElementType
  highlightSteps: number[]
  // Polygon/Line: array of [x, y] coordinates
  points?: [number, number][]
  // Circle/Arc: center point and radius
  center?: [number, number]
  radius?: number
  // Arc specific: angles in degrees
  startAngle?: number
  endAngle?: number
  // Point specific: single position
  position?: [number, number]
  // Angle marker: vertex and two ray endpoints
  vertex?: [number, number]
  rays?: [number, number][]
  // Styling
  style?: 'solid' | 'dashed'
  // Labels
  label?: DiagramLabel
  labels?: DiagramLabel[]
}

export interface DiagramSpec {
  viewBox: DiagramViewBox
  elements: DiagramElement[]
}

export interface AnalysisResponse {
  subject: string
  topic: string
  parent_context: ParentContext
  solution_steps: SolutionStep[]
  teaching_tips: TeachingTip[]
  common_mistakes: string[]
  diagram?: DiagramSpec | null
}

export interface Question {
  id: string
  child_profile_id: string
  topic_key: string
  image_url: string
  response_json: AnalysisResponse
  created_at: string
}

// Feedback types
export type FeedbackEventType =
  | 'TOO_SIMPLE'
  | 'JUST_RIGHT'
  | 'TOO_ADVANCED'
  | 'UNDERSTOOD'
  | 'STILL_CONFUSED'

export interface FeedbackEvent {
  id: string
  question_id: string
  child_profile_id: string
  topic_key: string
  event_type: FeedbackEventType
  created_at: string
}

// Create/Update types
export interface CreateChildProfile {
  nickname?: string
  grade: string
}

export interface UpdateChildProfile {
  nickname?: string
  grade?: string
}

export interface CreateFeedback {
  event_type: FeedbackEventType
}
