'use client'

import { PipelineResult, previewUrl, downloadUrl, sendEmail } from '../lib/api'
import { useState } from 'react'
import { ExternalLink, Download, Send, AlertTriangle, RotateCcw } from 'lucide-react'

interface Props {
  result: PipelineResult
  onReset: () => void
}

function RiskBand({
  label, count, pct, color, delay,
}: {
  label: string; count: number; pct: number; color: string; delay: string
}) {
  const bar = Math.round(pct)
  return (
    <div
      className="animate-fade-up fade-up-hidden"
      style={{ animationDelay: delay, animationFillMode: 'forwards' }}
    >
      <div className="flex items-baseline justify-between mb-2">
        <span className="text-xs font-mono uppercase tracking-widest" style={{ color }}>
          {label}
        </span>
        <span className="font-serif text-3xl text-mist">{count.toLocaleString()}</span>
      </div>
      <div className="h-px bg-smoke mb-1.5">
        <div
          className="h-full transition-all duration-700 ease-out"
          style={{ width: `${bar}%`, background: color }}
        />
      </div>
      <p className="text-xs font-mono text-ash text-right">{pct}% of base</p>
    </div>
  )
}

export default function ResultsDashboard({ result, onReset }: Props) {
  const [sending, setSending] = useState(false)
  const [sent,    setSent   ] = useState(false)
  const [sendErr, setSendErr] = useState('')

  const handleSend = async () => {
    setSending(true)
    setSendErr('')
    try {
      const data = await sendEmail(result.job_id)
      if (data.sent) setSent(true)
      else setSendErr('Send failed — check SENDGRID_API_KEY in .env')
    } catch (e: any) {
      setSendErr(e.message)
    } finally {
      setSending(false)
    }
  }

  const topAction = Object.entries(result.high_actions ?? {})
    .sort((a, b) => b[1] - a[1])[0]

  return (
    <div className="space-y-10 animate-fade-up" style={{ animationFillMode: 'forwards' }}>

      {/* ── Snapshot line ── */}
      <div className="flex items-center justify-between border-b border-smoke pb-5">
        <div>
          <p className="font-mono text-xs text-ash uppercase tracking-widest mb-1">Report date</p>
          <p className="font-serif text-xl text-mist italic">{result.snapshot_date}</p>
        </div>
        <div className="text-right">
          <p className="font-mono text-xs text-ash uppercase tracking-widest mb-1">Customers scored</p>
          <p className="font-serif text-xl text-mist">{result.total_customers.toLocaleString()}</p>
        </div>
      </div>

      {/* ── Risk breakdown ── */}
      <div>
        <p className="font-mono text-xs text-ash uppercase tracking-widest mb-6">Risk breakdown</p>
        <div className="space-y-7">
          <RiskBand label="High"   count={result.high_count}   pct={result.high_pct}   color="#E24B4A" delay="0ms" />
          <RiskBand label="Medium" count={result.medium_count} pct={result.medium_pct} color="#EF9F27" delay="80ms" />
          <RiskBand label="Low"    count={result.low_count}    pct={result.low_pct}    color="#639922" delay="160ms" />
        </div>
      </div>

      {/* ── Priority actions ── */}
      <div>
        <p className="font-mono text-xs text-ash uppercase tracking-widest mb-4">Priority actions</p>
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: 'Priority 1', count: result.p1_count, sub: 'Gold + Silver, act this week', accent: '#E24B4A' },
            { label: 'Priority 2', count: result.p2_count, sub: 'Bronze tier, act this week',   accent: '#EF9F27' },
          ].map(({ label, count, sub, accent }, i) => (
            <div
              key={label}
              className="rounded-lg border border-smoke p-4 animate-fade-up fade-up-hidden"
              style={{ animationDelay: `${i * 80}ms`, animationFillMode: 'forwards' }}
            >
              <p className="font-mono text-xs mb-1" style={{ color: accent }}>{label}</p>
              <p className="font-serif text-2xl text-mist mb-1">{count.toLocaleString()}</p>
              <p className="text-xs text-ash leading-snug">{sub}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Top recommendation ── */}
      {topAction && (
        <div className="rounded-lg border border-clay/30 bg-clay/5 p-5">
          <p className="font-mono text-xs text-clay uppercase tracking-widest mb-2">Top recommendation</p>
          <p className="text-sm text-mist leading-relaxed">
            <span className="font-mono text-clay">{topAction[1].toLocaleString()}</span> high-risk customers — {topAction[0]}
          </p>
        </div>
      )}

      {/* ── Model comparison ── */}
      <div>
        <p className="font-mono text-xs text-ash uppercase tracking-widest mb-4">Model comparison</p>
        <div className="border border-smoke rounded-lg divide-y divide-smoke overflow-hidden">
          {[
            { name: 'XGBoost',             auc: result.xgb_auc, winner: result.winner === 'XGBoost' },
            { name: 'Logistic Regression', auc: result.lr_auc,  winner: result.winner === 'Logistic Regression' },
          ].map(({ name, auc, winner }) => (
            <div key={name} className="flex items-center justify-between px-5 py-4">
              <div className="flex items-center gap-3">
                <span className="text-sm text-mist font-medium">{name}</span>
                {winner && (
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-clay/15 text-clay tracking-wider">
                    selected
                  </span>
                )}
              </div>
              <span className="font-mono text-sm text-ash">{auc.toFixed(4)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Province breakdown ── */}
      {result.high_province && Object.keys(result.high_province).length > 0 && (
        <div>
          <p className="font-mono text-xs text-ash uppercase tracking-widest mb-4">
            High-risk by province
          </p>
          <div className="space-y-3">
            {Object.entries(result.high_province)
              .sort((a, b) => b[1] - a[1])
              .map(([province, count]) => {
                const max = Math.max(...Object.values(result.high_province))
                const w = Math.round((count / max) * 100)
                return (
                  <div key={province} className="flex items-center gap-4">
                    <span className="text-xs font-mono text-ash w-36 shrink-0">{province}</span>
                    <div className="flex-1 h-px bg-smoke">
                      <div className="h-full bg-clay/60" style={{ width: `${w}%` }} />
                    </div>
                    <span className="font-mono text-xs text-ash w-8 text-right">{count}</span>
                  </div>
                )
              })}
          </div>
        </div>
      )}

      {/* ── Promo responsiveness ── */}
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg bg-smoke/50 p-4">
          <p className="font-mono text-xs text-ash mb-2">Promo responsive</p>
          <p className="font-serif text-2xl text-mist">{result.high_responsive.toLocaleString()}</p>
          <p className="text-xs text-ash mt-1">high-risk customers</p>
        </div>
        <div className="rounded-lg bg-smoke/50 p-4">
          <p className="font-mono text-xs text-ash mb-2">Non-responsive</p>
          <p className="font-serif text-2xl text-mist">{result.high_not_responsive.toLocaleString()}</p>
          <p className="text-xs text-ash mt-1">need freebie approach</p>
        </div>
      </div>

      {/* ── Action row ── */}
      {sendErr && (
        <div className="flex items-start gap-2 rounded-lg border border-red-900/50 bg-red-950/30 p-4">
          <AlertTriangle size={14} className="text-red-400 mt-0.5 shrink-0" />
          <p className="text-xs font-mono text-red-400">{sendErr}</p>
        </div>
      )}

      <div className="grid grid-cols-3 gap-3 pt-2">
        <a
          href={previewUrl(result.job_id)}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-2 rounded-lg border border-smoke px-4 py-3 text-xs font-mono text-ash hover:border-ash/50 hover:text-mist transition-colors"
        >
          <ExternalLink size={13} /> Preview email
        </a>

        <a
          href={downloadUrl(result.job_id)}
          className="flex items-center justify-center gap-2 rounded-lg border border-smoke px-4 py-3 text-xs font-mono text-ash hover:border-ash/50 hover:text-mist transition-colors"
        >
          <Download size={13} /> Download CSV
        </a>

        <button
          onClick={handleSend}
          disabled={sending || sent}
          className={[
            'flex items-center justify-center gap-2 rounded-lg px-4 py-3 text-xs font-mono transition-all',
            sent
              ? 'bg-clay/20 text-clay border border-clay/40 cursor-default'
              : 'bg-clay text-ink hover:bg-clay/90 active:scale-95',
          ].join(' ')}
        >
          <Send size={13} />
          {sent ? 'Sent!' : sending ? 'Sending…' : 'Send report'}
        </button>
      </div>

      {/* ── Run again ── */}
      <button
        onClick={onReset}
        className="w-full flex items-center justify-center gap-2 text-xs font-mono text-smoke hover:text-ash transition-colors py-2"
      >
        <RotateCcw size={12} /> Run again with new files
      </button>
    </div>
  )
}
