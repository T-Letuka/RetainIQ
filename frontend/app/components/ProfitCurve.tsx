'use client'

import {
  useEffect, useRef, useState, useCallback, forwardRef, useImperativeHandle,
} from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from 'recharts'
import { TrendingUp } from 'lucide-react'

const CLV          = 800
const INTERVENTION = 50
const MISSED_CHURN = 600

export interface ScoredCustomer {
  churn_probability: number
  churned: number
}

interface CurvePoint {
  threshold:  number
  net_profit: number
  tp: number; fp: number; fn: number; tn: number
  precision:  number
  recall:     number
  targeted:   number
}

export interface ProfitCurveHandle {
  exportPng: () => Promise<string | null>
}

interface Props {
  customers: ScoredCustomer[]
}

function buildCurve(customers: ScoredCustomer[]): CurvePoint[] {
  const n = customers.length
  if (n === 0) return []
  return Array.from({ length: 101 }, (_, i) => {
    const t = i / 100
    let tp = 0, fp = 0, fn = 0, tn = 0
    for (const c of customers) {
      const pred = c.churn_probability >= t ? 1 : 0
      if (pred === 1 && c.churned === 1) tp++
      else if (pred === 1 && c.churned === 0) fp++
      else if (pred === 0 && c.churned === 1) fn++
      else tn++
    }
    return {
      threshold:  Math.round(t * 100) / 100,
      net_profit: Math.round((tp * CLV) - (fp * INTERVENTION) - (fn * MISSED_CHURN)),
      tp, fp, fn, tn,
      precision:  tp + fp > 0 ? Math.round((tp / (tp + fp)) * 1000) / 1000 : 0,
      recall:     tp + fn > 0 ? Math.round((tp / (tp + fn)) * 1000) / 1000 : 0,
      targeted:   Math.round(((tp + fp) / n) * 100),
    }
  })
}

function formatRand(v: number) {
  return `R${Math.abs(v).toLocaleString('en-ZA')}`
}

function CurveTooltip({ active, payload }: { active?: boolean; payload?: any[] }) {
  if (!active || !payload?.length) return null
  const d: CurvePoint = payload[0].payload
  return (
    <div className="bg-ink border border-smoke rounded-lg p-3 text-xs font-mono shadow-xl">
      <p className="text-clay mb-2">Threshold  {d.threshold.toFixed(2)}</p>
      <p className={`text-base font-medium mb-2 ${d.net_profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
        {d.net_profit >= 0 ? '+' : ''}{formatRand(d.net_profit)}
      </p>
      <div className="space-y-0.5 text-ash border-t border-smoke pt-2 mt-1">
        <p>TP {d.tp}  ·  FP {d.fp}</p>
        <p>FN {d.fn}  ·  TN {d.tn}</p>
        <p className="mt-1">Precision {(d.precision * 100).toFixed(1)}%</p>
        <p>Recall    {(d.recall    * 100).toFixed(1)}%</p>
        <p>Targeting {d.targeted}% of base</p>
      </div>
    </div>
  )
}

const ProfitCurve = forwardRef<ProfitCurveHandle, Props>(({ customers }, ref) => {
  const [curve,   setCurve  ] = useState<CurvePoint[]>([])
  const [optimal, setOptimal] = useState<CurvePoint | null>(null)
  const [hovered, setHovered] = useState<CurvePoint | null>(null)
  const chartRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!customers.length) return
    const pts = buildCurve(customers)
    setCurve(pts)
    const best = pts.reduce((a, b) => b.net_profit > a.net_profit ? b : a)
    setOptimal(best)
    setHovered(best)
  }, [customers])

  const exportPng = useCallback(async (): Promise<string | null> => {
    if (!curve.length || !optimal) return null
    const W = 560, H = 240
    const canvas = document.createElement('canvas')
    canvas.width = W * 2; canvas.height = H * 2
    const ctx = canvas.getContext('2d')!
    ctx.scale(2, 2)
    ctx.fillStyle = '#162127'; ctx.fillRect(0, 0, W, H)

    const profits = curve.map(p => p.net_profit)
    const minP = Math.min(...profits), maxP = Math.max(...profits)
    const range = maxP - minP || 1
    const toY = (v: number) => 30 + ((maxP - v) / range) * (H - 50)
    const toX = (t: number) => 50 + t * (W - 70)

    ctx.strokeStyle = '#1E2D35'; ctx.lineWidth = 0.5
    for (let i = 0; i <= 4; i++) {
      const y = 30 + (i / 4) * (H - 50)
      ctx.beginPath(); ctx.moveTo(50, y); ctx.lineTo(W - 20, y); ctx.stroke()
    }

    if (minP < 0 && maxP > 0) {
      ctx.strokeStyle = '#8A9BA3'; ctx.lineWidth = 0.8; ctx.setLineDash([3, 3])
      ctx.beginPath(); ctx.moveTo(50, toY(0)); ctx.lineTo(W - 20, toY(0)); ctx.stroke()
      ctx.setLineDash([])
    }

    const grad = ctx.createLinearGradient(0, 30, 0, H - 20)
    grad.addColorStop(0, 'rgba(207,157,123,0.25)')
    grad.addColorStop(1, 'rgba(207,157,123,0.02)')
    ctx.beginPath()
    ctx.moveTo(toX(curve[0].threshold), toY(curve[0].net_profit))
    for (const p of curve) ctx.lineTo(toX(p.threshold), toY(p.net_profit))
    ctx.lineTo(toX(1), H - 20); ctx.lineTo(toX(0), H - 20); ctx.closePath()
    ctx.fillStyle = grad; ctx.fill()

    ctx.beginPath(); ctx.strokeStyle = '#CF9D7B'; ctx.lineWidth = 2
    curve.forEach((p, i) => {
      i === 0 ? ctx.moveTo(toX(p.threshold), toY(p.net_profit))
              : ctx.lineTo(toX(p.threshold), toY(p.net_profit))
    })
    ctx.stroke()

    const ox = toX(optimal.threshold), oy = toY(optimal.net_profit)
    ctx.beginPath(); ctx.arc(ox, oy, 5, 0, Math.PI * 2)
    ctx.fillStyle = '#CF9D7B'; ctx.fill()
    ctx.strokeStyle = '#162127'; ctx.lineWidth = 2; ctx.stroke()
    ctx.font = '10px monospace'; ctx.fillStyle = '#CF9D7B'
    ctx.fillText(`Optimal: ${optimal.threshold.toFixed(2)}`, ox + 8, oy - 6)
    ctx.fillText(`+${formatRand(optimal.net_profit)}`, ox + 8, oy + 6)
    ctx.font = '11px monospace'; ctx.fillStyle = '#EDF2F4'
    ctx.fillText('Profit Curve — Net profit by churn threshold', 50, 18)

    return canvas.toDataURL('image/png')
  }, [curve, optimal])

  useImperativeHandle(ref, () => ({ exportPng }), [exportPng])

  if (!curve.length) return null

  const display = hovered ?? optimal

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <p className="font-mono text-xs text-ash uppercase tracking-widest mb-1">Profit curve</p>
          <p className="text-xs text-smoke">
            TP ×R{CLV} − FP ×R{INTERVENTION} − FN ×R{MISSED_CHURN}
          </p>
        </div>
        <TrendingUp size={16} className="text-clay shrink-0 ml-4" />
      </div>

      <div ref={chartRef} style={{ width: '100%', height: 220, minHeight: '220px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={curve}
            margin={{ top: 10, right: 10, left: 10, bottom: 0 }}
            onMouseMove={(e: any) => {
              if (e?.activePayload?.[0]?.payload) setHovered(e.activePayload[0].payload)
            }}
            onMouseLeave={() => setHovered(optimal)}
          >
            <defs>
              <linearGradient id="profitGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#CF9D7B" stopOpacity={0.20} />
                <stop offset="95%" stopColor="#CF9D7B" stopOpacity={0.01} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#1E2D35" strokeWidth={0.5} vertical={false} />
            <XAxis
              dataKey="threshold"
              tick={{ fill: '#8A9BA3', fontSize: 10, fontFamily: 'monospace' }}
              tickLine={false} axisLine={false}
              tickFormatter={(v: number) => v.toFixed(1)}
              ticks={[0, 0.2, 0.4, 0.6, 0.8, 1.0]}
            />
            <YAxis
              tick={{ fill: '#8A9BA3', fontSize: 10, fontFamily: 'monospace' }}
              tickLine={false} axisLine={false}
              tickFormatter={(v: number) =>
                v >= 0 ? `R${(v / 1000).toFixed(0)}k` : `-R${(Math.abs(v) / 1000).toFixed(0)}k`
              }
              width={44}
            />
            <Tooltip content={<CurveTooltip />} />
            <ReferenceLine y={0} stroke="#8A9BA3" strokeWidth={0.8} strokeDasharray="4 4" />
            {optimal && (
              <ReferenceLine
                x={optimal.threshold}
                stroke="#CF9D7B"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                label={{
                  value: `↑ ${optimal.threshold.toFixed(2)}`,
                  position: 'top',
                  fill: '#CF9D7B',
                  fontSize: 10,
                  fontFamily: 'monospace',
                }}
              />
            )}
            <Area
              type="monotone"
              dataKey="net_profit"
              stroke="#CF9D7B"
              strokeWidth={2}
              fill="url(#profitGrad)"
              dot={false}
              activeDot={{ r: 4, fill: '#CF9D7B', stroke: '#162127', strokeWidth: 2 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {display && (
        <div className="mt-5 grid grid-cols-4 gap-3">
          {[
            { label: 'Threshold',  value: display.threshold.toFixed(2), accent: 'text-clay' },
            { label: 'Net profit', value: `${display.net_profit >= 0 ? '+' : ''}${formatRand(display.net_profit)}`, accent: display.net_profit >= 0 ? 'text-green-400' : 'text-red-400' },
            { label: 'Precision',  value: `${(display.precision * 100).toFixed(1)}%`, accent: 'text-mist' },
            { label: 'Recall',     value: `${(display.recall * 100).toFixed(1)}%`, accent: 'text-mist' },
          ].map(({ label, value, accent }) => (
            <div key={label} className="rounded-lg bg-smoke/40 p-3 text-center">
              <p className={`font-mono text-sm font-medium ${accent}`}>{value}</p>
              <p className="font-mono text-[10px] text-ash mt-1 uppercase tracking-wider">{label}</p>
            </div>
          ))}
        </div>
      )}

      {optimal && (
        <div className="mt-4 rounded-lg border border-clay/25 bg-clay/5 px-4 py-3 flex items-center justify-between">
          <div>
            <p className="font-mono text-xs text-clay mb-0.5">Optimal threshold</p>
            <p className="text-xs text-ash">
              Target customers ≥{' '}
              <span className="text-mist font-mono">{optimal.threshold.toFixed(2)}</span>
              {' '}— intervene on{' '}
              <span className="text-mist font-mono">{optimal.targeted}%</span> of base
            </p>
          </div>
          <p className="font-mono text-lg text-green-400 ml-4 shrink-0">
            +{formatRand(optimal.net_profit)}
          </p>
        </div>
      )}
    </div>
  )
})

ProfitCurve.displayName = 'ProfitCurve'
export default ProfitCurve