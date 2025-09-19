import { useEffect } from 'react'

// Lightweight hook to (re)apply anchor-js to all h1–h3 when deps change
export function useAnchorJS(deps: unknown[] = []) {
  useEffect(() => {
    let anchors: any | null = null

    const run = async () => {
      try {
        const mod: any = await import('anchor-js')
        const AnchorJS = mod?.default ?? mod
        anchors = new AnchorJS()
        anchors.options = {
          placement: 'right',
          visible: 'hover',
          // Use a small inline SVG link icon that inherits currentColor
          icon:
            '<svg aria-hidden="true" viewBox="0 0 24 24" width="16" height="16" style="display:inline-block;vertical-align:middle">\n' +
            '  <path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"\n' +
            '    d="M10.5 13.5l-2 2a4 4 0 1 1-5.657-5.657l3-3a4 4 0 0 1 5.657 0m3 3l2-2a4 4 0 1 1 5.657 5.657l-3 3a4 4 0 0 1-5.657 0"/>\n' +
            '</svg>',
        }
        // Remove previous to avoid duplicates, then add
        anchors.remove('h1, h2, h3')
        anchors.add('h1, h2, h3')
      } catch (e) {
        // eslint-disable-next-line no-console
        console.warn('anchor-js not available', e)
      }
    }

    run()

    return () => {
      try {
        anchors?.remove?.('h1, h2, h3')
      } catch {}
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}

export default useAnchorJS
