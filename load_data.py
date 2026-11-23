import sqlite3
import pandas as pd
import os

DB_PATH = "data/campaign.db"
CSV_PATH = "KAG_conversion_data.csv"
SCHEMA_PATH = "sql/schema.sql"
FLAGGED_PATH = "data/flagged/flagged_rows.csv"

CAMPAIGN_MAP = {
    1178: ("Awareness",     1),
    936:  ("Consideration", 1),
    916:  ("Conversion",    1),
}

os.makedirs("data", exist_ok=True)

conn = sqlite3.connect(DB_PATH)

# Apply schema
with open(SCHEMA_PATH) as f:
    conn.executescript(f.read())

# Seed clients table
conn.execute("INSERT OR IGNORE INTO clients (client_id, client_name, industry) VALUES (1, 'XYZ Company', 'Unknown')")

# Seed campaigns table
for xyz_id, (stage, client_id) in CAMPAIGN_MAP.items():
    conn.execute(
        "INSERT OR IGNORE INTO campaigns (client_id, xyz_campaign_id, inferred_stage) VALUES (?, ?, ?)",
        (client_id, xyz_id, stage)
    )
conn.commit()

# Load campaign_id lookup
campaign_id_map = {
    row[0]: row[1]
    for row in conn.execute("SELECT xyz_campaign_id, campaign_id FROM campaigns")
}

# Load ad_performance
df = pd.read_csv(CSV_PATH)
df["campaign_id"] = df["xyz_campaign_id"].map(campaign_id_map)
df = df.rename(columns={
    "Impressions":          "impressions",
    "Clicks":               "clicks",
    "Spent":                "spent",
    "Total_Conversion":     "total_conversion",
    "Approved_Conversion":  "approved_conversion",
    "fb_campaign_id":       "fb_campaign_id",
})
df[["ad_id", "campaign_id", "fb_campaign_id", "age", "gender", "interest",
    "impressions", "clicks", "spent", "total_conversion", "approved_conversion"]].to_sql(
    "ad_performance", conn, if_exists="append", index=False
)

# Load flagged rows if QA has been run
if os.path.exists(FLAGGED_PATH):
    flagged = pd.read_csv(FLAGGED_PATH)[["ad_id", "rule", "description", "recommendation"]]
    flagged.to_sql("flagged_rows", conn, if_exists="append", index=False)
    print(f"Loaded {len(flagged)} flagged rows")

conn.commit()
conn.close()
print(f"Database built at {DB_PATH}")
