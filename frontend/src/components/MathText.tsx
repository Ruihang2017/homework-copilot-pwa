import { useMemo } from 'react'
import katex from 'katex'
import 'katex/dist/katex.min.css'

interface MathTextProps {
  children: string
  className?: string
}

/**
 * MathText renders text with inline LaTeX math expressions.
 *
 * Supports:
 *   - LaTeX delimiters: $...$ for inline math
 *   - Escaped dollars \$ are preserved as literal $
 *   - Falls back to plain text if KaTeX fails to parse
 */

// Regex to split text into segments of plain text and $...$ math
// Handles: $\frac{3}{4}$, $x^2$, etc.
// Does NOT match escaped \$
const MATH_REGEX = /(?<!\\)\$(.+?)(?<!\\)\$/g

function renderLatex(latex: string): string {
  try {
    return katex.renderToString(latex, {
      throwOnError: false,
      displayMode: false,
      trust: false,
      strict: false,
    })
  } catch {
    // If KaTeX can't parse it, return the raw text
    return latex
  }
}

export default function MathText({ children, className = '' }: MathTextProps) {
  const html = useMemo(() => {
    if (!children) return ''

    const text = children

    // If no $ delimiters found, try to auto-detect common math patterns
    if (!text.includes('$')) {
      return autoFormatMath(text)
    }

    // Split by $...$ and render math segments
    const parts: string[] = []
    let lastIndex = 0

    const regex = new RegExp(MATH_REGEX, 'g')
    let match: RegExpExecArray | null

    while ((match = regex.exec(text)) !== null) {
      // Add plain text before match
      if (match.index > lastIndex) {
        parts.push(escapeHtml(text.slice(lastIndex, match.index)))
      }
      // Render math
      parts.push(renderLatex(match[1]))
      lastIndex = regex.lastIndex
    }

    // Add remaining plain text
    if (lastIndex < text.length) {
      parts.push(escapeHtml(text.slice(lastIndex)))
    }

    return parts.join('')
  }, [children])

  return (
    <span
      className={className}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}

/**
 * Auto-detect and format common math patterns when no $ delimiters are used.
 * Converts patterns like:
 *   - π → rendered as KaTeX
 *   - √18 → \sqrt{18}
 *   - 3^2 → 3^{2}
 *   - fractions like 3/4 in context
 */
function autoFormatMath(text: string): string {
  let result = escapeHtml(text)

  // Replace common Unicode math symbols with KaTeX rendered versions
  const mathPatterns: [RegExp, (match: string, ...groups: string[]) => string][] = [
    // Greek letters
    [/π/g, () => renderLatex('\\pi')],
    [/α/g, () => renderLatex('\\alpha')],
    [/β/g, () => renderLatex('\\beta')],
    [/θ/g, () => renderLatex('\\theta')],

    // Square root: √(number)
    [/√\(([^)]+)\)/g, (_m, inner) => renderLatex(`\\sqrt{${inner}}`)],
    [/√(\d+)/g, (_m, num) => renderLatex(`\\sqrt{${num}}`)],

    // Fractions in form a/b where both are numbers (standalone, not in URLs)
    [/(?<!\w)(\d+)\/(\d+)(?!\w)/g, (_m, a, b) => renderLatex(`\\frac{${a}}{${b}}`)],

    // Exponents: x^2, x^{n+1}, 3^2
    [/(\w)\^{([^}]+)}/g, (_m, base, exp) => renderLatex(`${base}^{${exp}}`)],
    [/(\w)\^(\d+)/g, (_m, base, exp) => renderLatex(`${base}^{${exp}}`)],

    // ± symbol
    [/±/g, () => renderLatex('\\pm')],
    // ≤ ≥ ≠
    [/≤/g, () => renderLatex('\\leq')],
    [/≥/g, () => renderLatex('\\geq')],
    [/≠/g, () => renderLatex('\\neq')],
    // ∈
    [/∈/g, () => renderLatex('\\in')],
    // ∞
    [/∞/g, () => renderLatex('\\infty')],
  ]

  for (const [pattern, replacer] of mathPatterns) {
    result = result.replace(pattern, replacer as (...args: string[]) => string)
  }

  return result
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}
