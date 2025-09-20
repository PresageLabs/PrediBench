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
          icon: '#',
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
