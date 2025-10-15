import anthropicLogo from '../assets/logos/anthropic.svg'
import deepseekLogo from '../assets/logos/deepseek.svg'
import googleLogo from '../assets/logos/google.svg'
import metaLogo from '../assets/logos/meta.svg'
import moonshotLogo from '../assets/logos/moonshot.svg'
import openaiLogo from '../assets/logos/openai.svg'
import perplexityLogo from '../assets/logos/perplexity.svg'
import presageLogo from '../assets/logos/presage.svg'
import qwenLogo from '../assets/logos/qwen.svg'
import xaiLogo from '../assets/logos/xai.svg'

interface CompanyInfo {
  name: string
  logo: string
  logoType: 'svg' | 'png'
  description?: string
}

const companyMapping: Record<string, CompanyInfo> = {
  // OpenAI models
  'GPT-5': { name: 'OpenAI', logo: openaiLogo, logoType: 'svg' },
  'GPT-5 Mini': { name: 'OpenAI', logo: openaiLogo, logoType: 'svg' },
  'GPT-4.1': { name: 'OpenAI', logo: openaiLogo, logoType: 'svg' },
  'GPT-OSS 120B': { name: 'OpenAI', logo: openaiLogo, logoType: 'svg' },

  // Anthropic models
  'Claude Opus 4.1': { name: 'Anthropic', logo: anthropicLogo, logoType: 'png' },
  'Claude Sonnet 4': { name: 'Anthropic', logo: anthropicLogo, logoType: 'png' },

  // Meta models
  'Llama 4 Scout': { name: 'Meta', logo: metaLogo, logoType: 'svg' },
  'Llama 3.3 70B': { name: 'Meta', logo: metaLogo, logoType: 'svg' },
  'Llama 4 Maverick': { name: 'Meta', logo: metaLogo, logoType: 'svg' },

  // Google models
  'Gemini 2.5 Flash': { name: 'Google', logo: googleLogo, logoType: 'svg' },
  'Gemini 2.5 Pro': { name: 'Google', logo: googleLogo, logoType: 'svg' },

  // Alibaba models
  'Qwen3 Coder 480B': { name: 'Alibaba', logo: qwenLogo, logoType: 'svg' },
  'Qwen3 235B': { name: 'Alibaba', logo: qwenLogo, logoType: 'svg' },

  // DeepSeek models - using moonshot as placeholder until we get proper logo
  'DeepSeek R1': { name: 'DeepSeek', logo: deepseekLogo, logoType: 'png' },
  'DeepSeek V3.1': { name: 'DeepSeek', logo: deepseekLogo, logoType: 'png' },

  // xAI models
  'Grok 4': { name: 'xAI', logo: xaiLogo, logoType: 'png' },

  // Perplexity models - using moonshot as placeholder until we get proper logo
  'Sonar Deep Research': { name: 'Perplexity', logo: perplexityLogo, logoType: 'png' },

  // Baseline models
  'Random Baseline': { name: 'Random predictions', logo: moonshotLogo, logoType: 'png', description: 'Makes random trading decisions' },
  'Market baseline': { name: 'Volume-weighted', logo: moonshotLogo, logoType: 'png', description: 'Follows market volume proportions' },

  // Aggregate models
  'Presage Aggregate': { name: 'Presage Labs', logo: presageLogo, logoType: 'svg', description: 'Median aggregate of top 4 models' }
}

export function getCompanyInfo(modelName: string): CompanyInfo | null {
  // First try exact match
  if (companyMapping[modelName]) {
    return companyMapping[modelName]
  }

  // Try partial matches for model families
  if (modelName.includes('GPT')) {
    return { name: 'OpenAI', logo: openaiLogo, logoType: 'svg' }
  }
  if (modelName.includes('Claude')) {
    return { name: 'Anthropic', logo: anthropicLogo, logoType: 'png' }
  }
  if (modelName.includes('Llama')) {
    return { name: 'Meta', logo: metaLogo, logoType: 'svg' }
  }
  if (modelName.includes('Gemini')) {
    return { name: 'Google', logo: googleLogo, logoType: 'svg' }
  }
  if (modelName.includes('Qwen')) {
    return { name: 'Alibaba', logo: qwenLogo, logoType: 'svg' }
  }
  if (modelName.includes('DeepSeek')) {
    return { name: 'DeepSeek', logo: moonshotLogo, logoType: 'png' }
  }
  if (modelName.includes('Grok')) {
    return { name: 'xAI', logo: moonshotLogo, logoType: 'png' }
  }
  if (modelName.includes('Sonar')) {
    return { name: 'Perplexity', logo: moonshotLogo, logoType: 'png' }
  }
  if (modelName.includes('Baseline') || modelName.includes('baseline')) {
    return { name: 'Baseline', logo: moonshotLogo, logoType: 'png', description: 'Benchmark model' }
  }
  if (modelName.includes('Presage') || modelName.includes('presage')) {
    return { name: 'Presage Labs', logo: presageLogo, logoType: 'svg', description: 'Median aggregate of top models' }
  }

  return null
}