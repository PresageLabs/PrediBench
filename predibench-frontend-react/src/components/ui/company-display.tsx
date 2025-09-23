import { getCompanyInfo } from '../../utils/company-mapping'

interface CompanyDisplayProps {
  modelName: string
  className?: string
}

export function CompanyDisplay({ modelName, className = "" }: CompanyDisplayProps) {
  const companyInfo = getCompanyInfo(modelName)

  if (!companyInfo) {
    return (
      <span className={`text-muted-foreground text-sm ${className}`}>
        Unknown
      </span>
    )
  }

  // Special handling for baseline models - show descriptive text instead of logos
  if (modelName === 'Market baseline') {
    return (
      <span className={`text-muted-foreground text-sm ${className}`}>
        Bet on the top-rated outcome
      </span>
    )
  }

  if (modelName === 'Random Baseline') {
    return (
      <span className={`text-muted-foreground text-sm ${className}`}>
        Bet at random
      </span>
    )
  }

  const needsColorInversion = companyInfo.name === 'OpenAI' || companyInfo.name === 'Anthropic' || companyInfo.name === 'xAI'

  return (
    <div className={`flex items-center gap-1.5 ${className}`}>
      <img
        src={companyInfo.logo}
        alt={`${companyInfo.name} logo`}
        className={`w-4 h-4 object-contain ${needsColorInversion ? 'dark:brightness-0 dark:invert' : ''
          }`}
        onError={(e) => {
          // Hide image if it fails to load
          (e.target as HTMLImageElement).style.display = 'none'
        }}
      />
      <span className="text-sm font-normal text-muted-foreground">{companyInfo.name}</span>
    </div>
  )
}