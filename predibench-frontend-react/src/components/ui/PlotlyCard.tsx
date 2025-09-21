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

export function PlotlyCard({ caption, path, secondPath }: { caption: string; path: string; secondPath?: string }) {
  const containerRef1 = useRef<HTMLDivElement | null>(null)
  const containerRef2 = useRef<HTMLDivElement | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const { theme } = useTheme()

  const url1 = useMemo(() => (path.startsWith('/') ? path : `/${path}`), [path])
  const url2 = useMemo(() => (secondPath ? (secondPath.startsWith('/') ? secondPath : `/${secondPath}`) : undefined), [secondPath])

  const getCardBg = (): string => {
    // Read from root where CSS variables are set according to theme
    const styles = getComputedStyle(document.documentElement)
    const card = styles.getPropertyValue('--card').trim()
    return card ? `hsl(${card})` : (theme === 'dark' ? '#000' : '#fff')
  }

  // Simple foreground rule per request: white in dark mode, otherwise standard dark gray
  const getSimpleFg = (): string => (theme === 'dark' ? '#ffffff' : '#111827')

  useEffect(() => {
    let cancelled = false
    let plotted1 = false
    let plotted2 = false
    let ro1: ResizeObserver | null = null
    let ro2: ResizeObserver | null = null

    async function run() {
      setLoading(true)
      setError(null)
      try {
        const [res1, res2] = await Promise.all([
          fetch(url1),
          url2 ? fetch(url2) : Promise.resolve(undefined as unknown as Response),
        ])
        if (!res1.ok) throw new Error(`HTTP ${res1.status} on ${url1}`)
        const raw1 = (await res1.json()) as PlotlyFigure
        const fig1 = decodeTypedArrays(raw1)
        const fig2 = res2 ? decodeTypedArrays(await res2.json()) as PlotlyFigure : undefined
        if (!containerRef1.current) return

        const config = {
          responsive: true,
          displaylogo: false,
          modeBarButtonsToRemove: ['toImage'],
          ...(fig1.config || {}),
        }

        const bg = getCardBg()
        const fg = getSimpleFg()
        const dims1 = (() => {
          const el = containerRef1.current!
          const w = Math.max(0, Math.round(el.getBoundingClientRect().width))
          const h = Math.max(320, Math.round(w * 0.6))
          return { w, h }
        })()
        const themedLayout1 = {
          ...(fig1.layout || {}),
          paper_bgcolor: bg,
          plot_bgcolor: bg,
          font: { ...((fig1.layout || {}).font || {}), color: fg },
          width: dims1.w,
          height: dims1.h,
          title: (fig1.layout || {}).title ? { ...((fig1.layout || {}).title), font: { ...(((fig1.layout || {}).title || {}).font || {}), color: fg } } : (fig1.layout || {}).title,
          legend: (fig1.layout || {}).legend ? { ...((fig1.layout || {}).legend), font: { ...(((fig1.layout || {}).legend || {}).font || {}), color: fg } } : (fig1.layout || {}).legend,
          xaxis: {
            ...((fig1.layout || {}).xaxis || {}),
            linecolor: fg,
            tickcolor: fg,
            tickfont: { ...((((fig1.layout || {}).xaxis || {}).tickfont || {})), color: fg },
            title: (((fig1.layout || {}).xaxis || {}).title)
              ? { ...(((fig1.layout || {}).xaxis || {}).title), font: { ...(((((fig1.layout || {}).xaxis || {}).title || {}).font || {})), color: fg } }
              : ((fig1.layout || {}).xaxis || {}).title,
          },
          yaxis: {
            ...((fig1.layout || {}).yaxis || {}),
            linecolor: fg,
            tickcolor: fg,
            tickfont: { ...((((fig1.layout || {}).yaxis || {}).tickfont || {})), color: fg },
            title: (((fig1.layout || {}).yaxis || {}).title)
              ? { ...(((fig1.layout || {}).yaxis || {}).title), font: { ...(((((fig1.layout || {}).yaxis || {}).title || {}).font || {})), color: fg } }
              : ((fig1.layout || {}).yaxis || {}).title,
          },
        }
        await Plotly.newPlot(containerRef1.current, fig1.data, themedLayout1, config)
        plotted1 = true

        if (containerRef2.current && fig2) {
          const dims2 = (() => {
            const el = containerRef2.current!
            const w = Math.max(0, Math.round(el.getBoundingClientRect().width))
            const h = Math.max(320, Math.round(w * 0.6))
            return { w, h }
          })()
          const themedLayout2 = {
            ...(fig2.layout || {}),
            paper_bgcolor: bg,
            plot_bgcolor: bg,
            font: { ...((fig2.layout || {}).font || {}), color: fg },
            width: dims2.w,
            height: dims2.h,
            title: (fig2.layout || {}).title ? { ...((fig2.layout || {}).title), font: { ...(((fig2.layout || {}).title || {}).font || {}), color: fg } } : (fig2.layout || {}).title,
            legend: (fig2.layout || {}).legend ? { ...((fig2.layout || {}).legend), font: { ...(((fig2.layout || {}).legend || {}).font || {}), color: fg } } : (fig2.layout || {}).legend,
            xaxis: {
              ...((fig2.layout || {}).xaxis || {}),
              linecolor: fg,
              tickcolor: fg,
              tickfont: { ...((((fig2.layout || {}).xaxis || {}).tickfont || {})), color: fg },
              title: (((fig2.layout || {}).xaxis || {}).title)
                ? { ...(((fig2.layout || {}).xaxis || {}).title), font: { ...(((((fig2.layout || {}).xaxis || {}).title || {}).font || {})), color: fg } }
                : ((fig2.layout || {}).xaxis || {}).title,
            },
            yaxis: {
              ...((fig2.layout || {}).yaxis || {}),
              linecolor: fg,
              tickcolor: fg,
              tickfont: { ...((((fig2.layout || {}).yaxis || {}).tickfont || {})), color: fg },
              title: (((fig2.layout || {}).yaxis || {}).title)
                ? { ...(((fig2.layout || {}).yaxis || {}).title), font: { ...(((((fig2.layout || {}).yaxis || {}).title || {}).font || {})), color: fg } }
                : ((fig2.layout || {}).yaxis || {}).title,
            },
          }
          await Plotly.newPlot(containerRef2.current, fig2.data, themedLayout2, { ...config, ...(fig2.config || {}) })
          plotted2 = true
        }
        if (cancelled) return
        // Setup resize observers to keep plots within card bounds
        if (containerRef1.current) {
          ro1 = new ResizeObserver(() => {
            try {
              const el = containerRef1.current!
              const w = Math.max(0, Math.round(el.getBoundingClientRect().width))
              const h = Math.max(320, Math.round(w * 0.6))
              Plotly.relayout(el, { width: w, height: h })
            } catch {}
          })
          ro1.observe(containerRef1.current)
        }
        if (containerRef2.current) {
          ro2 = new ResizeObserver(() => {
            try {
              const el = containerRef2.current!
              const w = Math.max(0, Math.round(el.getBoundingClientRect().width))
              const h = Math.max(320, Math.round(w * 0.6))
              Plotly.relayout(el, { width: w, height: h })
            } catch {}
          })
          ro2.observe(containerRef2.current)
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to render chart')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    run()

    return () => {
      cancelled = true
      try { ro1?.disconnect() } catch {}
      try { ro2?.disconnect() } catch {}
      if (plotted1 && containerRef1.current) {
        try { Plotly.purge(containerRef1.current) } catch { /* no-op */ }
      }
      if (plotted2 && containerRef2.current) {
        try { Plotly.purge(containerRef2.current) } catch { /* no-op */ }
      }
    }
  }, [url1, url2])

  // Update background and foreground dynamically without re-fetching data
  useEffect(() => {
    // Defer to next frame so CSS variables have updated after theme class change
    let raf = 0
    const relayout = () => {
      const bg = getCardBg()
      const fg = getSimpleFg()
      try {
        if (containerRef1.current) {
          Plotly.relayout(containerRef1.current, {
            paper_bgcolor: bg,
            plot_bgcolor: bg,
            'font.color': fg,
            'title.font.color': fg,
            'legend.font.color': fg,
            'xaxis.linecolor': fg,
            'xaxis.tickcolor': fg,
            'xaxis.tickfont.color': fg,
            'xaxis.title.font.color': fg,
            'yaxis.linecolor': fg,
            'yaxis.tickcolor': fg,
            'yaxis.tickfont.color': fg,
            'yaxis.title.font.color': fg,
          })
        }
        if (containerRef2.current) {
          Plotly.relayout(containerRef2.current, {
            paper_bgcolor: bg,
            plot_bgcolor: bg,
            'font.color': fg,
            'title.font.color': fg,
            'legend.font.color': fg,
            'xaxis.linecolor': fg,
            'xaxis.tickcolor': fg,
            'xaxis.tickfont.color': fg,
            'xaxis.title.font.color': fg,
            'yaxis.linecolor': fg,
            'yaxis.tickcolor': fg,
            'yaxis.tickfont.color': fg,
            'yaxis.title.font.color': fg,
          })
        }
      } catch {
        // ignore
      }
    }
    raf = window.requestAnimationFrame(relayout)
    return () => window.cancelAnimationFrame(raf)
  }, [theme])

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle>{caption}</CardTitle>
      </CardHeader>
      <CardContent>
        {error && <div className="text-red-500 text-sm mb-2">{error}</div>}
        {secondPath ? (
          <div className="grid md:grid-cols-2 gap-6">
            <div ref={containerRef1} className="w-full overflow-hidden" style={{ minHeight: 360 }} />
            <div ref={containerRef2} className="w-full overflow-hidden" style={{ minHeight: 360 }} />
          </div>
        ) : (
          <div ref={containerRef1} className="w-full overflow-hidden" style={{ minHeight: 360 }} />
        )}
        {loading && !error && (
          <div className="text-sm text-muted-foreground mt-2">Loading chart…</div>
        )}
      </CardContent>
    </Card>
  )
}

export default PlotlyCard
