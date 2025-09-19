import { useEffect, useMemo, useRef, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './card'
// Use the installed plotly.js bundle (no CDN)
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-expect-error - no types provided by the bundle
import Plotly from 'plotly.js/dist/plotly'
import { useTheme } from '../../contexts/ThemeContext'

type PlotlyFigure = {
  data: any
  layout?: any
  config?: any
}

function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binaryString = atob(base64)
  const len = binaryString.length
  const bytes = new Uint8Array(len)
  for (let i = 0; i < len; i++) bytes[i] = binaryString.charCodeAt(i)
  return bytes.buffer
}

function decodeTypedArrays(obj: any): any {
  // Recursively walk the object and replace { dtype, bdata } with typed arrays
  if (obj && typeof obj === 'object') {
    // Plotly Python to_json may store arrays as {dtype: 'f8', bdata: '<base64>'}
    if ('dtype' in obj && 'bdata' in obj && typeof obj.bdata === 'string') {
      const buf = base64ToArrayBuffer(obj.bdata)
      switch (obj.dtype) {
        case 'f8':
        case 'float64':
          return new Float64Array(buf)
        case 'f4':
        case 'float32':
          return new Float32Array(buf)
        case 'i4':
        case 'int32':
          return new Int32Array(buf)
        case 'i2':
        case 'int16':
          return new Int16Array(buf)
        case 'i1':
        case 'int8':
          return new Int8Array(buf)
        case 'u4':
        case 'uint32':
          return new Uint32Array(buf)
        case 'u2':
        case 'uint16':
          return new Uint16Array(buf)
        case 'u1':
        case 'uint8':
          return new Uint8Array(buf)
        default:
          return obj // unknown dtype, leave as-is
      }
    }
    if (Array.isArray(obj)) return obj.map(decodeTypedArrays)
    const out: Record<string, any> = {}
    for (const [k, v] of Object.entries(obj)) out[k] = decodeTypedArrays(v)
    return out
  }
  return obj
}

export function PlotlyCard({ caption, path }: { caption: string; path: string }) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const { theme } = useTheme()

  const url = useMemo(() => {
    const clean = path.startsWith('/') ? path : `/${path}`
    return clean
  }, [path])

  const getCardBg = (): string => {
    // Prefer reading from the card container to inherit CSS variables
    const el = containerRef.current || document.documentElement
    const styles = getComputedStyle(el)
    // CSS variables store H S L (and optional / alpha). Build hsl(var)
    const card = styles.getPropertyValue('--card').trim()
    return card ? `hsl(${card})` : (theme === 'dark' ? '#000' : '#fff')
  }

  useEffect(() => {
    let cancelled = false
    let plotted = false

    async function run() {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(url)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const raw = (await res.json()) as PlotlyFigure
        const fig = decodeTypedArrays(raw)
        if (!containerRef.current) return

        const config = {
          responsive: true,
          displaylogo: false,
          modeBarButtonsToRemove: ['toImage'],
          ...(fig.config || {}),
        }

        const themedLayout = { ...(fig.layout || {}), paper_bgcolor: getCardBg(), plot_bgcolor: getCardBg() }
        await Plotly.newPlot(containerRef.current, fig.data, themedLayout, config)
        if (cancelled) return
        plotted = true
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to render chart')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    run()

    return () => {
      cancelled = true
      if (plotted && containerRef.current) {
        try { Plotly.purge(containerRef.current) } catch { /* no-op */ }
      }
    }
  }, [url])

  // Update background dynamically without re-fetching data
  useEffect(() => {
    if (!containerRef.current) return
    const bg = getCardBg()
    try {
      Plotly.relayout(containerRef.current, {
        paper_bgcolor: bg,
        plot_bgcolor: bg,
      })
    } catch {
      // ignore
    }
  }, [theme])

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle>{caption}</CardTitle>
      </CardHeader>
      <CardContent>
        {error ? (
          <div className="text-red-500 text-sm">{error}</div>
        ) : (
          <div
            ref={containerRef}
            className="w-full"
            style={{ minHeight: 360 }}
          />
        )}
        {loading && !error && (
          <div className="text-sm text-muted-foreground mt-2">Loading chart…</div>
        )}
      </CardContent>
    </Card>
  )
}

export default PlotlyCard
