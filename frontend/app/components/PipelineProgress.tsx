'use client'

import { JobStatus } from '../lib/api'
import { CheckIcon } from 'lucide-react'

const STEPS = [
  'Validating inputs',
  'Training models',
  'Scoring customers',
  'Assigning actions',
  'Building summary',
  'Generating preview',
]

interface Props {
  status: JobStatus | null
  isComplete: boolean
}

export default function PipelineProgress({ status, isComplete }: Props) {
  const currentStep = status?.current_step ?? 0
  const pct = isComplete ? 100 : status?.progress_pct ?? 0

  return (
    <div className="w-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <p className="text-sm font-medium text-mist">
          {isComplete
            ? 'Pipeline complete'
            : status?.step_label
            ? `${status.step_label}…`
            : 'Starting…'}
        </p>
        <span className="font-mono text-xs text-ash">{pct}%</span>
      </div>

      {/* Progress bar */}
      <div className="h-px bg-smoke mb-8 overflow-hidden rounded">
        <div
          className="h-full bg-clay transition-all duration-500 ease-out rounded"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Steps */}
      <ol className="space-y-4">
        {STEPS.map((label, i) => {
          const done    = isComplete || i < currentStep
          const active  = !isComplete && i === currentStep
          const pending = !done && !active

          return (
            <li key={label} className="flex items-center gap-4">
              {/* Dot */}
              <div className={[
                'flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center',
                done    ? 'bg-clay'                : '',
                active  ? 'border border-clay'     : '',
                pending ? 'border border-smoke'    : '',
              ].join(' ')}>
                {done && <CheckIcon size={11} className="text-ink" strokeWidth={2.5} />}
                {active && (
                  <span className="w-1.5 h-1.5 rounded-full bg-clay animate-pulse-dot" />
                )}
              </div>

              {/* Label */}
              <span className={[
                'text-sm font-mono transition-colors',
                done    ? 'text-ash line-through decoration-ash/40' : '',
                active  ? 'text-mist'                                : '',
                pending ? 'text-smoke'                               : '',
              ].join(' ')}>
                {label}
              </span>

              {/* Step index */}
              <span className="ml-auto font-mono text-xs text-smoke">
                {String(i + 1).padStart(2, '0')}
              </span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
