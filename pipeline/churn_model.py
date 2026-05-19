"""
RetainIQ — Churn Model
========================
Trains two competing models on the feature table:
    1. Logistic Regression  (interpretable baseline)
    2. XGBoost              (performance champion)
 
Compares both on ROC-AUC and auto-selects the winner.
Saves the winning model to models/churn_model.pkl
"""


import os
import pickle
import pandas as pd 
import numpy as np

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    roc_auc_score, classification_report,confusion_matrix,RocCurveDisplay
)
from xgboost import XGBClassifier

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import warnings
warnings.filterwarnings('ignore')


FEATURE_COLS = [
   'total_transactions',
    'total_spend',
    'avg_monthly_frequency',
    'avg_order_value',
    'tenure_days',
    #promo engagement 
    'promo_redemption_count',
    'promo_redemption_rate',
    'avg_spend_after_promo',
    # SA context
    'avg_loadshedding_stage',
    'pct_high_loadshedding_txn',
    # Behavioural patterns
    'pct_weekend_txn',
    #customer profile
    'tier_encoded',
    'channel_encoded',
    'age_encoded',
    
]

TARGET_COL = 'churned'
TEST_SIZE = 0.20
RANDOM_STATE = 42
CV_FOLDS = 5

def train_and_select(features: pd.DataFrame, save_dir:str = 'models') -> dict:
    os.makedirs(save_dir, exist_ok=True)

    X = features[FEATURE_COLS]
    y= features[TARGET_COL]

    X_train, X_test, y_train, y_test = train_test_split(
        X,y , 
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    print(f"Train { len(X_train):,} rows  | Test: {len(X_test):,} rows")
    print(f" Churn rate - train : {y_train.mean()*100:.1f} | test: {y_test.mean()*100:.1f}")
    print()

    print('Training Logistic Regression')

    lr = Pipeline([
        ('scaler', StandardScaler()),
        ('model', LogisticRegression(
            class_weight='balanced',
            max_iter=1000,
            random_state=RANDOM_STATE,
        ))
    ])

    lr_cv_score = cross_val_score(
        lr, X_train, y_train,
        cv=StratifiedKFold(CV_FOLDS, shuffle=True, random_state=RANDOM_STATE),
        scoring='roc_auc',
        n_jobs=-1,    )
    
    lr.fit(X_train,y_train)
    lr_test_auc = roc_auc_score(y_test, lr.predict_proba(X_test)[:,1])

    print(f"  CV AUC : {lr_cv_score.mean():.4f} ± {lr_cv_score.std():.4f} ")
    print(f" Test AUC : {lr_test_auc:.4f}")
    print()


    neg_count = (y_train == 0).sum()
    pos_count = (y_train == 1).sum()

    scale_pos_weight = neg_count / pos_count 

    print(" TRAINING XGBoost")

    xgb_model = XGBClassifier(
        n_estimators      = 300,
        max_depth         = 4,
        learning_rate     = 0.05,
        subsample         = 0.8,
        colsample_bytree  = 0.8,
        scale_pos_weight  = scale_pos_weight,
        random_state      = RANDOM_STATE,
        eval_metric       = 'auc',
        verbosity         = 0,

    )

    xgb_cv_scores = cross_val_score(
        xgb_model, X_train, y_train,
        cv=StratifiedKFold(CV_FOLDS, shuffle=True, random_state=RANDOM_STATE),
        scoring='roc_auc',
        n_jobs=-1,
    )

    xgb_model.fit(X_train,y_train)
    xgb_test_auc = roc_auc_score(y_test, xgb_model.predict_proba(X_test)[:,1])

    print(f"  CV AUC: {xgb_cv_scores.mean():.4f} ± {xgb_cv_scores.std():.4f}")
    print(f"   Test AUC : {xgb_test_auc:.4f}")
    print()

    if xgb_test_auc >= lr_test_auc:
        winner = 'XGBoost'
        winner_model = xgb_model
        winner_auc = xgb_test_auc
    else:
        winner = 'Logistic Regression'
        winner_model = lr
        winner_auc = lr_test_auc
    print(f"  ----Model Comparison")
    print(f"  {'Model':<25} {'Test AUC':>10}")
    print(f"  {'XGBoost':<25} {xgb_test_auc:>10.4f}  {'← WINNER' if winner == 'XGBoost' else ''}")
    print(f"  {'Logistic Regression':<25} {lr_test_auc:>10.4f}  {'← WINNER' if winner == 'Logistic Regression' else ''}")
    print()
    print(f"  Selected: {winner} (AUC: {winner_auc:.4f})")
    model_path = os.path.join(save_dir, 'churn_model.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump({
            'model':        winner_model,
            'winner':       winner,
            'winner_auc':   winner_auc,
            'xgb_auc':      xgb_test_auc,
            'lr_auc':       lr_test_auc,
            'feature_cols': FEATURE_COLS,
        }, f)
    print(f"  Saved to {model_path}")
 
    return {
        'winner':      winner,
        'winner_auc':  winner_auc,
        'xgb_auc':     xgb_test_auc,
        'lr_auc':      lr_test_auc,
        'model':       winner_model,
        'X_test':      X_test,
        'y_test':      y_test,
        'xgb_model':   xgb_model,
        'lr_pipeline': lr,
    }
 
 

 
def score_customers(features: pd.DataFrame, model_dir: str = 'models') -> pd.DataFrame:
    """
    Load the saved winning model and score every customer.
 
    Returns features DataFrame with two new columns:
        churn_probability  — 0 to 1
        churn_risk_band    — High / Medium / Low
    """
 
    model_path = os.path.join(model_dir, 'churn_model.pkl')
    with open(model_path, 'rb') as f:
        bundle = pickle.load(f)
 
    model        = bundle['model']
    feature_cols = bundle['feature_cols']
 
    scored = features.copy()
    scored['churn_probability'] = model.predict_proba(scored[feature_cols])[:, 1].round(4)
 
    # Risk bands — thresholds informed by business context:
    # High   ≥ 0.60 → prioritise for promo intervention this week
    # Medium 0.30–0.59 → monitor, lower-cost nudge
    # Low    < 0.30 → no action needed
    scored['churn_risk_band'] = pd.cut(
        scored['churn_probability'],
        bins   = [0, 0.30, 0.60, 1.01],
        labels = ['Low', 'Medium', 'High'],
        right  = False,
    )
 
    return scored
 
 

def plot_evaluation(results: dict, save_dir: str = 'data'):
    """
    Generate 4 evaluation plots:
        1. ROC curves — both models overlaid
        2. Confusion matrices — both models side by side
        3. Feature importance — XGBoost
        4. Churn probability distribution
    """
 
    os.makedirs(save_dir, exist_ok=True)
    X_test      = results['X_test']
    y_test      = results['y_test']
    xgb_model   = results['xgb_model']
    lr_pipeline = results['lr_pipeline']
 
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('RetainIQ — Model Evaluation', fontsize=15, fontweight='bold')
    COLORS = ['#E63946', '#457B9D', '#2A9D8F', '#E9C46A']
 
    
    ax = axes[0, 0]
    for model, label, color in [
        (xgb_model,   f"XGBoost (AUC={results['xgb_auc']:.3f})",  COLORS[0]),
        (lr_pipeline, f"Logistic Regression (AUC={results['lr_auc']:.3f})", COLORS[1]),
    ]:
        RocCurveDisplay.from_estimator(model, X_test, y_test,
                                        ax=ax, name=label, color=color)
    ax.plot([0,1],[0,1], 'k--', linewidth=0.8, label='Random (AUC=0.500)')
    ax.set_title('ROC Curves — Model Comparison', fontweight='bold')
    ax.legend(fontsize=8)
 

    for i, (model, label) in enumerate([
        (xgb_model,   'XGBoost'),
        (lr_pipeline, 'Logistic Regression'),
    ]):
        ax = axes[0, 1] if i == 0 else axes[1, 0]
        cm = confusion_matrix(y_test, model.predict(X_test))
        sns_cm = pd.DataFrame(
            cm,
            index   = ['Actual Active', 'Actual Churned'],
            columns = ['Pred Active',   'Pred Churned'],
        )
        import seaborn as sns
        sns.heatmap(sns_cm, annot=True, fmt='d', cmap='Blues', ax=ax,
                    linewidths=0.5, cbar=False)
        ax.set_title(f'Confusion Matrix — {label}', fontweight='bold')
        ax.set_ylabel('')
        ax.set_xlabel('')
 

    ax = axes[1, 1]
    importance = pd.Series(
        xgb_model.feature_importances_,
        index=FEATURE_COLS
    ).sort_values(ascending=True).tail(12)
 
    ax.barh(importance.index, importance.values, color=COLORS[2], edgecolor='white')
    ax.set_title('XGBoost — Top 12 Feature Importances', fontweight='bold')
    ax.set_xlabel('Importance Score')
 
    plt.tight_layout()
    path = os.path.join(save_dir, 'model_evaluation.png')
    plt.savefig(path, bbox_inches='tight', dpi=120)
    plt.show()
    print(f"  Evaluation plots saved to {path}")
 
 

if __name__ == '__main__':
 
    print("Loading features...")
    features = pd.read_csv('data/features.csv')
    print(f"  {len(features):,} customers | churn rate: {features['churned'].mean()*100:.1f}%")
    print()
 
    print("Training models...")
    results = train_and_select(features)
 
    print()
    print("Generating evaluation plots...")
    plot_evaluation(results)
 
    print()
    print("Scoring all customers...")
    scored = score_customers(features)
 
    print()
    print("── Score Distribution ──────────────────────────────────")
    band_counts = scored['churn_risk_band'].value_counts()
    for band in ['High', 'Medium', 'Low']:
        count = band_counts.get(band, 0)
        pct   = count / len(scored) * 100
        print(f"  {band:<8} {count:>5,} customers  ({pct:.1f}%)")
 
    print()
    print("── Sample Scored Output ────────────────────────────────")
    print(scored[['customer_id', 'recency_days', 'churn_probability',
                   'churn_risk_band']].head(10).to_string(index=False))
 
    scored.to_csv('data/scored_customers.csv', index=False)
    print()
    print("Saved to data/scored_customers.csv")



