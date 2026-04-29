"""
Instant Refund Simulation Engine
================================
This code is designed to run via the tamara-data-assistant MCP's run_python_analysis tool.
It expects a DataFrame 'df' loaded from the SQL query (provided as the 'query' parameter).

The simulation applies different eligibility parameter combinations and produces
a comprehensive sizing report.
"""

import pandas as pd
import numpy as np
from itertools import product

# ── Simulation Parameters ──────────────────────────────────────────────────────

CUSTOMER_COHORTS = {
    'PIF Only': lambda row: row['is_pif'],
    'Buyer Protection (Smart OR PIF)': lambda row: row['buyer_protection_eligible'],
}

CAP_AMOUNTS = [500, 1000, 99999999]  # 99999999 = effectively no cap
CAP_LABELS = {500: '500', 1000: '1000', 99999999: 'No Cap'}

MAX_DISPUTES_PER_YEAR_N1 = [1, 2, 3]

MAX_INSTANT_REFUNDS_PER_YEAR_N2 = [1, 2, 3]

# Fixed rules (always applied)
# - chargebacks_180d = 0
# - is_blacklisted = false
# - order_age_days <= 14

# ── Apply Eligibility Rules ────────────────────────────────────────────────────

results = []

for cohort_name, cohort_filter in CUSTOMER_COHORTS.items():
    for cap in CAP_AMOUNTS:
        for n1 in MAX_DISPUTES_PER_YEAR_N1:
            for n2 in MAX_INSTANT_REFUNDS_PER_YEAR_N2:
                eligible_mask = (
                    df.apply(cohort_filter, axis=1) &
                    (df['chargebacks_180d'] == 0) &
                    (~df['is_blacklisted']) &
                    (df['order_age_days'] <= 14) &
                    (df['prior_disputes_365d'] < n1) &
                    (df['dispute_amount'] <= cap)
                )

                eligible = df[eligible_mask]
                total = len(df)

                refund_amounts = eligible['dispute_amount'].clip(upper=cap)

                # Leakage proxy: disputes that were NOT approved by agents
                leakage_mask = eligible_mask & (~df['was_approved'])
                leakage = df[leakage_mask]
                leakage_amounts = leakage['dispute_amount'].clip(upper=cap)

                results.append({
                    'cohort': cohort_name,
                    'cap_amount': CAP_LABELS[cap],
                    'n1_max_disputes_yr': n1,
                    'n2_max_instant_refunds_yr': n2,
                    'total_disputes': total,
                    'eligible_count': len(eligible),
                    'eligible_pct': round(100 * len(eligible) / total, 2) if total > 0 else 0,
                    'total_refund_value': round(refund_amounts.sum(), 2),
                    'avg_refund_value': round(refund_amounts.mean(), 2) if len(eligible) > 0 else 0,
                    'median_refund_value': round(refund_amounts.median(), 2) if len(eligible) > 0 else 0,
                    'max_refund_value': round(refund_amounts.max(), 2) if len(eligible) > 0 else 0,
                    'potential_leakage_count': len(leakage),
                    'potential_leakage_value': round(leakage_amounts.sum(), 2),
                    'leakage_rate_pct': round(100 * len(leakage) / len(eligible), 2) if len(eligible) > 0 else 0,
                    'eligible_sa': len(eligible[eligible['market'] == 'SA']),
                    'eligible_ae': len(eligible[eligible['market'] == 'AE']),
                    'refund_value_sa': round(eligible[eligible['market'] == 'SA']['dispute_amount'].clip(upper=cap).sum(), 2),
                    'refund_value_ae': round(eligible[eligible['market'] == 'AE']['dispute_amount'].clip(upper=cap).sum(), 2),
                })

sim_df = pd.DataFrame(results)

# ── Print Summary Tables ───────────────────────────────────────────────────────

print("=" * 120)
print("INSTANT REFUND SIMULATION RESULTS")
print("=" * 120)
print(f"\nTotal disputes in population (last 12 months): {len(df):,}")
print(f"Date range: {df['dispute_created_at'].min()} to {df['dispute_created_at'].max()}")
print(f"Markets: {df['market'].value_counts().to_dict()}")
print(f"Payment methods: {df['payment_method'].value_counts().to_dict()}")
print()

# ── Table 1: Key Scenarios Comparison ──────────────────────────────────────────

print("\n" + "=" * 120)
print("TABLE 1: ALL SCENARIO COMBINATIONS")
print("=" * 120)
cols = ['cohort', 'cap_amount', 'n1_max_disputes_yr', 'n2_max_instant_refunds_yr',
        'eligible_count', 'eligible_pct', 'total_refund_value', 'avg_refund_value',
        'potential_leakage_count', 'potential_leakage_value', 'leakage_rate_pct']
print(sim_df[cols].to_string(index=False))

# ── Table 2: By Market Breakdown ──────────────────────────────────────────────

print("\n" + "=" * 120)
print("TABLE 2: MARKET BREAKDOWN (SA vs AE)")
print("=" * 120)
market_cols = ['cohort', 'cap_amount', 'n1_max_disputes_yr', 'n2_max_instant_refunds_yr',
               'eligible_sa', 'refund_value_sa', 'eligible_ae', 'refund_value_ae']
print(sim_df[market_cols].to_string(index=False))

# ── Table 3: Monthly Distribution for "Recommended" Scenario ──────────────────

print("\n" + "=" * 120)
print("TABLE 3: MONTHLY DISTRIBUTION - Buyer Protection, CAP=1000, N1=3, N2=3")
print("=" * 120)

rec_mask = (
    df.apply(CUSTOMER_COHORTS['Buyer Protection (Smart OR PIF)'], axis=1) &
    (df['chargebacks_180d'] == 0) &
    (~df['is_blacklisted']) &
    (df['order_age_days'] <= 14) &
    (df['prior_disputes_365d'] < 3) &
    (df['dispute_amount'] <= 1000)
)

rec_eligible = df[rec_mask].copy()
rec_eligible['month'] = pd.to_datetime(rec_eligible['dispute_created_at']).dt.to_period('M')
monthly = rec_eligible.groupby('month').agg(
    eligible_count=('dispute_id', 'count'),
    total_refund_value=('dispute_amount', 'sum'),
    avg_refund=('dispute_amount', 'mean'),
    approved_count=('was_approved', 'sum'),
).reset_index()
monthly['leakage_count'] = monthly['eligible_count'] - monthly['approved_count']
monthly['leakage_pct'] = round(100 * monthly['leakage_count'] / monthly['eligible_count'], 2)
print(monthly.to_string(index=False))

# ── Table 4: By Dispute Reason ────────────────────────────────────────────────

print("\n" + "=" * 120)
print("TABLE 4: BY DISPUTE REASON - Buyer Protection, CAP=1000, N1=3, N2=3")
print("=" * 120)

by_reason = rec_eligible.groupby('dispute_reason').agg(
    eligible_count=('dispute_id', 'count'),
    total_refund_value=('dispute_amount', 'sum'),
    avg_refund=('dispute_amount', 'mean'),
    approved_count=('was_approved', 'sum'),
).reset_index()
by_reason['leakage_count'] = by_reason['eligible_count'] - by_reason['approved_count']
by_reason['leakage_pct'] = round(100 * by_reason['leakage_count'] / by_reason['eligible_count'], 2)
print(by_reason.to_string(index=False))

# ── Table 5: By Payment Method ────────────────────────────────────────────────

print("\n" + "=" * 120)
print("TABLE 5: BY PAYMENT METHOD - Buyer Protection, CAP=1000, N1=3, N2=3")
print("=" * 120)

by_pm = rec_eligible.groupby('payment_method').agg(
    eligible_count=('dispute_id', 'count'),
    total_refund_value=('dispute_amount', 'sum'),
    avg_refund=('dispute_amount', 'mean'),
).reset_index()
print(by_pm.to_string(index=False))

# ── Table 6: Sensitivity Sweep on CAP ────────────────────────────────────────

print("\n" + "=" * 120)
print("TABLE 6: SENSITIVITY SWEEP ON CAP AMOUNT (Buyer Protection, N1=3, N2=3)")
print("=" * 120)

for cap_val in [100, 150, 200, 300, 500, 750, 1000, 1500, 2000]:
    cap_mask = rec_mask & (df['dispute_amount'] <= cap_val)
    cap_eligible = df[cap_mask]
    refunds = cap_eligible['dispute_amount'].clip(upper=cap_val)
    leak = cap_eligible[~cap_eligible['was_approved']]
    leak_refunds = leak['dispute_amount'].clip(upper=cap_val)
    print(f"  CAP={cap_val:>5}: eligible={len(cap_eligible):>6}, "
          f"refund_value={refunds.sum():>12,.2f}, "
          f"avg={refunds.mean():>8,.2f} | "
          f"leakage_count={len(leak):>5}, leakage_value={leak_refunds.sum():>10,.2f}")

print("\n" + "=" * 120)
print("SIMULATION COMPLETE")
print("=" * 120)
