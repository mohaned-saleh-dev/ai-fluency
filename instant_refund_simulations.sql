-- =============================================================================
-- INSTANT REFUND SIMULATIONS - Data Sizing Queries
-- =============================================================================
-- These queries should be run against the Tamara BigQuery environment
-- using the tamara-data-assistant MCP tool once the connection is restored.
-- =============================================================================

-- STEP 1: Discover relevant tables
-- Run these first to find the right table names for disputes and orders

-- 1a. Find dispute/claim tables
SELECT table_schema, table_name
FROM `tamara-44603.region-EU.INFORMATION_SCHEMA.TABLES`
WHERE (table_name LIKE '%dispute%' OR table_name LIKE '%claim%' OR table_name LIKE '%refund%')
  AND table_schema LIKE 'hatta%'
ORDER BY table_schema, table_name;

-- 1b. Find order tables
SELECT table_schema, table_name
FROM `tamara-44603.region-EU.INFORMATION_SCHEMA.TABLES`
WHERE table_name LIKE '%order%'
  AND table_schema LIKE 'hatta%'
ORDER BY table_schema, table_name;

-- 1c. Find customer/membership tables
SELECT table_schema, table_name
FROM `tamara-44603.region-EU.INFORMATION_SCHEMA.TABLES`
WHERE (table_name LIKE '%customer%' OR table_name LIKE '%member%' OR table_name LIKE '%smart%'
       OR table_name LIKE '%buyer_protection%' OR table_name LIKE '%blacklist%')
  AND table_schema LIKE 'hatta%'
ORDER BY table_schema, table_name;

-- 1d. Find chargeback tables
SELECT table_schema, table_name
FROM `tamara-44603.region-EU.INFORMATION_SCHEMA.TABLES`
WHERE (table_name LIKE '%chargeback%' OR table_name LIKE '%fraud%')
  AND table_schema LIKE 'hatta%'
ORDER BY table_schema, table_name;


-- =============================================================================
-- STEP 2: Get column schemas (use get_columns_of_a_table_in_gbq tool)
-- Replace {schema} and {table} with actual names found in Step 1
-- =============================================================================


-- =============================================================================
-- STEP 3: Base dispute population (last 12 months)
-- This CTE structure will be reused in all simulations.
-- Adjust table/column names after schema discovery.
-- =============================================================================

/*
WITH base_disputes AS (
  SELECT
    d.dispute_id,
    d.order_id,
    d.customer_id,
    d.market,
    d.dispute_reason,
    d.dispute_amount,
    d.currency,
    d.created_at AS dispute_created_at,
    d.status AS dispute_status,
    d.agent_decision,
    d.agent_final_amount,

    -- Order fields
    o.order_amount,
    o.payment_method,
    o.order_created_at,
    DATE_DIFF(d.created_at, o.order_created_at, DAY) AS order_age_days,

    -- Customer fields
    c.is_smart_member,
    CASE WHEN o.payment_method = 'PIF' THEN TRUE ELSE FALSE END AS is_pif,
    (c.is_smart_member OR o.payment_method = 'PIF') AS buyer_protection_eligible,
    c.is_blacklisted,

    -- Dispute history (rolling 365d before this dispute)
    (SELECT COUNT(*)
     FROM disputes d2
     WHERE d2.customer_id = d.customer_id
       AND d2.created_at < d.created_at
       AND d2.created_at >= DATE_SUB(d.created_at, INTERVAL 365 DAY)
    ) AS prior_disputes_365d,

    -- Chargeback history (rolling 180d before this dispute)
    (SELECT COUNT(*)
     FROM chargebacks cb
     WHERE cb.customer_id = d.customer_id
       AND cb.created_at < d.created_at
       AND cb.created_at >= DATE_SUB(d.created_at, INTERVAL 180 DAY)
    ) AS chargebacks_180d,

    -- Whether dispute was ultimately approved/refunded
    CASE WHEN d.status IN ('APPROVED', 'REFUNDED') THEN TRUE ELSE FALSE END AS was_approved,

    -- Merchant tier
    m.risk_tier AS merchant_tier

  FROM disputes d
  JOIN orders o ON d.order_id = o.order_id
  JOIN customers c ON d.customer_id = c.customer_id
  LEFT JOIN merchants m ON o.merchant_id = m.merchant_id
  WHERE d.created_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
    AND d.created_at < CURRENT_DATE()
)
*/


-- =============================================================================
-- STEP 4: SIMULATION SCENARIOS
-- Each scenario applies different eligibility filters on top of base_disputes
-- =============================================================================

/*
-- Scenario Matrix:
-- Dimension 1: Customer Eligibility
--   A) PIF only
--   B) Buyer Protection (Smart OR PIF)
--
-- Dimension 2: Max Dispute Amount (CAP1)
--   i)   500 local
--   ii)  1000 local
--   iii) No cap
--
-- Dimension 3: Max Disputes per Year (N1)
--   a) 1 per year
--   b) 2 per year
--   c) 3 per year
--
-- Dimension 4: Chargeback Check
--   Always: chargebacks_180d = 0
--
-- Dimension 5: Blacklist Check
--   Always: is_blacklisted = false
--
-- Total Scenarios: 2 x 3 x 3 = 18 combinations

SELECT
  customer_cohort,
  cap_amount,
  max_disputes_per_year AS n1,
  COUNT(*) AS total_disputes,
  COUNT(*) FILTER (WHERE eligible) AS eligible_disputes,
  ROUND(100.0 * COUNT(*) FILTER (WHERE eligible) / COUNT(*), 2) AS pct_eligible,
  SUM(CASE WHEN eligible THEN LEAST(dispute_amount, cap_amount) ELSE 0 END) AS total_refund_value,
  AVG(CASE WHEN eligible THEN LEAST(dispute_amount, cap_amount) END) AS avg_refund_value,
  -- Leakage proxy: eligible disputes that were ultimately denied by agents
  COUNT(*) FILTER (WHERE eligible AND NOT was_approved) AS potential_leakage_count,
  SUM(CASE WHEN eligible AND NOT was_approved THEN LEAST(dispute_amount, cap_amount) ELSE 0 END) AS potential_leakage_value,
  -- Breakdown by market
  COUNT(*) FILTER (WHERE eligible AND market = 'SA') AS eligible_sa,
  COUNT(*) FILTER (WHERE eligible AND market = 'AE') AS eligible_ae
FROM simulation_grid
GROUP BY customer_cohort, cap_amount, max_disputes_per_year
ORDER BY customer_cohort, cap_amount, max_disputes_per_year;
*/
