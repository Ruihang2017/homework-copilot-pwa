import { useMemo } from 'react'
import type { DiagramSpec, DiagramElement, DiagramLabel } from '@/types'
import { cn } from '@/lib/utils'

interface DiagramRendererProps {
  diagram: DiagramSpec
  activeStep: number | null
  className?: string
}

type SvgTextAnchor = 'start' | 'middle' | 'end' | 'inherit'
type SvgDominantBaseline =
  | 'auto'
  | 'middle'
  | 'hanging'
  | 'alphabetic'
  | 'central'
  | 'text-before-edge'
  | 'text-after-edge'
  | 'inherit'

// Color palette for kid-friendly diagrams
const COLORS = {
  active: {
    fill: 'rgba(34, 197, 94, 0.2)', // green-500/20
    stroke: '#22c55e', // green-500
  },
  inactive: {
    fill: 'rgba(148, 163, 184, 0.1)', // slate-400/10
    stroke: '#64748b', // slate-500
  },
  auxiliary: {
    stroke: '#f97316', // orange-500
  },
  label: {
    active: '#22c55e',
    inactive: '#94a3b8',
  },
}

function isElementActive(element: DiagramElement, activeStep: number | null): boolean {
  if (activeStep === null) return true // Show all when no step selected
  return element.highlightSteps.includes(activeStep)
}

function getLabelPosition(
  label: DiagramLabel,
  element: DiagramElement
): { x: number; y: number; anchor: SvgTextAnchor; baseline: SvgDominantBaseline } {
  // Default position calculation based on element type and label position
  let x = 0
  let y = 0
  let anchor: SvgTextAnchor = 'middle'
  let baseline: SvgDominantBaseline = 'middle'

  if (element.type === 'line' && element.points && element.points.length >= 2) {
    const [p1, p2] = element.points
    x = (p1[0] + p2[0]) / 2
    y = (p1[1] + p2[1]) / 2
  } else if (element.center) {
    x = element.center[0]
    y = element.center[1]
  } else if (element.points && element.points.length > 0) {
    // For polygons, find centroid
    const sumX = element.points.reduce((sum, p) => sum + p[0], 0)
    const sumY = element.points.reduce((sum, p) => sum + p[1], 0)
    x = sumX / element.points.length
    y = sumY / element.points.length
  }

  const offset = 15
  switch (label.position) {
    case 'top':
      y -= offset
      baseline = 'auto'
      break
    case 'bottom':
      y += offset
      baseline = 'hanging'
      break
    case 'left':
      x -= offset
      anchor = 'end'
      break
    case 'right':
      x += offset
      anchor = 'start'
      break
  }

  return { x, y, anchor, baseline }
}

function renderPolygon(element: DiagramElement, isActive: boolean) {
  if (!element.points || element.points.length < 3) return null

  const pointsStr = element.points.map((p) => `${p[0]},${p[1]}`).join(' ')
  const colors = isActive ? COLORS.active : COLORS.inactive

  return (
    <polygon
      key={element.id}
      points={pointsStr}
      fill={colors.fill}
      stroke={colors.stroke}
      strokeWidth={isActive ? 3 : 2}
      className="transition-all duration-300"
    />
  )
}

function renderCircle(element: DiagramElement, isActive: boolean) {
  if (!element.center || !element.radius) return null

  const colors = isActive ? COLORS.active : COLORS.inactive

  return (
    <circle
      key={element.id}
      cx={element.center[0]}
      cy={element.center[1]}
      r={element.radius}
      fill={colors.fill}
      stroke={colors.stroke}
      strokeWidth={isActive ? 3 : 2}
      className="transition-all duration-300"
    />
  )
}

function renderArc(element: DiagramElement, isActive: boolean) {
  if (!element.center || !element.radius || element.startAngle === undefined || element.endAngle === undefined) {
    return null
  }

  const [cx, cy] = element.center
  const r = element.radius
  const startAngle = (element.startAngle * Math.PI) / 180
  const endAngle = (element.endAngle * Math.PI) / 180

  // Calculate start and end points
  const startX = cx + r * Math.cos(startAngle)
  const startY = cy + r * Math.sin(startAngle)
  const endX = cx + r * Math.cos(endAngle)
  const endY = cy + r * Math.sin(endAngle)

  // Determine if arc is greater than 180 degrees
  const angleDiff = endAngle - startAngle
  const largeArcFlag = Math.abs(angleDiff) > Math.PI ? 1 : 0
  const sweepFlag = angleDiff > 0 ? 1 : 0

  const pathD = `M ${startX} ${startY} A ${r} ${r} 0 ${largeArcFlag} ${sweepFlag} ${endX} ${endY}`

  const colors = isActive ? COLORS.active : COLORS.inactive

  return (
    <path
      key={element.id}
      d={pathD}
      fill="none"
      stroke={colors.stroke}
      strokeWidth={isActive ? 3 : 2}
      className="transition-all duration-300"
    />
  )
}

function renderLine(element: DiagramElement, isActive: boolean) {
  if (!element.points || element.points.length < 2) return null

  const [p1, p2] = element.points
  const colors = isActive ? COLORS.active : COLORS.inactive

  return (
    <line
      key={element.id}
      x1={p1[0]}
      y1={p1[1]}
      x2={p2[0]}
      y2={p2[1]}
      stroke={element.style === 'dashed' ? COLORS.auxiliary.stroke : colors.stroke}
      strokeWidth={isActive ? 2.5 : 1.5}
      strokeDasharray={element.style === 'dashed' ? '8,4' : undefined}
      className="transition-all duration-300"
    />
  )
}

function renderPoint(element: DiagramElement, isActive: boolean) {
  if (!element.position) return null

  const colors = isActive ? COLORS.active : COLORS.inactive

  return (
    <circle
      key={element.id}
      cx={element.position[0]}
      cy={element.position[1]}
      r={isActive ? 6 : 4}
      fill={colors.stroke}
      className="transition-all duration-300"
    />
  )
}

function renderAngle(element: DiagramElement, isActive: boolean) {
  if (!element.vertex || !element.rays || element.rays.length < 2) return null

  const [vx, vy] = element.vertex
  const [r1, r2] = element.rays
  const colors = isActive ? COLORS.active : COLORS.inactive

  // Calculate angles
  const angle1 = Math.atan2(r1[1] - vy, r1[0] - vx)
  const angle2 = Math.atan2(r2[1] - vy, r2[0] - vx)

  // Arc radius for angle marker
  const arcRadius = 20

  // Calculate arc path
  const startX = vx + arcRadius * Math.cos(angle1)
  const startY = vy + arcRadius * Math.sin(angle1)
  const endX = vx + arcRadius * Math.cos(angle2)
  const endY = vy + arcRadius * Math.sin(angle2)

  // Determine sweep direction
  let angleDiff = angle2 - angle1
  if (angleDiff < 0) angleDiff += 2 * Math.PI
  const largeArcFlag = angleDiff > Math.PI ? 1 : 0

  const pathD = `M ${startX} ${startY} A ${arcRadius} ${arcRadius} 0 ${largeArcFlag} 1 ${endX} ${endY}`

  return (
    <path
      key={element.id}
      d={pathD}
      fill="none"
      stroke={colors.stroke}
      strokeWidth={isActive ? 2 : 1.5}
      className="transition-all duration-300"
    />
  )
}

function renderLabel(label: DiagramLabel, element: DiagramElement, isActive: boolean, index: number) {
  const pos = getLabelPosition(label, element)
  const color = isActive ? COLORS.label.active : COLORS.label.inactive

  return (
    <text
      key={`${element.id}-label-${index}`}
      x={pos.x}
      y={pos.y}
      textAnchor={pos.anchor}
      dominantBaseline={pos.baseline}
      fill={color}
      fontSize="14"
      fontWeight={isActive ? '600' : '400'}
      className="transition-all duration-300 select-none"
      style={{ fontFamily: 'system-ui, sans-serif' }}
    >
      {label.text}
    </text>
  )
}

function renderStandaloneLabel(element: DiagramElement, isActive: boolean) {
  if (!element.position || !element.label) return null

  const color = isActive ? COLORS.label.active : COLORS.label.inactive

  return (
    <text
      key={element.id}
      x={element.position[0]}
      y={element.position[1]}
      textAnchor="middle"
      dominantBaseline="middle"
      fill={color}
      fontSize="14"
      fontWeight={isActive ? '600' : '400'}
      className="transition-all duration-300 select-none"
      style={{ fontFamily: 'system-ui, sans-serif' }}
    >
      {element.label.text}
    </text>
  )
}

export default function DiagramRenderer({ diagram, activeStep, className }: DiagramRendererProps) {
  const { viewBox, elements } = diagram

  // Separate elements into layers for proper rendering order
  const { shapes, lines, points, labels } = useMemo(() => {
    const shapes: DiagramElement[] = []
    const lines: DiagramElement[] = []
    const points: DiagramElement[] = []
    const labels: DiagramElement[] = []

    for (const el of elements) {
      switch (el.type) {
        case 'polygon':
        case 'circle':
        case 'arc':
          shapes.push(el)
          break
        case 'line':
        case 'angle':
          lines.push(el)
          break
        case 'point':
          points.push(el)
          break
        case 'label':
          labels.push(el)
          break
      }
    }

    return { shapes, lines, points, labels }
  }, [elements])

  const svgViewBox = `0 0 ${viewBox.width} ${viewBox.height}`

  return (
    <div className={cn('w-full', className)}>
      <svg
        viewBox={svgViewBox}
        className="w-full h-auto max-h-[400px]"
        style={{ backgroundColor: 'rgba(15, 23, 42, 0.5)' }} // slate-900/50
      >
        {/* Render shapes first (background) */}
        {shapes.map((el) => {
          const isActive = isElementActive(el, activeStep)
          switch (el.type) {
            case 'polygon':
              return renderPolygon(el, isActive)
            case 'circle':
              return renderCircle(el, isActive)
            case 'arc':
              return renderArc(el, isActive)
            default:
              return null
          }
        })}

        {/* Render lines */}
        {lines.map((el) => {
          const isActive = isElementActive(el, activeStep)
          switch (el.type) {
            case 'line':
              return renderLine(el, isActive)
            case 'angle':
              return renderAngle(el, isActive)
            default:
              return null
          }
        })}

        {/* Render points */}
        {points.map((el) => renderPoint(el, isElementActive(el, activeStep)))}

        {/* Render standalone labels */}
        {labels.map((el) => renderStandaloneLabel(el, isElementActive(el, activeStep)))}

        {/* Render element labels on top */}
        {elements.map((el) => {
          const isActive = isElementActive(el, activeStep)

          // Single label
          if (el.label && el.type !== 'label') {
            return renderLabel(el.label, el, isActive, 0)
          }

          // Multiple labels
          if (el.labels) {
            return el.labels.map((label, idx) => renderLabel(label, el, isActive, idx))
          }

          return null
        })}
      </svg>
    </div>
  )
}

