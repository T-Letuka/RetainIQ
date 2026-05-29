const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export interface JobStarted {
  job_id: string
  snapshot_date: string
}

export interface JobStatus {
  job_id: string
  status: 'pending' | 'running' | 'complete' | 'failed'
  current_step: number
  total_steps: number
  step_label: string
  progress_pct: number
  error?: string
}

export interface PipelineResult {
  job_id: string
  snapshot_date: string
  total_customers: number
  winner: string
  winner_auc: number
  xgb_auc: number
  lr_auc: number
  high_count: number
  high_pct: number
  medium_count: number
  medium_pct: number
  low_count: number
  low_pct: number
  p1_count: number
  p2_count: number
  high_actions: Record<string, number>
  high_province: Record<string, number>
  high_tier: Record<string, number>
  high_responsive: number
  high_not_responsive: number
  preview_available: boolean
}

export async function startPipeline(
  featuresFile: File,
  customersFile: File,
): Promise<JobStarted> {
  const fd = new FormData()
  fd.append('features_file', featuresFile)
  fd.append('customers_file', customersFile)

  const res = await fetch(`${API}/api/run-pipeline`, { method: 'POST', body: fd })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API ${res.status}: ${body}`)
  }
  return res.json()
}

export async function getStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API}/api/status/${jobId}`)
  if (!res.ok) throw new Error(`Status fetch failed: ${res.status}`)
  return res.json()
}

export async function getResults(jobId: string): Promise<PipelineResult> {
  const res = await fetch(`${API}/api/results/${jobId}`)
  if (!res.ok) throw new Error(`Results fetch failed: ${res.status}`)
  return res.json()
}

export async function sendEmail(jobId: string): Promise<{ sent: boolean; to: string }> {
  const res = await fetch(`${API}/api/send-email/${jobId}`, { method: 'POST' })
  if (!res.ok) throw new Error(`Send failed: ${res.status}`)
  return res.json()
}

export function previewUrl(jobId: string)  { return `${API}/api/preview/${jobId}` }
export function downloadUrl(jobId: string) { return `${API}/api/download/${jobId}` }
