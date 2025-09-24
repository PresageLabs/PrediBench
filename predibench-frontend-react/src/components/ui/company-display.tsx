import { getCompanyInfo } from '../../utils/company-mapping'

interface CompanyDisplayProps {
  modelName: string
  className?: string
}

export function CompanyDisplay({ modelName, className = "" }: CompanyDisplayProps) {
  const companyInfo = getCompanyInfo(modelName)

  if (!companyInfo) {
    return (
      <div className={`flex items-center gap-1.5 h-4 ${className}`}>
        <span className="text-sm font-normal text-muted-foreground">Unknown</span>
      </div>
    )
  }

  // Special handling for baseline models - show descriptive text instead of logos
  if (modelName === 'Market baseline') {
    return (
      <div className={`flex items-center gap-1.5 h-4 ${className}`}>
        <span className="text-sm font-normal text-muted-foreground">
          Bet on the top-rated outcome
        </span>
      </div>
    )
  }

  if (modelName === 'Random Baseline') {
    return (
      <div className={`flex items-center gap-1.5 h-4 ${className}`}>
        <span className="text-sm font-normal text-muted-foreground">
          Bet at random
        </span>
      </div>
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