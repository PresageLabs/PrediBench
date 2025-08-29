import { ArrowRight } from 'lucide-react'
import { type ReactNode } from 'react'

interface RedirectButtonProps {
  href?: string
  onClick?: () => void
  children: ReactNode
  icon?: ReactNode
  className?: string
}

export function RedirectButton({ 
  href, 
  onClick, 
  children, 
  icon = <ArrowRight className="h-4 w-4" />,
  className = ''
}: RedirectButtonProps) {
  const baseClasses = "inline-flex items-center space-x-2 text-foreground hover:shadow-lg transition-all duration-200 font-medium border border-border rounded-lg px-6 py-3 hover:border-primary/50"
  
  if (href) {
    return (
      <a
        href={href}
        className={`${baseClasses} ${className}`}
      >
        <span>{children}</span>
        {icon}
      </a>
    )
  }

  return (
    <button
      onClick={onClick}
      className={`${baseClasses} ${className}`}
    >
      <span>{children}</span>
      {icon}
    </button>
  )
}