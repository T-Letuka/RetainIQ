'use client'

import { useRef, useState, DragEvent } from 'react'
import { Upload, CheckCircle2 } from 'lucide-react'

interface Props {
  label: string
  subLabel: string
  file: File | null
  demoName?: string
  onChange: (f: File) => void
}

export default function UploadZone({ label, subLabel, file, demoName, onChange }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  const filled = file !== null || !!demoName
  const displayName = file?.name ?? demoName

  const handleDrop = (e: DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) onChange(dropped)
  }

  return (
    <div
      onClick={() => !filled && inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={[
        'relative rounded-xl border transition-all duration-200 p-7 text-center select-none',
        filled
          ? 'border-clay/60 bg-clay/5 cursor-default'
          : dragging
          ? 'border-clay bg-clay/8 cursor-copy'
          : 'border-smoke hover:border-ash/50 hover:bg-smoke/40 cursor-pointer',
      ].join(' ')}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onChange(f) }}
      />

      <div className={`mb-3 flex justify-center ${filled ? 'text-clay' : 'text-ash'}`}>
        {filled
          ? <CheckCircle2 size={28} strokeWidth={1.5} />
          : <Upload size={28} strokeWidth={1.5} />
        }
      </div>

      <p className={`text-sm font-medium mb-1 ${filled ? 'text-clay' : 'text-mist'}`}>
        {label}
      </p>
      <p className="text-xs font-mono text-ash">{subLabel}</p>

      {displayName && (
        <p className="mt-3 text-xs font-mono text-clay/80 truncate px-2">
          {displayName}
        </p>
      )}

      {filled && (
        <button
          onClick={(e) => { e.stopPropagation(); onChange(null as any) }}
          className="absolute top-2.5 right-3 text-ash hover:text-mist text-xs font-mono transition-colors"
        >
          change
        </button>
      )}
    </div>
  )
}
