#Generating data.

"""
RetainIQ — Synthetic Data Generator
=====================================
Generates 4 tables simulating 24 months of a fictional SA fast food
loyalty programme:
  - customers.csv
  - transactions.csv
  - promotions.csv
  - promo_redemptions.csv
 
Run:
    pip install pandas numpy faker
    python generate_data.py
 
Outputs land in ./data/
"""

import os 
import random
import pandas as pd
import numpy as np
from datetime import date, timedelta

random.seed(42)
np.random.seed(42)

os.makedirs('data',exist_ok=True)

N_CUSTOMERS   = 10_000
START_DATE    = date(2023, 1, 1)
END_DATE      = date(2024, 12, 31)
DATE_RANGE    = pd.date_range(START_DATE, END_DATE, freq="D")


PROVINCES = ["Gauteng", "Western Cape", "KwaZulu-Natal", "Eastern Cape",
             "Limpopo", "Mpumalanga", "North West", "Free State", "Northern Cape"]
PROVINCE_WEIGHTS = [0.26, 0.12, 0.20, 0.12, 0.10, 0.07, 0.06, 0.05, 0.02]

SA_PROMO_EVENTS = [
    ("NewYear2023",       "Discount", 15, "2023-01-01", "2023-01-02", "All"),
    ("ValentinesDay2023", "BOGOF",     0, "2023-02-14", "2023-02-14", "App"),
    ("HumanRightsDay2023","Discount", 20, "2023-03-21", "2023-03-21", "All"),
    ("FreedomDay2023",    "Freebie",   0, "2023-04-27", "2023-04-28", "App"),
    ("YouthDay2023",      "Discount", 10, "2023-06-16", "2023-06-16", "All"),
    ("WomensDay2023",     "Discount", 20, "2023-08-09", "2023-08-09", "All"),
    ("HeritageDay2023",   "BOGOF",     0, "2023-09-24", "2023-09-24", "App"),
    ("BlackFriday2023",   "Discount", 30, "2023-11-24", "2023-11-26", "All"),
    ("FestiveSeason2023", "Discount", 15, "2023-12-15", "2023-12-31", "App"),
    ("NewYear2024",       "Discount", 15, "2024-01-01", "2024-01-02", "All"),
    ("ValentinesDay2024", "BOGOF",     0, "2024-02-14", "2024-02-14", "App"),
    ("HumanRightsDay2024","Discount", 20, "2024-03-21", "2024-03-21", "All"),
    ("FreedomDay2024",    "Freebie",   0, "2024-04-27", "2024-04-28", "App"),
    ("ElectionDay2024",   "Discount", 10, "2024-05-29", "2024-05-29", "All"),
    ("YouthDay2024",      "Discount", 10, "2024-06-16", "2024-06-16", "All"),
    ("WomensDay2024",     "Discount", 20, "2024-08-09", "2024-08-09", "All"),
    ("HeritageDay2024",   "BOGOF",     0, "2024-09-24", "2024-09-24", "App"),
    ("BlackFriday2024",   "Discount", 30, "2024-11-29", "2024-12-01", "All"),
    ("FestiveSeason2024", "Discount", 15, "2024-12-15", "2024-12-31", "App"),
]

LOADSHEDDING_PERIODS = [
    ("2023-01-01", "2023-02-28", 4),
    ("2023-03-01", "2023-06-30", 6),
    ("2023-07-01", "2023-09-30", 5),
    ("2023-10-01", "2023-12-31", 3),
    ("2024-01-01", "2024-03-31", 2),
    ("2024-04-01", "2024-12-31", 0),   
]

def get_loadshedding_stage(dt):
    for start, end, stage in LOADSHEDDING_PERIODS:
        if pd.Timestamp(start) <= dt <= pd.Timestamp(end):
            return stage
    return 0
 

ls_lookup = {d: get_loadshedding_stage(d) for d in DATE_RANGE}

#for table 1 
print('Gnerating customers')
age_groups   = ["18-25", "26-35", "36-50", "50+"]
age_weights  = [0.25, 0.35, 0.28, 0.12]
genders      = ["Male", "Female", "Prefer not to say"]
gender_w     = [0.46, 0.50, 0.04]
tiers        = ["Bronze", "Silver", "Gold"]
tier_weights = [0.60, 0.30, 0.10]
channels     = ["In-store", "App", "Drive-thru"]
channel_w    = [0.45, 0.35, 0.20]

join_dates = [
    START_DATE + timedelta(days=random.randint(0, (END_DATE - START_DATE).days))
    for _ in range(N_CUSTOMERS)
]

customers = pd.DataFrame({
    "customer_id":        [f"C{str(i).zfill(5)}" for i in range(1, N_CUSTOMERS + 1)],
    "join_date":          join_dates,
    "province":           np.random.choice(PROVINCES, N_CUSTOMERS, p=PROVINCE_WEIGHTS),
    "age_group":          np.random.choice(age_groups, N_CUSTOMERS, p=age_weights),
    "gender":             np.random.choice(genders, N_CUSTOMERS, p=gender_w),
    "loyalty_tier":       np.random.choice(tiers, N_CUSTOMERS, p=tier_weights),
    "preferred_channel":  np.random.choice(channels, N_CUSTOMERS, p=channel_w),
})

customers.to_csv('data/customers.csv',index=False)
print(f"{len(customers):,} customers")


#table 2 
print('generating transactions')

cust_freq = {}
tier_freq_map = {"Bronze": (2, 6), "Silver": (4, 10), "Gold": (8, 16)}
 
for _, row in customers.iterrows():
    lo, hi = tier_freq_map[row["loyalty_tier"]]
    cust_freq[row["customer_id"]] = random.randint(lo, hi)
 

churner_ids = set(
    customers.sample(frac=0.20, random_state=42)["customer_id"].tolist()
)
 
transactions = []
tx_id = 1

for _, cust in customers.iterrows():
    cid        = cust["customer_id"]
    join_dt    = pd.Timestamp(cust["join_date"])
    freq       = cust_freq[cid]               
    channel    = cust["preferred_channel"]
    is_churner = cid in churner_ids
 
    churn_date = None
    if is_churner:
        offset = random.randint(180, 540)
        churn_date = join_dt + timedelta(days=offset)
 
    
    cur = join_dt
    while cur <= pd.Timestamp(END_DATE):
        # Churners stop after churn_date
        if churn_date and cur > churn_date:
            break
 
        
        monthly_visits = max(0, int(np.random.poisson(freq)))
 
        for _ in range(monthly_visits):
            
            days_in_month = 28
            tx_date = cur + timedelta(days=random.randint(0, days_in_month - 1))
            if tx_date > pd.Timestamp(END_DATE):
                break
 
            ls_stage = ls_lookup.get(tx_date, 0)
 
           
            if channel == "In-store" and ls_stage >= 4:
                if random.random() < 0.40:
                    continue
 
            
            tier_multiplier = {"Bronze": 1.0, "Silver": 1.2, "Gold": 1.5}[cust["loyalty_tier"]]
            order_val = round(
                np.random.lognormal(mean=np.log(110 * tier_multiplier), sigma=0.4), 2
            )
            order_val = max(25.0, min(order_val, 600.0))   # floor R25, cap R600
 
            items = max(1, int(np.random.poisson(2.5)))
 
            transactions.append({
                "transaction_id":    f"T{str(tx_id).zfill(7)}",
                "customer_id":       cid,
                "transaction_date":  tx_date.date(),
                "order_value":       order_val,
                "items_ordered":     items,
                "channel":           channel,
                "day_of_week":       tx_date.day_name(),
                "is_weekend":        tx_date.dayofweek >= 5,
                "loadshedding_stage": ls_stage,
            })
            tx_id += 1
 
        # Advance to next month, feb doesnt have full 30 days so day=1 had to be added.
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1,day=1)
        else:
            cur = cur.replace(month=cur.month + 1,day=1)
 
tx_df = pd.DataFrame(transactions)
tx_df.to_csv("data/transactions.csv", index=False)
print(f"  ✓ {len(tx_df):,} transactions")

#table 3 
print("Generating promotions...")
 
promos = []
for i, (name, ptype, disc, start, end, ch) in enumerate(SA_PROMO_EVENTS, 1):
    promos.append({
        "promo_id":      f"P{str(i).zfill(3)}",
        "promo_name":    name,
        "promo_type":    ptype,
        "discount_pct":  disc,
        "start_date":    start,
        "end_date":      end,
        "channel":       ch,
    })
 
promo_df = pd.DataFrame(promos)
promo_df.to_csv("data/promotions.csv", index=False)
print(f"  ✓ {len(promo_df)} promotions")

#table 4 
print("Generating promo redemptions...")
 

date_to_promos = {}
for _, p in promo_df.iterrows():
    for d in pd.date_range(p["start_date"], p["end_date"]):
        date_to_promos.setdefault(d.date(), []).append(p)
 
redemptions = []
redemption_id = 1
 

tx_df["transaction_date"] = pd.to_datetime(tx_df["transaction_date"]).dt.date
eligible = tx_df[tx_df["transaction_date"].isin(date_to_promos.keys())]
 
for _, tx in eligible.iterrows():
    promos_on_day = date_to_promos[tx["transaction_date"]]
    for p in promos_on_day:
        
        if p["channel"] != "All" and p["channel"] != tx["channel"]:
            continue
 
        
        base_prob = {"Discount": 0.55, "BOGOF": 0.45, "Freebie": 0.65}.get(p["promo_type"], 0.50)
 
        if random.random() < base_prob:
            disc = p["discount_pct"] / 100 if p["promo_type"] == "Discount" else 0
            order_after = round(tx["order_value"] * (1 - disc) * random.uniform(0.95, 1.20), 2)
 
            redemptions.append({
                "redemption_id":    f"R{str(redemption_id).zfill(7)}",
                "customer_id":      tx["customer_id"],
                "promo_id":         p["promo_id"],
                "redemption_date":  tx["transaction_date"],
                "order_value_after": order_after,
            })
            redemption_id += 1
 
redemption_df = pd.DataFrame(redemptions)
redemption_df.to_csv("data/promo_redemptions.csv", index=False)
print(f"  ✓ {len(redemption_df):,} redemptions")
print("\n── RetainIQ Dataset Summary ──────────────────")
print(f"  Customers:      {len(customers):>10,}")
print(f"  Transactions:   {len(tx_df):>10,}")
print(f"  Promotions:     {len(promo_df):>10,}")
print(f"  Redemptions:    {len(redemption_df):>10,}")
print(f"  Churner IDs:    {len(churner_ids):>10,}  (~20% of customers)")
print(f"  Date range:     {START_DATE} → {END_DATE}")
print("  Output:         ./data/")
print("────────────────────────────────────────────────\n")