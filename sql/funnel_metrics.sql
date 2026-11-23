-- ============================================================
-- funnel_metrics.sql
-- Full funnel analysis queries
-- Demonstrates: CTEs, multiple JOINs, CASE WHEN,
--               window functions (RANK, SUM OVER), HAVING
-- ============================================================


-- ------------------------------------------------------------
-- Query 1: Funnel overview
-- Shows each stage's volume and core KPI side by side.
-- Uses CASE WHEN to label which KPI matters per stage.
-- ------------------------------------------------------------
SELECT
    cp.inferred_stage,
    SUM(ap.impressions)                                                      AS impressions,
    SUM(ap.clicks)                                                           AS clicks,
    SUM(ap.approved_conversion)                                              AS approved_conversions,
    ROUND(SUM(ap.spent), 2)                                                  AS total_spent,
    CASE cp.inferred_stage
        WHEN 'Awareness'     THEN ROUND(SUM(ap.spent) / NULLIF(SUM(ap.impressions), 0) * 1000, 2)
        WHEN 'Consideration' THEN ROUND(SUM(ap.clicks) * 1.0 / NULLIF(SUM(ap.impressions), 0) * 100, 2)
        WHEN 'Conversion'    THEN ROUND(SUM(ap.spent) / NULLIF(SUM(ap.approved_conversion), 0), 2)
    END                                                                      AS primary_kpi,
    CASE cp.inferred_stage
        WHEN 'Awareness'     THEN 'CPM'
        WHEN 'Consideration' THEN 'CTR %'
        WHEN 'Conversion'    THEN 'CPA'
    END                                                                      AS kpi_label
FROM ad_performance ap
JOIN campaigns cp ON ap.campaign_id = cp.campaign_id
GROUP BY cp.inferred_stage
ORDER BY
    CASE cp.inferred_stage
        WHEN 'Awareness'     THEN 1
        WHEN 'Consideration' THEN 2
        WHEN 'Conversion'    THEN 3
    END;


-- ------------------------------------------------------------
-- Query 2: Budget share vs conversion share by age group
-- Uses CTEs to calculate each metric separately, then JOINs
-- them together for comparison.
-- Core of Finding 1 in the analysis.
-- ------------------------------------------------------------
WITH awareness_spend AS (
    SELECT
        ap.age,
        SUM(ap.spent)                                        AS age_spend,
        SUM(SUM(ap.spent)) OVER ()                           AS total_spend,
        ROUND(SUM(ap.spent) / SUM(SUM(ap.spent)) OVER () * 100, 1) AS budget_share_pct
    FROM ad_performance ap
    JOIN campaigns cp ON ap.campaign_id = cp.campaign_id
    WHERE cp.inferred_stage = 'Awareness'
    GROUP BY ap.age
),
conversion_share AS (
    SELECT
        ap.age,
        SUM(ap.approved_conversion)                          AS age_approved,
        SUM(SUM(ap.approved_conversion)) OVER ()             AS total_approved,
        ROUND(SUM(ap.approved_conversion) * 1.0 / SUM(SUM(ap.approved_conversion)) OVER () * 100, 1) AS conv_share_pct
    FROM ad_performance ap
    JOIN campaigns cp ON ap.campaign_id = cp.campaign_id
    GROUP BY ap.age
)
SELECT
    a.age,
    a.budget_share_pct,
    c.conv_share_pct,
    ROUND(c.conv_share_pct - a.budget_share_pct, 1)          AS efficiency_gap
FROM awareness_spend a
JOIN conversion_share c ON a.age = c.age
ORDER BY efficiency_gap DESC;


-- ------------------------------------------------------------
-- Query 3: Approval rate by age group with rank
-- Uses window function RANK() to order segments by conversion
-- quality. Filters out segments with fewer than 5 conversions
-- using HAVING to avoid drawing conclusions from small samples.
-- ------------------------------------------------------------
WITH approval_by_age AS (
    SELECT
        ap.age,
        SUM(ap.total_conversion)                             AS total_conversions,
        SUM(ap.approved_conversion)                          AS approved_conversions,
        ROUND(SUM(ap.approved_conversion) * 1.0 / NULLIF(SUM(ap.total_conversion), 0) * 100, 1) AS approval_rate_pct
    FROM ad_performance ap
    GROUP BY ap.age
    HAVING SUM(ap.total_conversion) >= 5
)
SELECT
    age,
    total_conversions,
    approved_conversions,
    approval_rate_pct,
    RANK() OVER (ORDER BY approval_rate_pct DESC)            AS quality_rank
FROM approval_by_age
ORDER BY quality_rank;


-- ------------------------------------------------------------
-- Query 4: Flag rate per campaign
-- LEFT JOINs ad_performance to flagged_rows so campaigns with
-- zero flags still appear. Shows data quality context alongside
-- performance metrics.
-- ------------------------------------------------------------
SELECT
    cp.inferred_stage,
    cp.xyz_campaign_id,
    COUNT(DISTINCT ap.ad_id)                                 AS total_ads,
    COUNT(DISTINCT fr.ad_id)                                 AS flagged_ads,
    ROUND(COUNT(DISTINCT fr.ad_id) * 1.0 / COUNT(DISTINCT ap.ad_id) * 100, 1) AS flag_rate_pct
FROM ad_performance ap
JOIN  campaigns  cp ON ap.campaign_id = cp.campaign_id
LEFT JOIN flagged_rows fr ON ap.ad_id = fr.ad_id
GROUP BY cp.inferred_stage, cp.xyz_campaign_id
ORDER BY flag_rate_pct DESC;
