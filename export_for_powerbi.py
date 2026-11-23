import pandas as pd
import os

df = pd.read_csv("KAG_conversion_data.csv")
stage_map = {916: "Conversion", 936: "Consideration", 1178: "Awareness"}
df["stage"] = df["xyz_campaign_id"].map(stage_map)

os.makedirs("data/powerbi", exist_ok=True)

# --- 1. Funnel stage overview ---
stage = df.groupby("stage").agg(
    impressions=("Impressions", "sum"),
    clicks=("Clicks", "sum"),
    spent=("Spent", "sum"),
    total_conversions=("Total_Conversion", "sum"),
    approved_conversions=("Approved_Conversion", "sum"),
).reset_index()
stage["CTR_pct"]          = (stage["clicks"] / stage["impressions"] * 100).round(3)
stage["CPM"]              = (stage["spent"] / stage["impressions"] * 1000).round(2)
stage["CPC"]              = (stage["spent"] / stage["clicks"]).round(2)
stage["CPA"]              = (stage["spent"] / stage["approved_conversions"]).round(2)
stage["approval_rate_pct"] = (stage["approved_conversions"] / stage["total_conversions"] * 100).round(1)
stage["budget_share_pct"] = (stage["spent"] / stage["spent"].sum() * 100).round(1)
stage["stage_order"] = stage["stage"].map({"Awareness": 1, "Consideration": 2, "Conversion": 3})
stage = stage.sort_values("stage_order").drop(columns="stage_order")
stage.to_csv("data/powerbi/funnel_stage_overview.csv", index=False)
print("Exported: funnel_stage_overview.csv")

# --- 2. Budget share vs conversion share by age ---
total_spent = df[df["stage"] == "Awareness"]["Spent"].sum()
budget_by_age = (
    df[df["stage"] == "Awareness"]
    .groupby("age")["Spent"].sum()
    .reset_index()
    .rename(columns={"Spent": "awareness_spend"})
)
budget_by_age["budget_share_pct"] = (budget_by_age["awareness_spend"] / total_spent * 100).round(1)

total_approved = df["Approved_Conversion"].sum()
conv_by_age = (
    df.groupby("age")["Approved_Conversion"].sum()
    .reset_index()
    .rename(columns={"Approved_Conversion": "approved_conversions"})
)
conv_by_age["conv_share_pct"] = (conv_by_age["approved_conversions"] / total_approved * 100).round(1)

age_alignment = budget_by_age.merge(conv_by_age, on="age")
age_alignment["efficiency_gap"] = (age_alignment["conv_share_pct"] - age_alignment["budget_share_pct"]).round(1)
age_alignment.to_csv("data/powerbi/age_budget_vs_conversion.csv", index=False)
print("Exported: age_budget_vs_conversion.csv")

# --- 3. Approval rate by age ---
approval = (
    df.groupby("age")
    .agg(total_conv=("Total_Conversion", "sum"), approved_conv=("Approved_Conversion", "sum"))
    .reset_index()
)
approval["approval_rate_pct"] = (approval["approved_conv"] / approval["total_conv"] * 100).round(1)
approval["quality_rank"] = approval["approval_rate_pct"].rank(ascending=False).astype(int)
approval.to_csv("data/powerbi/approval_rate_by_age.csv", index=False)
print("Exported: approval_rate_by_age.csv")

# --- 4. KPI by age and gender ---
age_gender = (
    df.groupby(["stage", "age", "gender"])
    .agg(
        impressions=("Impressions", "sum"),
        clicks=("Clicks", "sum"),
        spent=("Spent", "sum"),
        approved_conv=("Approved_Conversion", "sum"),
    )
    .reset_index()
)
age_gender["CPA"] = (age_gender["spent"] / age_gender["approved_conv"].replace(0, pd.NA)).round(2)
age_gender["CTR_pct"] = (age_gender["clicks"] / age_gender["impressions"] * 100).round(3)
age_gender.to_csv("data/powerbi/kpi_by_age_gender.csv", index=False)
print("Exported: kpi_by_age_gender.csv")

# --- 5. QA flag summary ---
flagged_path = "data/flagged/flagged_rows.csv"
if os.path.exists(flagged_path):
    flagged = pd.read_csv(flagged_path)
    flag_summary = flagged.groupby("rule").agg(count=("ad_id", "count")).reset_index()
    flag_summary.to_csv("data/powerbi/qa_flag_summary.csv", index=False)
    print("Exported: qa_flag_summary.csv")
else:
    print("Skipped qa_flag_summary.csv (run qa_check.py first)")

print("\nAll exports saved to data/powerbi/")
print("In Power BI: Get Data > Text/CSV, import each file.")
