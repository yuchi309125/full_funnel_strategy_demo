-- ============================================================
-- schema.sql
-- Multi-client ad campaign database schema
-- ============================================================

-- Drop tables in reverse dependency order for clean reloads
DROP TABLE IF EXISTS flagged_rows;
DROP TABLE IF EXISTS ad_performance;
DROP TABLE IF EXISTS campaigns;
DROP TABLE IF EXISTS clients;


-- ------------------------------------------------------------
-- clients
-- One row per advertiser. Designed for multi-client use.
-- ------------------------------------------------------------
CREATE TABLE clients (
    client_id    INTEGER PRIMARY KEY,
    client_name  TEXT    NOT NULL,
    industry     TEXT
);


-- ------------------------------------------------------------
-- campaigns
-- One row per campaign. Links to clients via client_id.
-- inferred_stage is derived from observed behavior since the
-- dataset does not include an objective field.
-- ------------------------------------------------------------
CREATE TABLE campaigns (
    campaign_id      INTEGER PRIMARY KEY,
    client_id        INTEGER NOT NULL REFERENCES clients(client_id),
    xyz_campaign_id  INTEGER NOT NULL UNIQUE,
    inferred_stage   TEXT    NOT NULL CHECK (inferred_stage IN ('Awareness', 'Consideration', 'Conversion'))
);


-- ------------------------------------------------------------
-- ad_performance
-- One row per ad per audience segment (age x gender x interest).
-- Links to campaigns via campaign_id.
-- ------------------------------------------------------------
CREATE TABLE ad_performance (
    ad_id                INTEGER PRIMARY KEY,
    campaign_id          INTEGER NOT NULL REFERENCES campaigns(campaign_id),
    fb_campaign_id       INTEGER,
    age                  TEXT,
    gender               TEXT    CHECK (gender IN ('M', 'F')),
    interest             INTEGER,
    impressions          INTEGER,
    clicks               INTEGER,
    spent                REAL,
    total_conversion     INTEGER,
    approved_conversion  INTEGER
);


-- ------------------------------------------------------------
-- flagged_rows
-- Output of qa_check.py. One row per flagged ad per rule.
-- ------------------------------------------------------------
CREATE TABLE flagged_rows (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ad_id           INTEGER NOT NULL REFERENCES ad_performance(ad_id),
    rule            TEXT    NOT NULL,
    description     TEXT,
    recommendation  TEXT
);


-- ============================================================
-- Views
-- ============================================================

-- funnel_summary
-- Per-campaign funnel metrics with stage-appropriate KPIs.
-- Joining ad_performance -> campaigns -> clients.
CREATE VIEW funnel_summary AS
SELECT
    c.client_name,
    cp.inferred_stage,
    cp.xyz_campaign_id,
    COUNT(DISTINCT ap.ad_id)                                        AS ad_count,
    SUM(ap.impressions)                                             AS impressions,
    SUM(ap.clicks)                                                  AS clicks,
    ROUND(SUM(ap.spent), 2)                                         AS spent,
    SUM(ap.total_conversion)                                        AS total_conversions,
    SUM(ap.approved_conversion)                                     AS approved_conversions,
    -- Awareness KPI
    ROUND(SUM(ap.spent) / NULLIF(SUM(ap.impressions), 0) * 1000, 2) AS cpm,
    -- Consideration KPI
    ROUND(SUM(ap.clicks) * 1.0 / NULLIF(SUM(ap.impressions), 0) * 100, 2) AS ctr_pct,
    ROUND(SUM(ap.spent) / NULLIF(SUM(ap.clicks), 0), 2)            AS cpc,
    -- Conversion KPI
    ROUND(SUM(ap.approved_conversion) * 1.0 / NULLIF(SUM(ap.total_conversion), 0) * 100, 2) AS approval_rate_pct,
    ROUND(SUM(ap.spent) / NULLIF(SUM(ap.approved_conversion), 0), 2) AS cpa
FROM ad_performance ap
JOIN campaigns  cp ON ap.campaign_id    = cp.campaign_id
JOIN clients    c  ON cp.client_id      = c.client_id
GROUP BY cp.inferred_stage, cp.xyz_campaign_id, c.client_name;
