import MarkdownRenderer from '../lib/MarkdownRenderer'
// Import the Markdown file as raw text via Vite
// Edit this file to update the About page content.
// Location: src/content/about.md
// eslint-disable-next-line import/no-relative-packages
import aboutContent from '../content/about.md?raw'

export function AboutPage() {
  return (
    <div className="container mx-auto px-6 py-12 max-w-3xl">
      <MarkdownRenderer content={aboutContent} />
    </div>
  )
}
