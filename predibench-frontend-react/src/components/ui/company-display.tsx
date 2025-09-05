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
      <span className="text-xs font-medium">{companyInfo.name}</span>
    </div>
  )
}