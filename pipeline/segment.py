"""
=========================================================================
RetainIQ — Segment Rules
=========================================================================

Takes the scored customer table and assigns each customer a
recommended marketing action based on:

    - churn_risk_band    (High / Medium / Low)
    - promo_redemption_rate  (are they promo-responsive?)
    - loyalty_tier       (what level of intervention is justified?)
 
Please note - Threshold was adjusted 
"""

import pandas as pd
import numpy as np

PROMO_RESPONSIVE_THRESHOLD = 0.03

HIGH_VALUE_SPEND_THRESHOLD = 5000

def _assign_single_action(row: pd.Series) -> str:
    """
    Assign a recommended action to a single customer row.
 
    Decision logic:
     High      -->  Yes + Gold/Silver   --> Priority discount — high value save 
     High      -->  Yes + Bronze        --> Standard discount offer             
     High      -->  No                  -->  Freebie offer — break the pattern   

     for medium :
    Medium      --> Yes                  -->  Gentle nudge — low discount         
     Medium      -->  No                   -->  Engagement content — no promo yet   

     for low :
     Low        -->  Any                  -->  No action — customer is healthy     
    """

    band = row['churn_risk_band']
    tier = row['loyalty_tier']
    responsive = row['promo_redemption_rate'] >= PROMO_RESPONSIVE_THRESHOLD
    high_value = row['total_spend'] >= HIGH_VALUE_SPEND_THRESHOLD

    if band == 'High':
        if responsive and tier in ('Gold', 'Silver'):
            return f"Priority Discount - 25% off next order"
        elif responsive and tier == 'Bronze':
            return f'Standard Discount -15% off next order'
        else: return f"Freebie Offer - free item with next purchase"

    elif band == 'Medium':
        if responsive:
            return f'Gentle Nudge — 10% off, limited time'
        else:
            return 'Engagement Push — remind them what they are missing'
 
    else:  
        return 'No Action — customer is healthy'
    
def _assign_priority(row: pd.Series) -> str:
    if row ['churn_risk_band'] == 'High' and row['loyalty_tier'] in ('Gold', 'Silver'):
        return 'Priority 1 - Act This Week'
    elif row['churn_risk_band'] == 'High':
        return 'Priority 2 - Act This Week' 
    elif row['churn_risk_band'] == 'Medium':
        return 'Priority 3 - Monitor'
    else:
        return 'Priority 4 -No Action'


def assign_actions(
        scored: pd.DataFrame,
        customers: pd.DataFrame,

) -> pd.DataFrame:
    profile_cols = ['customer_id', 'loyalty_tier', 'province', 'age_group',
                    'preferred_channel', 'gender']
    df = scored.merge(customers[profile_cols], on='customer_id', how='left')

    df['recommended_action'] = df.apply(_assign_single_action, axis=1)
    df['priority']           = df.apply(_assign_priority,       axis=1)
 
    print(f"  Actions assigned: {len(df):,} customers")
 
    return df
def build_segment_summary(actioned: pd.DataFrame, snapshot_date: str) -> dict:
    """
    Build the summary stats that go into the email report body.
 
    Returns a dict with everything the email template needs.
    """
 
    total     = len(actioned)
    high      = actioned[actioned['churn_risk_band'] == 'High']
    medium    = actioned[actioned['churn_risk_band'] == 'Medium']
    low       = actioned[actioned['churn_risk_band'] == 'Low']
 
    
    high_actions = high['recommended_action'].value_counts().to_dict()
 
   
    high_tier = high['loyalty_tier'].value_counts().to_dict()
 
    
    high_province = high['province'].value_counts().head(3).to_dict()
 
    
    high_responsive = (high['promo_redemption_rate'] >= PROMO_RESPONSIVE_THRESHOLD).sum()
    high_not_responsive = len(high) - high_responsive
 
    summary = {
        'snapshot_date':       snapshot_date,
        'total_customers':     total,
 
        'high_count':          len(high),
        'high_pct':            round(len(high) / total * 100, 1),
        'medium_count':        len(medium),
        'medium_pct':          round(len(medium) / total * 100, 1),
        'low_count':           len(low),
        'low_pct':             round(len(low) / total * 100, 1),
 
        'high_actions':        high_actions,
        'high_tier':           high_tier,
        'high_province':       high_province,
        'high_responsive':     high_responsive,
        'high_not_responsive': high_not_responsive,
 
        'p1_count':            (actioned['priority'] == 'P1 — Act This Week').sum(),
        'p2_count':            (actioned['priority'] == 'P2 — Act This Week').sum(),
    }
 
    return summary
 
 
 
if __name__ == '__main__':
 
    print("Loading data...")
    scored    = pd.read_csv('data/scored_customers.csv')
    customers = pd.read_csv('data/customers.csv')
    print(f"  {len(scored):,} scored customers loaded")
 
    print()
    print("Assigning actions...")
    actioned = assign_actions(scored, customers)
 
    print()
    print("── Action Breakdown ")
    action_counts = actioned['recommended_action'].value_counts()
    for action, count in action_counts.items():
        pct = count / len(actioned) * 100
        print(f"  {count:>5,} ({pct:4.1f}%)  {action}")
 
    print()
    print("── Priority Breakdown ")
    priority_counts = actioned['priority'].value_counts().sort_index()
    for priority, count in priority_counts.items():
        print(f"  {count:>5,}  {priority}")
 
    print()
    print("── High Risk Deep Dive ")
    high = actioned[actioned['churn_risk_band'] == 'High']
    print(f"  Total high risk:      {len(high):,}")
    print(f"  Promo responsive:     {(high['promo_redemption_rate'] >= PROMO_RESPONSIVE_THRESHOLD).sum():,}")
    print(f"  Not promo responsive: {(high['promo_redemption_rate'] < PROMO_RESPONSIVE_THRESHOLD).sum():,}")
    print()
    print("  Tier breakdown:")
    for tier, count in high['loyalty_tier'].value_counts().items():
        print(f"    {tier:<10} {count:>4,}")
    print()
    print("  Top provinces:")
    for province, count in high['province'].value_counts().head(3).items():
        print(f"    {province:<20} {count:>4,}")
 
    print()
    print("── Sample Output ───")
    cols = ['customer_id', 'churn_probability', 'churn_risk_band',
            'loyalty_tier', 'recommended_action', 'priority']
    print(actioned[actioned['churn_risk_band'] == 'High'][cols].head(8).to_string(index=False))
 
    actioned.to_csv('data/actioned_customers.csv', index=False)
    print()
    print("Saved to data/actioned_customers.csv")
 