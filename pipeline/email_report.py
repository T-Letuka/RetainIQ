"""
RetainIQ — Email Report
========================
Renders the Jinja2 HTML template and delivers via SendGrid.
 
Setup:
    pip install sendgrid python-dotenv jinja2
    Add to .env:
        SENDGRID_API_KEY=SG.xxxxxxxxx
        RETAINIQ_FROM_EMAIL=you@domain.com
        RETAINIQ_TO_EMAIL=marketing@domain.com
 
Called by:
    run_pipeline.py  →  send_report(actioned, summary, model_results)
 
Or standalone:
    python pipeline/email_report.py
"""

import os
import base64
import pickle
import pandas as pd
from datetime import date
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Attachment, FileContent, FileName, FileType, Disposition
)

load_dotenv()

def render_template(summary:dict, model_results: dict) -> str:
    env      = Environment(loader=FileSystemLoader('pipeline'))
    template = env.get_template('email_template.html')
    return template.render(**summary, **model_results)

def preview(summary: dict, model_results: dict, path: str = 'data/email_preview.html'):
    html = render_template(summary, model_results)
    with open(path, 'w') as f:
        f.write(html)
    print(f"  Preview saved → {path}")
    print(f"  Open in browser: file://{os.path.abspath(path)}")

def send_report(actioned: pd.DataFrame, summary: dict, model_results: dict) -> bool:
 
    api_key    = os.environ['SENDGRID_API_KEY']
    from_email = os.environ['RETAINIQ_FROM_EMAIL']
    to_email   = os.environ['RETAINIQ_TO_EMAIL']
 
    subject = (
        f"RetainIQ Weekly Report — {summary['snapshot_date']} | "
        f"{summary['high_count']} High Risk Customers"
    )
 
    html = render_template(summary, model_results)
 
    message = Mail(
        from_email   = from_email,
        to_emails    = to_email,
        subject      = subject,
        html_content = html,
    )
 
    # Attach scored CSV
    output_cols = [
        'customer_id', 'churn_probability', 'churn_risk_band',
        'loyalty_tier', 'province', 'recommended_action', 'priority'
    ]
    csv_bytes = actioned[output_cols].to_csv(index=False).encode('utf-8')
    attachment = Attachment(
        FileContent(base64.b64encode(csv_bytes).decode()),
        FileName(f"retainiq_scores_{summary['snapshot_date']}.csv"),
        FileType('text/csv'),
        Disposition('attachment'),
    )
    message.attachment = attachment
 
    response = SendGridAPIClient(api_key).send(message)
    success  = response.status_code in (200, 202)
 
    if success:
        print(f"   Email sent to {to_email}")
    else:
        print(f"   Failed — status {response.status_code}: {response.body}")
 
    return success

if __name__ == '__main__':
    import sys
    sys.path.append('.')
    from pipeline.segment import build_segment_summary
 
    actioned = pd.read_csv('data/actioned_customers.csv')
    with open('models/churn_model.pkl', 'rb') as f:
        bundle = pickle.load(f)
 
    model_results = {
        'winner':     bundle['winner'],
        'winner_auc': bundle['winner_auc'],
        'xgb_auc':    bundle['xgb_auc'],
        'lr_auc':     bundle['lr_auc'],
    }
    summary = build_segment_summary(actioned, str(date.today()))
 
    preview(summary, model_results)
 
    if os.environ.get('SENDGRID_API_KEY'):
        send_report(actioned, summary, model_results)
    else:
        print("  SENDGRID_API_KEY not set -  preview only.")
 
