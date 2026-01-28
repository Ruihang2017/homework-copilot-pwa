interface LogoProps {
  className?: string
  size?: number
}

export default function Logo({ className = '', size = 32 }: LogoProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 100 100"
      width={size}
      height={size}
      className={className}
    >
      <defs>
        <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#8b5cf6" />
          <stop offset="100%" stopColor="#14b8a6" />
        </linearGradient>
      </defs>
      <rect width="100" height="100" rx="20" fill="url(#logoGrad)" />
      <path
        d="M50 25 L70 35 L70 50 L50 60 L30 50 L30 35 Z"
        fill="none"
        stroke="white"
        strokeWidth="4"
      />
      <path d="M50 60 L50 75" stroke="white" strokeWidth="4" />
      <path d="M70 42 L70 62 L75 65" stroke="white" strokeWidth="3" />
      <circle cx="75" cy="68" r="5" fill="white" />
    </svg>
  )
}
