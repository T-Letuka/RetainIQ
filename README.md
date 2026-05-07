# RetainIQ 🍔
### Weekly Customer Churn Risk Scoring Pipeline
> *"Every week, tell us which customers are about to go quiet and whether a promo will bring them back."*

---

## The Problem

A mid-size SA fast food brand runs a loyalty programme with thousands of active customers. Some go quiet and never return. The marketing team currently sends blanket promos, wasting budget on customers who were never leaving, and missing the ones who actually needed a nudge.

**RetainIQ** is a repeatable weekly pipeline that scores every loyalty customer on:
1. **Churn risk** — probability of going silent in the next 30 days
2. **Promo sensitivity** — whether a promotion will actually change their behaviour

The data team runs it every Monday and hands a prioritised list to marketing.

---

## Project Structure

```
retainiq/
│
├── data/                        # Generated synthetic datasets (gitignored)
│   ├── customers.csv
│   ├── transactions.csv
│   ├── promotions.csv
│   └── promo_redemptions.csv
│
├── notebooks/
│   ├── 01_eda.ipynb             # Exploratory data analysis
│   ├── 02_feature_engineering.ipynb
│   ├── 03_churn_model.ipynb
│   ├── 04_promo_sensitivity_model.ipynb
│   └── 05_llm_segment_briefs.ipynb
│
├── pipeline/
│   ├── feature_engineering.py   # RFM + behavioural features
│   ├── churn_model.py           # Churn scoring logic
│   ├── promo_model.py           # Promo sensitivity scoring
│   ├── llm_briefs.py            # Claude API segment summaries
│   └── run_pipeline.py          # Weekly entry point
│
├── outputs/                     # Weekly scored output (gitignored)
│   └── weekly_scores_YYYY-MM-DD.csv
│
├── generate_data.py             # Synthetic dataset generator
├── requirements.txt
└── README.md
```

---

## Datasets

All data is **synthetically generated** to simulate a realistic SA fast food loyalty programme. No real customer data is used.

| Table | Rows (approx) | Description |
|---|---|---|
| `customers.csv` | 10 000 | Loyalty members — province, age group, tier, preferred channel |
| `transactions.csv` | ~1.2M | 24 months of purchase history with load-shedding context |
| `promotions.csv` | 19 | SA public holiday & seasonal promos across 2023–2024 |
| `promo_redemptions.csv` | ~200K | Which customers redeemed which promos |

### SA Realism Built In
- **Load-shedding stages** on each transaction — Stage 4+ suppresses in-store visits
- **SA public holidays** as promo triggers (Freedom Day, Heritage Day, Black Friday, etc.)
- **Province distribution** weighted by SA population (GP heaviest, NC lightest)
- **Rand-denominated** spend (R25–R600) with tier-adjusted order values
- **~20% of customers** are seeded as churners with realistic drop-off patterns

---

## Quickstart

### 1. Clone & set up environment

```bash
git clone https://github.com/yourusername/retainiq.git
cd retainiq

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Generate the synthetic data

```bash
python generate_data.py
```

This creates the `data/` folder with all 4 CSV files. Takes ~2–3 minutes for 10 000 customers.

### 3. Run the notebooks in order

Open Jupyter and work through the notebooks in `notebooks/` sequentially:

```bash
jupyter notebook
```

| Notebook | What it covers |
|---|---|
| `01_eda.ipynb` | Data quality, distributions, churn patterns, promo lift |
| `02_feature_engineering.ipynb` | RFM scores, recency trends, promo history features |
| `03_churn_model.ipynb` | Binary churn classifier (XGBoost + SHAP explainability) |
| `04_promo_sensitivity_model.ipynb` | Uplift model — who responds to promos? |
| `05_llm_segment_briefs.ipynb` | Claude API generates plain-English segment summaries |

### 4. Run the weekly pipeline

```bash
python pipeline/run_pipeline.py
```

Outputs a scored CSV to `outputs/weekly_scores_YYYY-MM-DD.csv` with columns:

| Column | Description |
|---|---|
| `customer_id` | Loyalty member ID |
| `churn_probability` | 0–1 score (≥0.6 = high risk) |
| `promo_sensitivity_score` | 0–1 score (≥0.5 = likely to respond) |
| `recommended_action` | `target_with_promo` / `monitor` / `no_action` |
| `segment_brief` | LLM-generated plain-English summary |

---

## Requirements

```
pandas>=2.0
numpy>=1.24
scikit-learn>=1.3
xgboost>=2.0
shap>=0.43
anthropic>=0.25
jupyter
matplotlib
seaborn
```

Install all at once:

```bash
pip install -r requirements.txt
```

You will need an **Anthropic API key** for the LLM segment briefs notebook and pipeline step:

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

---

## Churn Definition

A customer is labelled **churned** if:
- They had **≥2 purchases/month** in any prior 2-month window, AND
- They subsequently had **zero transactions for 45+ days**

This definition captures genuine disengagement rather than natural low-frequency customers.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Data generation | Python, NumPy, pandas |
| Feature engineering | pandas, custom RFM logic |
| Churn model | XGBoost, scikit-learn |
| Promo sensitivity | Logistic Regression / XGBoost uplift |
| Explainability | SHAP |
| LLM layer | Claude API (Anthropic) |
| Deployment *(coming)* | Streamlit + Render / HuggingFace Spaces |

---

## Roadmap

- [x] Synthetic data generation
- [ ] EDA notebook
- [ ] Feature engineering pipeline
- [ ] Churn model + SHAP explainability
- [ ] Promo sensitivity model
- [ ] LLM segment brief generation
- [ ] Streamlit dashboard
- [ ] Dockerised weekly pipeline

---

## Author

Built as a portfolio project targeting marketing analytics roles.
Focused on demonstrating end-to-end DS skills: data engineering, ML modelling, LLM integration, and production pipeline thinking.