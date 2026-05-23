""" 
RetainIQ - fAST API BACKEND

EXPOSES THE PIPELINE AS HTTP ENDPOINTS BY THE NEXT.JS FRONTEND

Endpoints:
    POST  /api/run-pipeline          Upload both CSVs → run full pipeline
    GET   /api/status/{job_id}       Poll job progress (SSE-friendly)
    GET   /api/results/{job_id}      Fetch final summary + scored CSV
    POST  /api/send-email/{job_id}   Trigger email send after preview
    GET   /health                    Health check


"""

import os
import uuid
import asyncio
import traceback
import pickle
import sys

from datetime import date,datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

sys.path.append(str(Path(__file__).parent))

from pipeline.churn_model import train_and_select, score_customers
from pipeline.segment import assign_actions, build_segment_summary
from pipeline.email_report import send_report, preview

app = FastAPI(title= 'RetainIq', version='1.0.0' )

app.add_middleware(
    CORSMiddleware,
    allow_origins=['"http://localhost:3000", "http://127.0.0.1:3000"'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS:dict ={}

STEP_LABELS =[
    "Validating inputs",
    "Training models",
    "Scoring customers",
    "Assigning actions",
    "Building summary",
    "Generating preview",
]

class JobStatus(BaseModel):
    job_id : str
    status : str
    current_step : int
    total_steps : int
    step_label: str
    progress_pct: int
    error: Optional[str] = None

class PipelineResult(BaseModel):
    job_id:        str
    snapshot_date: str
    total_customers: int
    winner:     str
    winner_auc:    float
    xgb_auc:       float
    lr_auc:     float
    high_count:    int
    high_pct:      float
    medium_count:  int
    medium_pct: float
    low_count:     int
    low_pct:       float
    p1_count:    int
    p2_count:      int
    high_actions:dict
    high_province: dict
    high_tier:  dict
    high_responsive:     int
    high_not_responsive: int
    preview_available: bool

def _update_step(job_id : str, step: int, status: str = 'running'):
    JOBS[job_id]['current_step'] = step
    JOBS[job_id]['status'] =  status
    JOBS[job_id]['step_label'] = STEP_LABELS[step] if step < len(STEP_LABELS) else 'Done'

def run_pipeline_task(
    job_id:         str,
    features_path:  str,
    customers_path: str,
    snapshot_date:  str,
):
    job_dir   = Path("data") / "jobs" / job_id
    model_dir = job_dir / "models"
    job_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
 
    try:

        _update_step(job_id, 0)
        features  = pd.read_csv(features_path)
        customers = pd.read_csv(customers_path)
 
        required_feat = [
            'customer_id', 'churned', 'total_transactions', 'total_spend',
            'avg_monthly_frequency', 'avg_order_value', 'tenure_days',
            'promo_redemption_count', 'promo_redemption_rate',
            'avg_spend_after_promo', 'avg_loadshedding_stage',
            'pct_high_loadshedding_txn', 'pct_weekend_txn',
            'tier_encoded', 'channel_encoded', 'age_encoded',
        ]
        required_cust = ['customer_id', 'loyalty_tier', 'province',
                         'age_group', 'preferred_channel', 'gender']
 
        missing_f = [c for c in required_feat if c not in features.columns]
        missing_c = [c for c in required_cust if c not in customers.columns]
        if missing_f or missing_c:
            raise ValueError(
                f"Missing columns — features: {missing_f}, customers: {missing_c}"
            )
 

        _update_step(job_id, 1)
        results = train_and_select(features, save_dir=str(model_dir))
        model_results = {
            'winner':     results['winner'],
            'winner_auc': results['winner_auc'],
            'xgb_auc':    results['xgb_auc'],
            'lr_auc':     results['lr_auc'],
        }
 

        _update_step(job_id, 2)
        scored = score_customers(features, model_dir=str(model_dir))
        scored.to_csv(job_dir / "scored_customers.csv", index=False)
 

        _update_step(job_id, 3)
        actioned = assign_actions(scored, customers)
        actioned.to_csv(job_dir / "actioned_customers.csv", index=False)
 
  
        _update_step(job_id, 4)
        summary = build_segment_summary(actioned, snapshot_date)
 

        _update_step(job_id, 5)
        preview_path = str(job_dir / "email_preview.html")
        preview(summary, model_results, path=preview_path)
 

        JOBS[job_id]["result"] = {
            **summary,
            **model_results,
            "preview_available": True,
            "job_dir": str(job_dir),
            "actioned_path": str(job_dir / "actioned_customers.csv"),
        }
        JOBS[job_id]["status"] = "complete"
 
    except Exception as exc:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"]  = str(exc)
        JOBS[job_id]["trace"]  = traceback.format_exc()

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}
 
 
@app.post("/api/run-pipeline")
async def run_pipeline_endpoint(
    background_tasks: BackgroundTasks,
    features_file:    UploadFile = File(...),
    customers_file:   UploadFile = File(...),
    snapshot_date:    str        = None,
):
   
    job_id  = str(uuid.uuid4())[:8]
    snap    = snapshot_date or str(date.today())
 
    # Save uploads to temp location
    upload_dir = Path("data") / "uploads" / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
 
    features_path  = str(upload_dir / "features.csv")
    customers_path = str(upload_dir / "customers.csv")
 
    content = await features_file.read()
    Path(features_path).write_bytes(content)
 
    content = await customers_file.read()
    Path(customers_path).write_bytes(content)
 
    JOBS[job_id] = {
        "status":       "pending",
        "current_step": 0,
        "step_label":   STEP_LABELS[0],
        "result":       None,
        "error":        None,
        "started_at":   datetime.utcnow().isoformat(),
    }
 
    background_tasks.add_task(
        run_pipeline_task, job_id, features_path, customers_path, snap
    )
 
    return {"job_id": job_id, "snapshot_date": snap}
 
 
@app.get("/api/status/{job_id}", response_model=JobStatus)
def get_status(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(404, f"Job {job_id} not found")
 
    job   = JOBS[job_id]
    step  = job["current_step"]
    total = len(STEP_LABELS)
    pct   = int((step / total) * 100) if job["status"] == "running" else \
            (100 if job["status"] == "complete" else int((step / total) * 100))
 
    return JobStatus(
        job_id        = job_id,
        status        = job["status"],
        current_step  = step,
        total_steps   = total,
        step_label    = job.get("step_label", STEP_LABELS[0]),
        progress_pct  = pct,
        error         = job.get("error"),
    )
 
 
@app.get("/api/results/{job_id}", response_model=PipelineResult)
def get_results(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(404, f"Job {job_id} not found")
 
    job = JOBS[job_id]
    if job["status"] != "complete":
        raise HTTPException(400, f"Job not complete — status: {job['status']}")
 
    r = job["result"]
    return PipelineResult(
        job_id             = job_id,
        snapshot_date      = r["snapshot_date"],
        total_customers    = r["total_customers"],
        winner             = r["winner"],
        winner_auc         = round(r["winner_auc"], 4),
        xgb_auc            = round(r["xgb_auc"], 4),
        lr_auc             = round(r["lr_auc"], 4),
        high_count         = r["high_count"],
        high_pct           = r["high_pct"],
        medium_count       = r["medium_count"],
        medium_pct         = r["medium_pct"],
        low_count          = r["low_count"],
        low_pct            = r["low_pct"],
        p1_count           = r["p1_count"],
        p2_count           = r["p2_count"],
        high_actions       = r["high_actions"],
        high_province      = r["high_province"],
        high_tier          = r["high_tier"],
        high_responsive    = r["high_responsive"],
        high_not_responsive= r["high_not_responsive"],
        preview_available  = r["preview_available"],
    )
 
 
@app.post("/api/send-email/{job_id}")
def send_email_endpoint(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(404, f"Job {job_id} not found")
 
    job = JOBS[job_id]
    if job["status"] != "complete":
        raise HTTPException(400, "Pipeline must complete before sending email")
 
    if not os.environ.get("SENDGRID_API_KEY"):
        raise HTTPException(400, "SENDGRID_API_KEY not set in .env")
 
    r        = job["result"]
    actioned = pd.read_csv(r["actioned_path"])
    summary  = {k: r[k] for k in [
        "snapshot_date", "total_customers",
        "high_count", "high_pct", "medium_count", "medium_pct",
        "low_count", "low_pct", "high_actions", "high_tier",
        "high_province", "high_responsive", "high_not_responsive",
        "p1_count", "p2_count",
    ]}
    model_results = {
        "winner":     r["winner"],
        "winner_auc": r["winner_auc"],
        "xgb_auc":    r["xgb_auc"],
        "lr_auc":     r["lr_auc"],
    }
 
    success = send_report(actioned, summary, model_results)
    return {"sent": success, "to": os.environ.get("RETAINIQ_TO_EMAIL")}
 
 
@app.get("/api/preview/{job_id}")
def get_preview(job_id: str):

    if job_id not in JOBS:
        raise HTTPException(404, f"Job {job_id} not found")
 
    job = JOBS[job_id]
    if job["status"] != "complete":
        raise HTTPException(400, "Pipeline not complete")
 
    preview_path = Path(job["result"]["job_dir"]) / "email_preview.html"
    if not preview_path.exists():
        raise HTTPException(404, "Preview file not found")
 
    return StreamingResponse(
        preview_path.open("rb"),
        media_type="text/html"
    )
 
 
@app.get("/api/download/{job_id}")
def download_csv(job_id: str):
  
    if job_id not in JOBS:
        raise HTTPException(404, f"Job {job_id} not found")
 
    job = JOBS[job_id]
    if job["status"] != "complete":
        raise HTTPException(400, "Pipeline not complete")
 
    csv_path = Path(job["result"]["actioned_path"])
    snap     = job["result"]["snapshot_date"]
 
    return StreamingResponse(
        csv_path.open("rb"),
        media_type="text/csv",
        headers={
            "Content-Disposition":
                f'attachment; filename="retainiq_{snap}_{job_id}.csv"'
        },
    )
 