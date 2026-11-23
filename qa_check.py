import pandas as pd
import argparse
import os

RULES = {
    "clicks_exceed_impressions": {
        "description": "Clicks > Impressions (physically impossible)",
        "recommendation": "Exclude — likely a tracking error",
    },
    "conversions_exceed_impressions": {
        "description": "Total_Conversion > Impressions (conversions cannot exceed total exposure)",
        "recommendation": "Exclude — likely a tracking error",
    },
    "conversions_exceed_clicks": {
        "description": "Total_Conversion > Clicks (may be view-through attribution or a tracking error)",
        "recommendation": "Investigate — confirm attribution settings before excluding",
    },
    "approved_exceed_clicks": {
        "description": "Approved_Conversion > Clicks (may be view-through attribution or a tracking error)",
        "recommendation": "Investigate — confirm attribution settings before excluding",
    },
    "approved_exceed_total_conversion": {
        "description": "Approved_Conversion > Total_Conversion (Approved should be a subset of Total)",
        "recommendation": "Exclude — inconsistent metric definition",
    },
    "clicks_without_spend": {
        "description": "Clicks > 0 but Spent = 0 (clicks recorded but no spend in a paid campaign)",
        "recommendation": "Investigate — may indicate tracking or billing discrepancy",
    },
    "spend_without_impressions": {
        "description": "Spend > 0 but Impressions = 0 (budget spent but no recorded exposure)",
        "recommendation": "Investigate — ad may not have served correctly",
    },
    "negative_values": {
        "description": "Negative values in Impressions, Clicks, Spent, Total_Conversion, or Approved_Conversion",
        "recommendation": "Exclude — invalid data",
    },
    "missing_values": {
        "description": "Missing values in any column",
        "recommendation": "Investigate — may indicate incomplete data pipeline",
    },
    "duplicate_rows": {
        "description": "Duplicate rows (same ad_id appearing more than once)",
        "recommendation": "Deduplicate — keep first occurrence",
    },
}


def run_checks(df):
    flagged = []

    # Rule 1: Clicks > Impressions
    mask = df["Clicks"] > df["Impressions"]
    if mask.any():
        rows = df[mask].copy()
        rows["rule"] = "clicks_exceed_impressions"
        rows["description"] = RULES["clicks_exceed_impressions"]["description"]
        rows["recommendation"] = RULES["clicks_exceed_impressions"]["recommendation"]
        flagged.append(rows)

    # Rule 2: Total_Conversion > Impressions (severe — exclude)
    mask = df["Total_Conversion"] > df["Impressions"]
    if mask.any():
        rows = df[mask].copy()
        rows["rule"] = "conversions_exceed_impressions"
        rows["description"] = RULES["conversions_exceed_impressions"]["description"]
        rows["recommendation"] = RULES["conversions_exceed_impressions"]["recommendation"]
        flagged.append(rows)

    # Rule 3: Total_Conversion > Clicks but <= Impressions (investigate — may be attribution)
    mask = (df["Total_Conversion"] > df["Clicks"]) & (df["Total_Conversion"] <= df["Impressions"])
    if mask.any():
        rows = df[mask].copy()
        rows["rule"] = "conversions_exceed_clicks"
        rows["description"] = RULES["conversions_exceed_clicks"]["description"]
        rows["recommendation"] = RULES["conversions_exceed_clicks"]["recommendation"]
        flagged.append(rows)

    # Rule 4: Approved_Conversion > Clicks but <= Impressions (investigate — may be attribution)
    mask = (df["Approved_Conversion"] > df["Clicks"]) & (df["Approved_Conversion"] <= df["Impressions"])
    if mask.any():
        rows = df[mask].copy()
        rows["rule"] = "approved_exceed_clicks"
        rows["description"] = RULES["approved_exceed_clicks"]["description"]
        rows["recommendation"] = RULES["approved_exceed_clicks"]["recommendation"]
        flagged.append(rows)

    # Rule 5: Approved_Conversion > Total_Conversion
    mask = df["Approved_Conversion"] > df["Total_Conversion"]
    if mask.any():
        rows = df[mask].copy()
        rows["rule"] = "approved_exceed_total_conversion"
        rows["description"] = RULES["approved_exceed_total_conversion"]["description"]
        rows["recommendation"] = RULES["approved_exceed_total_conversion"]["recommendation"]
        flagged.append(rows)

    # Rule 6: Clicks > 0 but Spent = 0
    mask = (df["Clicks"] > 0) & (df["Spent"] == 0)
    if mask.any():
        rows = df[mask].copy()
        rows["rule"] = "clicks_without_spend"
        rows["description"] = RULES["clicks_without_spend"]["description"]
        rows["recommendation"] = RULES["clicks_without_spend"]["recommendation"]
        flagged.append(rows)

    # Rule 7: Spend > 0 but Impressions = 0
    mask = (df["Spent"] > 0) & (df["Impressions"] == 0)
    if mask.any():
        rows = df[mask].copy()
        rows["rule"] = "spend_without_impressions"
        rows["description"] = RULES["spend_without_impressions"]["description"]
        rows["recommendation"] = RULES["spend_without_impressions"]["recommendation"]
        flagged.append(rows)

    # Rule 8: Negative values
    numeric_cols = ["Impressions", "Clicks", "Spent", "Total_Conversion", "Approved_Conversion"]
    mask = (df[numeric_cols] < 0).any(axis=1)
    if mask.any():
        rows = df[mask].copy()
        rows["rule"] = "negative_values"
        rows["description"] = RULES["negative_values"]["description"]
        rows["recommendation"] = RULES["negative_values"]["recommendation"]
        flagged.append(rows)

    # Rule 9: Missing values
    mask = df.isnull().any(axis=1)
    if mask.any():
        rows = df[mask].copy()
        rows["rule"] = "missing_values"
        rows["description"] = RULES["missing_values"]["description"]
        rows["recommendation"] = RULES["missing_values"]["recommendation"]
        flagged.append(rows)

    # Rule 10: Duplicate ad_id
    mask = df.duplicated(subset=["ad_id"], keep=False)
    if mask.any():
        rows = df[mask].copy()
        rows["rule"] = "duplicate_rows"
        rows["description"] = RULES["duplicate_rows"]["description"]
        rows["recommendation"] = RULES["duplicate_rows"]["recommendation"]
        flagged.append(rows)

    return pd.concat(flagged, ignore_index=True) if flagged else pd.DataFrame()


def print_summary(df, flagged):
    print(f"\nTotal rows: {len(df)}")
    print(f"Flagged rows: {len(flagged)}\n")

    if flagged.empty:
        print("No issues found.")
        return

    summary = flagged.groupby("rule").agg(
        count=("ad_id", "count"),
        description=("description", "first"),
        recommendation=("recommendation", "first"),
    ).reset_index()

    for _, row in summary.iterrows():
        print(f"[{row['rule']}]")
        print(f"  Count       : {row['count']}")
        print(f"  Description : {row['description']}")
        print(f"  Action      : {row['recommendation']}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Run data quality checks on ad campaign data.")
    parser.add_argument("--input", required=True, help="Path to input CSV file")
    parser.add_argument("--output", required=True, help="Directory to write flagged rows CSV")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    flagged = run_checks(df)

    print_summary(df, flagged)

    if not flagged.empty:
        os.makedirs(args.output, exist_ok=True)
        output_path = os.path.join(args.output, "flagged_rows.csv")
        flagged.to_csv(output_path, index=False)
        print(f"Flagged rows saved to: {output_path}")


if __name__ == "__main__":
    main()
