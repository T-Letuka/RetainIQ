"""
RetainIQ — Feature Engineering
================================
Takes raw transaction, customer, and redemption data and produces
a single model-ready feature table: one row per customer.

"""

import pandas as pd
import numpy as np
from datetime import timedelta


CHURN_DAYS       = 45    
WINDOW_90        = 90    
WINDOW_30        = 30    
HIGH_LS_STAGE    = 4     


def build_features(
    snapshot_date: pd.Timestamp,
    transactions:  pd.DataFrame,
    customers:     pd.DataFrame,
    redemptions:   pd.DataFrame,
) -> pd.DataFrame:
    """
    Build one feature row per customer relative to snapshot_date.

    Parameters
    ----------
    snapshot_date : pd.Timestamp
        The "as of" date — treat this as today. Only transactions
        on or before this date are used. This is what makes the
        pipeline reusable week over week.
    transactions  : raw transactions DataFrame
    customers     : raw customers DataFrame
    redemptions   : raw redemptions DataFrame
    """

    tx = transactions[transactions['transaction_date'] <= snapshot_date].copy()
    rd = redemptions[redemptions['redemption_date'] <= snapshot_date].copy()

    cutoff_90 = snapshot_date - timedelta(days=WINDOW_90)
    cutoff_30 = snapshot_date - timedelta(days=WINDOW_30)

    tx_90 = tx[tx['transaction_date'] >= cutoff_90]
    tx_30 = tx[tx['transaction_date'] >= cutoff_30]
    tx_prev30 = tx[
        (tx['transaction_date'] >= snapshot_date - timedelta(days=60)) &
        (tx['transaction_date'] <  snapshot_date - timedelta(days=30))
    ]


    rfm = tx.groupby('customer_id').agg(
        last_transaction_date = ('transaction_date', 'max'),
        total_transactions    = ('transaction_id',   'count'),
        total_spend           = ('order_value',      'sum'),
    ).reset_index()

    rfm['recency_days'] = (snapshot_date - rfm['last_transaction_date']).dt.days
    rfm['tenure_days']  = (
        snapshot_date - tx.groupby('customer_id')['transaction_date'].min()
    ).dt.days.values

    rfm['avg_monthly_frequency'] = (
        rfm['total_transactions'] /
        (rfm['tenure_days'] / 30).clip(lower=1)
    ).round(2)

    rfm['avg_order_value'] = (rfm['total_spend'] / rfm['total_transactions']).round(2)

   

    recent_90 = tx_90.groupby('customer_id').agg(
        tx_count_90d      = ('transaction_id', 'count'),
        avg_order_val_90d = ('order_value',    'mean'),
        total_spend_90d   = ('order_value',    'sum'),
    ).reset_index()
    recent_90['avg_order_val_90d'] = recent_90['avg_order_val_90d'].round(2)


    freq_recent = tx_30.groupby('customer_id')['transaction_id'].count().rename('freq_last_30')
    freq_prior  = tx_prev30.groupby('customer_id')['transaction_id'].count().rename('freq_prior_30')

    trend = pd.concat([freq_recent, freq_prior], axis=1).fillna(0)
    trend['frequency_trend'] = (trend['freq_last_30'] - trend['freq_prior_30']).astype(int)
    trend = trend[['frequency_trend']].reset_index()


    total_promo_opps = (
        tx.groupby('customer_id')['transaction_id'].count()
        .rename('total_tx_for_promo_rate')
    )

    cust_redemptions = rd.groupby('customer_id').agg(
        promo_redemption_count  = ('redemption_id',    'count'),
        avg_spend_after_promo   = ('order_value_after', 'mean'),
    ).reset_index()
    cust_redemptions['avg_spend_after_promo'] = cust_redemptions['avg_spend_after_promo'].round(2)

    promo_features = cust_redemptions.merge(
        total_promo_opps.reset_index(), on='customer_id', how='right'
    ).fillna(0)

    promo_features['promo_redemption_rate'] = (
        promo_features['promo_redemption_count'] /
        promo_features['total_tx_for_promo_rate']
    ).round(4)

    promo_features = promo_features[
        ['customer_id', 'promo_redemption_count',
         'promo_redemption_rate', 'avg_spend_after_promo']
    ]


    ls = tx.groupby('customer_id').agg(
        avg_loadshedding_stage    = ('loadshedding_stage', 'mean'),
        pct_high_loadshedding_txn = ('loadshedding_stage',
                                     lambda x: (x >= HIGH_LS_STAGE).mean()),
    ).reset_index()
    ls['avg_loadshedding_stage']    = ls['avg_loadshedding_stage'].round(2)
    ls['pct_high_loadshedding_txn'] = ls['pct_high_loadshedding_txn'].round(4)


    weekend = tx.groupby('customer_id').agg(
        pct_weekend_txn = ('is_weekend', 'mean'),
    ).reset_index()
    weekend['pct_weekend_txn'] = weekend['pct_weekend_txn'].round(4)



    profile = customers[['customer_id', 'loyalty_tier',
                          'preferred_channel', 'age_group', 'province']].copy()

    tier_map    = {'Bronze': 0, 'Silver': 1, 'Gold': 2}
    channel_map = {'In-store': 0, 'Drive-thru': 1, 'App': 2}
    age_map     = {'18-25': 0, '26-35': 1, '36-50': 2, '50+': 3}

    profile['tier_encoded']    = profile['loyalty_tier'].map(tier_map)
    profile['channel_encoded'] = profile['preferred_channel'].map(channel_map)
    profile['age_encoded']     = profile['age_group'].map(age_map)

    profile = profile[['customer_id', 'tier_encoded',
                        'channel_encoded', 'age_encoded']]



    rfm['churned'] = (rfm['recency_days'] >= CHURN_DAYS).astype(int)


    feature_table = (
        rfm[[
            'customer_id', 'recency_days', 'total_transactions',
            'total_spend', 'avg_monthly_frequency', 'avg_order_value',
            'tenure_days', 'churned'
        ]]
        .merge(recent_90,    on='customer_id', how='left')
        .merge(trend,        on='customer_id', how='left')
        .merge(promo_features, on='customer_id', how='left')
        .merge(ls,           on='customer_id', how='left')
        .merge(weekend,      on='customer_id', how='left')
        .merge(profile,      on='customer_id', how='left')
    )

    fill_zero_cols = [
        'tx_count_90d', 'avg_order_val_90d', 'total_spend_90d',
        'frequency_trend', 'promo_redemption_count',
        'promo_redemption_rate', 'avg_spend_after_promo',
    ]
    feature_table[fill_zero_cols] = feature_table[fill_zero_cols].fillna(0)

    print(f"  Feature table built: {len(feature_table):,} customers "
          f"| {feature_table.shape[1]} columns "
          f"| churn rate: {feature_table['churned'].mean()*100:.1f}%")

    return feature_table




if __name__ == '__main__':
    import os

    print("Loading data...")
    customers    = pd.read_csv('data/customers.csv',     parse_dates=['join_date'])
    transactions = pd.read_csv('data/transactions.csv',  parse_dates=['transaction_date'])
    redemptions  = pd.read_csv('data/promo_redemptions.csv', parse_dates=['redemption_date'])

    snapshot = pd.Timestamp('2024-12-31')
    print(f"Building features as of {snapshot.date()}...")

    features = build_features(snapshot, transactions, customers, redemptions)

    os.makedirs('data', exist_ok=True)
    features.to_csv('data/features.csv', index=False)

    print()
    print("── Feature Table Preview ───────────────────────────────")
    print(features.head(5).to_string())
    print()
    print("── Feature Summary ─────────────────────────────────────")
    print(features.describe().round(2).to_string())
    print()
    print("── Null Check ──────────────────────────────────────────")
    nulls = features.isnull().sum()
    print(nulls[nulls > 0] if nulls.any() else "  No nulls — clean feature table.")
    print()
    print(f"Saved to data/features.csv")


