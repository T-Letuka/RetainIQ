'use client'


import { useState, useEffect, useCallback, useRef } from 'react'
import {
  startPipeline, getStatus, getResults,
  JobStatus, PipelineResult,
} from '../app/lib/api'
import { ScoredCustomer } from './components/ProfitCurve'
import UploadZone from './components/UploadZone'
import PipelineProgress from './components/PipelineProgress'
import ResultsDashboard from './components/ResultDashboard'
import { Zap, AlertCircle } from 'lucide-react'

type Stage = 'upload' | 'running' | 'done' | 'error'

const DEMO_FEATURES_URL  = '/demo/demo_features.csv'
const DEMO_CUSTOMERS_URL = '/demo/demo_customers.csv'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function urlToFile(url: string, name: string): Promise<File> {
  const res  = await fetch(url)
  const blob = await res.blob()
  return new File([blob], name, { type: 'text/csv' })
}
async function fetchScoredCustomers(jobId: string): Promise<ScoredCustomer[]> {
  try {
    const res = await fetch(`${API}/api/download-scored/${jobId}`)
    if (!res.ok) return []

    const text = (await res.text()).replace(/\r/g, '')  
    const lines = text.trim().split('\n')
    const header = lines[0].split(',')

    const probIdx    = header.findIndex(h => h.trim() === 'churn_probability')
    const churnedIdx = header.findIndex(h => h.trim() === 'churned')

    console.log('cols:', probIdx, churnedIdx)
    if (probIdx === -1 || churnedIdx === -1) return []

    const result: ScoredCustomer[] = []
    for (const line of lines.slice(1)) {
      if (!line.trim()) continue
      const cols    = line.split(',')
      const prob    = parseFloat(cols[probIdx])
      const churned = parseInt(cols[churnedIdx], 10)
      if (!isNaN(prob) && !isNaN(churned)) result.push({ churn_probability: prob, churned })
    }

    console.log('parsed:', result.length, result[0])
    return result
  } catch (e) {
    console.error(e)
    return []
  }
}
export default function Home() {
  const [stage,         setStage        ] = useState<Stage>('upload')
  const [featuresFile,  setFeaturesFile ] = useState<File | null>(null)
  const [customersFile, setCustomersFile] = useState<File | null>(null)
  const [demoLoaded,    setDemoLoaded   ] = useState(false)
  const [jobId,         setJobId        ] = useState<string | null>(null)
  const [jobStatus,     setJobStatus    ] = useState<JobStatus | null>(null)
  const [result,        setResult       ] = useState<PipelineResult | null>(null)
  const [error,         setError        ] = useState('')
  const [scoredCustomers , setScoredCustomers] = useState<ScoredCustomer[]>([])
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const ready = (featuresFile !== null || demoLoaded) &&
                (customersFile !== null || demoLoaded)


const poll = useCallback(async (id: string) => {
  try {
    const s = await getStatus(id)
    setJobStatus(s)

    if (s.status === 'complete') {
      const r = await getResults(id)
      setResult(r)

      // fetch scored CSV for profit curve
      const scored = await fetchScoredCustomers(id)
      console.log('scored customers fetched:', scored.length, scored[0])
      setScoredCustomers(scored)

      setStage('done')
    } else if (s.status === 'failed') {
      setError(s.error ?? 'Pipeline failed — check FastAPI logs')
      setStage('error')
    } else {
      pollRef.current = setTimeout(() => poll(id), 1100)
    }
  } catch {
    pollRef.current = setTimeout(() => poll(id), 2000)
  }
}, [])

  useEffect(() => () => { if (pollRef.current) clearTimeout(pollRef.current) }, [])


  const loadDemo = async () => {
    try {
      const [f, c] = await Promise.all([
        urlToFile(DEMO_FEATURES_URL,  'demo_features.csv'),
        urlToFile(DEMO_CUSTOMERS_URL, 'demo_customers.csv'),
      ])
      setFeaturesFile(f)
      setCustomersFile(c)
      setDemoLoaded(true)
    } catch {
   
      setDemoLoaded(true)
    }
  }

  const run = async () => {
    if (!featuresFile || !customersFile) return
    setError('')
    setStage('running')
    try {
      const { job_id } = await startPipeline(featuresFile, customersFile)
      setJobId(job_id)
      poll(job_id)
    } catch (e: any) {
      setError(e.message)
      setStage('error')
    }
  }


  const reset = () => {
    if (pollRef.current) clearTimeout(pollRef.current)
    setStage('upload')
    setFeaturesFile(null)
    setCustomersFile(null)
    setDemoLoaded(false)
    setJobId(null)
    setJobStatus(null)
    setResult(null)
    setError('')
  }


  return (
    <div className="min-h-screen bg-ink">
      <div className="max-w-lg mx-auto px-10 py-30 ">

     
        <header className="mb-14">
          <div className="flex items-start justify-between mb-8">
            <div>
              <h1 className="font-serif text-5xl text-[#471914] leading-none mb-1">
                Retain<span className="italic text-clay">IQ</span>
              </h1>
              <p className="font-mono text-xs text-[#471914] tracking-widest uppercase">
                Churn Intelligence Engine
              </p>
            </div>
            <div className="text-right">
              <p className="font-mono text-[10px] text-[#471914] uppercase tracking-widest">API</p>
              <p className="font-mono text-xs text-[#471914]">localhost:8000</p>
            </div>
          </div>


          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-smoke" />
            <div className="w-1 h-1 rounded-full bg-clay" />
            <div className="flex-1 h-px bg-smoke" />
          </div>
        </header>


        {(stage === 'upload' || stage === 'error') && (
          <div className="space-y-6 animate-fade-up" style={{ animationFillMode: 'forwards' }}>

            <div>
              <p className="font-mono text-xs text- uppercase tracking-widest mb-4">
                Upload data files
              </p>
              <div className="grid grid-cols-2 gap-3">
                <UploadZone
                  label="features.csv"
                  subLabel="ML feature table"
                  file={featuresFile}
                  demoName={demoLoaded && !featuresFile ? 'demo_features.csv' : undefined}
                  onChange={setFeaturesFile}
                />
                <UploadZone
                  label="customers.csv"
                  subLabel="Customer profiles"
                  file={customersFile}
                  demoName={demoLoaded && !customersFile ? 'demo_customers.csv' : undefined}
                  onChange={setCustomersFile}
                />
              </div>
            </div>

            {/* Demo strip */}
            <div className="flex items-center gap-3">
              <div className="flex-1 h-px bg-smoke" />
              <button
                onClick={loadDemo}
                className="flex items-center gap-1.5 font-mono text-xs text-ash hover:text-clay transition-colors"
              >
                <Zap size={11} />
                {demoLoaded ? 'demo loaded' : 'use demo data'}
              </button>
              <div className="flex-1 h-px bg-smoke" />
            </div>

            {demoLoaded && (
              <p className="font-mono text-[11px] text-smoke text-center -mt-2">
                500 SA customers · 24.6% churn · all provinces
              </p>
            )}


            {stage === 'error' && error && (
              <div className="flex items-start gap-3 rounded-lg border border-red-900/50 bg-red-950/20 p-4">
                <AlertCircle size={14} className="text-red-500 mt-0.5 shrink-0" />
                <div>
                  <p className="font-mono text-xs text-red-400 mb-1">Pipeline error</p>
                  <p className="font-mono text-[11px] text-red-500/70">{error}</p>
                  <p className="font-mono text-[11px] text-smoke mt-2">
                    Is FastAPI running? <code className="text-ash">uvicorn main:app --reload --port 8000</code>
                  </p>
                </div>
              </div>
            )}

            {/* Run button */}
            <button
              onClick={run}
              disabled={!ready}
              className={[
                'w-full py-4 rounded-xl font-mono text-sm tracking-wider transition-all duration-200',
                ready
                  ? 'bg-clay text-ink hover:bg-clay/90 active:scale-[0.98]'
                  : 'bg-smoke/50 text-ash cursor-not-allowed',
              ].join(' ')}
            >
              {stage === 'error' ? '↺  Retry pipeline' : '▶  Run pipeline'}
            </button>

       
            {!ready && (
              <p className="font-mono text-[11px] text-smoke text-center">
                Upload both files or load demo data to continue
              </p>
            )}
          </div>
        )}


        {stage === 'running' && (
          <div className="animate-fade-up" style={{ animationFillMode: 'forwards' }}>
            <p className="font-mono text-xs text-ash uppercase tracking-widest mb-8">
              Pipeline running
              {jobId && <span className="ml-3 text-smoke">· job {jobId}</span>}
            </p>
            <PipelineProgress status={jobStatus} isComplete={false} />
          </div>
        )}


        {stage === 'done' && result && (
          <ResultsDashboard result={result} onReset={reset}  scoredCustomers={scoredCustomers} />
        )}


        <footer className="mt-16 pt-8 border-t border-smoke">
          <p className="font-mono text-[10px] text-smoke text-center tracking-widest uppercase">
            RetainIQ · Automated Churn Intelligence · {new Date().getFullYear()}
          </p>
        </footer>

      </div>
    </div>
  )
}
