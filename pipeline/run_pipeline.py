"""
RetainIQ — Pipeline Orchestrator
==================================
Ties together all pipeline stages in order:
 
    1. Load & validate raw CSV inputs
    2. Train models + auto-select winner      (churn_model.py)
    3. Score all customers                    (churn_model.py)
    4. Assign segment actions                 (segment_rules.py)
    5. Build summary stats                    (segment_rules.py)
    6. Render preview + send email report     (email_report.py)
 
Usage:
    python run_pipeline.py                                  # uses default paths
    python run_pipeline.py --features data/features.csv --customers data/customers.csv
    python run_pipeline.py --preview-only                   # skips email send
    python run_pipeline.py --skip-train                     # uses existing models/churn_model.pkl
 """

import os 
import sys 
import argparse
import pickle
import traceback
from datetime import date, datetime 

import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
 
from pipeline.churn_model   import train_and_select, score_customers
from pipeline.segment import assign_actions, build_segment_summary
from pipeline.email_report  import send_report, preview

DEFAULTS = {
    'feature_path': 'data/features.csv',
    'customer_path': 'data/customers.csv',
    'output_dir': 'data',
    'model_dir': 'models',
}

REQUIRED_FEATURE_COLS = [
    'customer_id', 'churned', ''
    'total_transations','total_spend' ' avg_monthly_frequency',
   'avg_order_value', 'tenure_days', 'promotion_redemption_count', 'pct_high_loadshedding_txn',
   'avg_loadshedding_stage', 'avg_spend_after_promo', 'promotion_redemption_rate',
   'pct_weekend_txn', 'tier_encoded', 'channel_encoded', 'age_encoded'  

]
REQUIRED_CUSTOMER_COLS = [
    'customer_id', 'loyalty_tier', 'province',
    'age_group', 'preferred_channel', 'gender',
]
 
def _banner(text:str):
    print('--' * 62)
    print(f"  {text}")
    print('--'* 62)

def _step(n:int, label:str):
    print(f" \n [{n}]  {label}")
    print(f"      {'--' * (len(label) + 2)}")

def _validate_csv(path: str, required_cols: list, label: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"{label} not found at: {path}")
 
    df = pd.read_csv(path)
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(
            f"{label} is missing columns: {missing}\n"
            f"  Found: {list(df.columns)}"
        )
    print(f"       ✓  {label}: {len(df):,} rows, {len(df.columns)} columns")
    return df
 
def _load_model_bundle(model_dir: str) -> dict:
    model_path = os.path.join(model_dir, 'churn_model.pkl')
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"No saved model at {model_path}. "
            "Run without --skip-train to train first."
        )
    with open(model_path, 'rb') as f:
        bundle = pickle.load(f)
    print(f"       ✓  Loaded: {bundle['winner']} (AUC {bundle['winner_auc']:.4f})")
    return bundle

def _print_risk_summary(actioned: pd.DataFrame):
    total = len(actioned)
    print()
    print(f"       {'Band':<10} {'Count':>6}  {'%':>5}   {'Top Action'}")
    print(f"       {'─'*10} {'─'*6}  {'─'*5}   {'─'*35}")
    for band in ['High', 'Medium', 'Low']:
        subset = actioned[actioned['churn_risk_band'] == band]
        count  = len(subset)
        pct    = count / total * 100
        top    = subset['recommended_action'].mode()[0] if count else '—'
        print(f"       {band:<10} {count:>6,}  {pct:>4.1f}%   {top}")


def run_pipeline(
    features_path:  str  = DEFAULTS['features_path'],
    customers_path: str  = DEFAULTS['customers_path'],
    output_dir:     str  = DEFAULTS['output_dir'],
    model_dir:      str  = DEFAULTS['model_dir'],
    skip_train:     bool = False,
    preview_only:   bool = False,
    snapshot_date:  str  = None,
) -> bool:
 
    started_at = datetime.now()
    snapshot   = snapshot_date or str(date.today())
 
    _banner(f"RetainIQ — Weekly Pipeline  ·  {snapshot}")
 
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(model_dir,  exist_ok=True)
 
    # ── Step 1 : Load & validate ─────────────────────────────────────────────
    _step(1, "Loading & validating inputs")
    features  = _validate_csv(features_path,  REQUIRED_FEATURE_COLS,  "features.csv")
    customers = _validate_csv(customers_path, REQUIRED_CUSTOMER_COLS, "customers.csv")
 
    churn_rate = features['churned'].mean() * 100
    print(f"       ✓  Churn rate: {churn_rate:.1f}%")
 
    # ── Step 2 : Train or load model ─────────────────────────────────────────
    if skip_train:
        _step(2, "Loading existing model  (--skip-train)")
        bundle = _load_model_bundle(model_dir)
        model_results = {
            'winner':     bundle['winner'],
            'winner_auc': bundle['winner_auc'],
            'xgb_auc':    bundle['xgb_auc'],
            'lr_auc':     bundle['lr_auc'],
        }
    else:
        _step(2, "Training models")
        print()
        results = train_and_select(features, save_dir=model_dir)
        model_results = {
            'winner':     results['winner'],
            'winner_auc': results['winner_auc'],
            'xgb_auc':    results['xgb_auc'],
            'lr_auc':     results['lr_auc'],
        }
        print(f"\n       ✓  Winner: {model_results['winner']} "
              f"(AUC {model_results['winner_auc']:.4f})")
 
    # ── Step 3 : Score customers ─────────────────────────────────────────────
    _step(3, "Scoring all customers")
    scored = score_customers(features, model_dir=model_dir)
 
    high_n   = (scored['churn_risk_band'] == 'High').sum()
    medium_n = (scored['churn_risk_band'] == 'Medium').sum()
    low_n    = (scored['churn_risk_band'] == 'Low').sum()
    print(f"       ✓  Scored {len(scored):,} customers")
    print(f"           High: {high_n:,}  |  Medium: {medium_n:,}  |  Low: {low_n:,}")
 
    scored_path = os.path.join(output_dir, 'scored_customers.csv')
    scored.to_csv(scored_path, index=False)
    print(f"       ✓  Saved → {scored_path}")
 
    # ── Step 4 : Assign actions ──────────────────────────────────────────────
    _step(4, "Assigning segment actions")
    actioned = assign_actions(scored, customers)
 
    _print_risk_summary(actioned)
 
    actioned_path = os.path.join(output_dir, 'actioned_customers.csv')
    actioned.to_csv(actioned_path, index=False)
    print(f"\n       ✓  Saved → {actioned_path}")
 
    # ── Step 5 : Build summary ───────────────────────────────────────────────
    _step(5, "Building report summary")
    summary = build_segment_summary(actioned, snapshot)
 
    print(f"       ✓  P1 (act this week): {summary['p1_count']:,} customers")
    print(f"       ✓  P2 (act this week): {summary['p2_count']:,} customers")
 
    # ── Step 6 : Email report ────────────────────────────────────────────────
    _step(6, "Generating email report")
 
    preview_path = os.path.join(output_dir, 'email_preview.html')
    preview(summary, model_results, path=preview_path)
 
    if preview_only:
        print(f"\n       ⚠  --preview-only flag set — skipping email send")
        email_sent = False
    elif not os.environ.get('SENDGRID_API_KEY'):
        print(f"\n       ⚠  SENDGRID_API_KEY not set in .env — skipping send")
        email_sent = False
    else:
        print(f"\n       Sending via SendGrid...")
        email_sent = send_report(actioned, summary, model_results)
 
    # ── Done ─────────────────────────────────────────────────────────────────
    elapsed = (datetime.now() - started_at).total_seconds()
 
    _banner(f"Pipeline complete  ·  {elapsed:.1f}s")
    print(f"  Snapshot date  : {snapshot}")
    print(f"  Customers      : {summary['total_customers']:,}")
    print(f"  Model          : {model_results['winner']}  (AUC {model_results['winner_auc']:.4f})")
    print(f"  High risk      : {summary['high_count']:,}  ({summary['high_pct']}%)")
    print(f"  Priority 1     : {summary['p1_count']:,}")
    print(f"  Priority 2     : {summary['p2_count']:,}")
    print(f"  Email sent     : {'Yes' if email_sent else 'No'}")
    print(f"  Outputs        : {output_dir}/")
    print()
 
    return email_sent
 
 
# ── CLI ───────────────────────────────────────────────────────────────────────
 
def _parse_args():
    p = argparse.ArgumentParser(
        description='RetainIQ — Weekly churn analysis pipeline',
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument('--features',      default=DEFAULTS['features_path'],
                   help=f"Path to features CSV  (default: {DEFAULTS['features_path']})")
    p.add_argument('--customers',     default=DEFAULTS['customers_path'],
                   help=f"Path to customers CSV  (default: {DEFAULTS['customers_path']})")
    p.add_argument('--output-dir',    default=DEFAULTS['output_dir'],
                   help=f"Output directory  (default: {DEFAULTS['output_dir']})")
    p.add_argument('--model-dir',     default=DEFAULTS['model_dir'],
                   help=f"Model directory  (default: {DEFAULTS['model_dir']})")
    p.add_argument('--skip-train',    action='store_true',
                   help='Skip model training and load existing models/churn_model.pkl')
    p.add_argument('--preview-only',  action='store_true',
                   help='Generate HTML preview but do not send email')
    p.add_argument('--date',          default=None,
                   help='Override snapshot date  (default: today, YYYY-MM-DD)')
    return p.parse_args()
 
 
if __name__ == '__main__':
    args = _parse_args()
    try:
        run_pipeline(
            features_path  = args.features,
            customers_path = args.customers,
            output_dir     = args.output_dir,
            model_dir      = args.model_dir,
            skip_train     = args.skip_train,
            preview_only   = args.preview_only,
            snapshot_date  = args.date,
        )
    except (FileNotFoundError, ValueError) as e:
        print(f"\n  ✗  Input error: {e}\n")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n  Pipeline interrupted.\n")
        sys.exit(0)
    except Exception:
        print(f"\n  ✗  Unexpected error:\n")
        traceback.print_exc()
        sys.exit(1)


 

