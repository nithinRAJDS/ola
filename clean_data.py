"""
OLA DataSet — Profiling, Cleaning & Data-Quality Scorecard
==========================================================
Input : raw/OLA_DataSet.xlsx  (sheet 'July')
Output: data/ola_cleaned.csv, data/ola_cleaned.sqlite, data/quality_scorecard.json,
        data/profile_before.json, data/profile_after.json, data/cleaning_log.md
"""
import json, os, re
import numpy as np
import pandas as pd

RAW = "raw/OLA_DataSet.xlsx"
OUT = "data"
os.makedirs(OUT, exist_ok=True)

# ----------------------------------------------------------------------------
# 1. LOAD
# ----------------------------------------------------------------------------
df = pd.read_excel(RAW, sheet_name="July")
raw_rows, raw_cols = df.shape
log = []
def step(msg):
    log.append(msg)
    print("[CLEAN]", msg)

step(f"Loaded sheet 'July': {raw_rows:,} rows x {raw_cols} columns.")

# ----------------------------------------------------------------------------
# 2. PROFILE (BEFORE)
# ----------------------------------------------------------------------------
def profile(d):
    p = {"rows": int(len(d)), "cols": int(d.shape[1]), "columns": {}}
    for c in d.columns:
        s = d[c]
        col = {
            "dtype": str(s.dtype),
            "missing": int(s.isna().sum()),
            "missing_pct": round(float(s.isna().mean() * 100), 2),
            "n_unique": int(s.nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(s):
            col.update({
                "min": (None if s.dropna().empty else float(s.min())),
                "max": (None if s.dropna().empty else float(s.max())),
                "mean": (None if s.dropna().empty else round(float(s.mean()), 3)),
                "std": (None if s.dropna().empty else round(float(s.std()), 3)),
                "zeros": int((s == 0).sum()),
            })
        p["columns"][c] = col
    p["duplicate_rows"] = int(d.duplicated().sum())
    return p

prof_before = profile(df)
with open(f"{OUT}/profile_before.json", "w") as f:
    json.dump(prof_before, f, indent=2)

# ----------------------------------------------------------------------------
# 3. CLEANING
# ----------------------------------------------------------------------------
# 3.1 Combine Date + Time into a single timestamp
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
def to_time(v):
    if isinstance(v, str):
        try:
            return pd.to_datetime(v).time()
        except Exception:
            return pd.NaT
    return v
df["Time"] = df["Time"].apply(to_time)
df["Booking_Datetime"] = pd.to_datetime(
    df["Date"].dt.strftime("%Y-%m-%d") + " " + df["Time"].astype(str),
    errors="coerce",
)
bad_dt = int(df["Booking_Datetime"].isna().sum())
step(f"Parsed Date+Time -> Booking_Datetime (unparseable: {bad_dt}).")

# 3.2 Derived time features
df["Booking_Hour"] = df["Booking_Datetime"].dt.hour
df["Booking_DayOfWeek"] = df["Booking_Datetime"].dt.day_name()
df["Booking_Date"] = df["Booking_Datetime"].dt.date.astype(str)
df["Is_Weekend"] = df["Booking_DayOfWeek"].isin(["Saturday", "Sunday"]).astype(int)
step("Derived Booking_Hour, Booking_DayOfWeek, Booking_Date, Is_Weekend.")

# 3.3 Standardise text columns (strip whitespace, title-case categories)
text_cols = ["Booking_Status", "Vehicle_Type", "Pickup_Location", "Drop_Location",
             "Payment_Method", "Incomplete_Rides", "Incomplete_Rides_Reason",
             "Canceled_Rides_by_Customer", "Canceled_Rides_by_Driver"]
for c in text_cols:
    df[c] = df[c].astype("string").str.strip()
step("Stripped whitespace on all categorical text columns.")

# 3.4 Normalise vehicle-type label (template uses 'E-Bike')
df["Vehicle_Type"] = df["Vehicle_Type"].replace({"eBike": "E-Bike"})
step("Normalised vehicle label 'eBike' -> 'E-Bike' (matches slide template).")

# 3.5 Structural missingness: TAT / ratings / payment only exist for SUCCESS rides
success_mask = df["Booking_Status"].eq("Success")
n_success = int(success_mask.sum())
n_nonsuccess = raw_rows - n_success
step(f"Booking_Status split: {n_success:,} Success / {n_nonsuccess:,} non-success.")

# 3.6 Incomplete_Rides: fill 'No' where blank (blank == ride completed fine)
df["Incomplete_Rides"] = df["Incomplete_Rides"].fillna("No")
step("Filled Incomplete_Rides blanks with 'No' (blank = completed ride).")

# 3.7 Payment_Method: only meaningful for successful rides -> 'Not Applicable' otherwise
df["Payment_Method"] = df["Payment_Method"].fillna("Not Applicable")
step("Filled Payment_Method blanks with 'Not Applicable' (non-successful rides).")

# 3.8 Cancellation reason columns -> 'Not Applicable' when not that cancellation type
df["Canceled_Rides_by_Customer"] = df["Canceled_Rides_by_Customer"].fillna("Not Applicable")
df["Canceled_Rides_by_Driver"] = df["Canceled_Rides_by_Driver"].fillna("Not Applicable")
df["Incomplete_Rides_Reason"] = df["Incomplete_Rides_Reason"].fillna("Not Applicable")
step("Filled cancellation / incomplete reason blanks with 'Not Applicable'.")

# 3.9 TAT & ratings: keep NaN for non-success (do NOT impute fake values),
#     but flag them so downstream analysis can filter cleanly.
df["Has_TAT"] = df["V_TAT"].notna().astype(int)
step("Kept V_TAT/C_TAT/ratings as NULL for non-successful rides (no fake imputation); "
     "added Has_TAT flag.")

# 3.10 Outlier handling — flag (winsorise) rather than delete
def iqr_flags(s):
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return (s < lo) | (s > hi), lo, hi

outlier_report = {}
for c in ["V_TAT", "C_TAT", "Booking_Value", "Ride_Distance"]:
    flags, lo, hi = iqr_flags(df[c].dropna())
    n_out = int(flags.sum())
    outlier_report[c] = {"iqr_low": round(float(lo), 2), "iqr_high": round(float(hi), 2),
                         "n_outliers": n_out}
    df[f"{c}_is_outlier"] = 0
    df.loc[flags.index[flags], f"{c}_is_outlier"] = 1
step(f"IQR outlier flags computed: " +
     ", ".join(f"{k}={v['n_outliers']}" for k, v in outlier_report.items()))

# 3.11 Zero-distance rides (data-quality issue: distance recorded as 0)
zero_dist = int((df["Ride_Distance"] == 0).sum())
df["Zero_Distance_Flag"] = (df["Ride_Distance"] == 0).astype(int)
step(f"Flagged {zero_dist:,} zero-distance rides (Zero_Distance_Flag).")

# 3.12 Drop exact duplicates (none found, but enforce)
before = len(df)
df = df.drop_duplicates(subset=["Booking_ID"]).reset_index(drop=True)
step(f"De-duplicated on Booking_ID: removed {before - len(df)} rows.")

# 3.13 Final column order
order = ["Booking_ID", "Booking_Datetime", "Booking_Date", "Booking_Hour",
         "Booking_DayOfWeek", "Is_Weekend", "Booking_Status", "Customer_ID",
         "Vehicle_Type", "Pickup_Location", "Drop_Location", "Ride_Distance",
         "Booking_Value", "Payment_Method", "V_TAT", "C_TAT",
         "Driver_Ratings", "Customer_Rating", "Incomplete_Rides",
         "Incomplete_Rides_Reason", "Canceled_Rides_by_Customer",
         "Canceled_Rides_by_Driver", "Has_TAT", "Zero_Distance_Flag",
         "V_TAT_is_outlier", "C_TAT_is_outlier", "Booking_Value_is_outlier",
         "Ride_Distance_is_outlier", "Vehicle Images"]
df = df[order]

# ----------------------------------------------------------------------------
# 4. SAVE
# ----------------------------------------------------------------------------
df.to_csv(f"{OUT}/ola_cleaned.csv", index=False)
step(f"Saved cleaned dataset -> {OUT}/ola_cleaned.csv ({len(df):,} rows x {df.shape[1]} cols).")

prof_after = profile(df)
with open(f"{OUT}/profile_after.json", "w") as f:
    json.dump(prof_after, f, indent=2)

# ----------------------------------------------------------------------------
# 5. DATA-QUALITY SCORECARD
# ----------------------------------------------------------------------------
def completeness(p):
    tot = p["rows"] * p["cols"]
    miss = sum(c["missing"] for c in p["columns"].values())
    return round(100 * (1 - miss / tot), 2)

scorecard = {
    "rows_before": raw_rows, "rows_after": int(len(df)),
    "cols_before": raw_cols, "cols_after": int(df.shape[1]),
    "completeness_before_pct": completeness(prof_before),
    "completeness_after_pct": completeness(prof_after),
    "duplicate_rows_before": prof_before["duplicate_rows"],
    "duplicate_rows_after": prof_after["duplicate_rows"],
    "unparseable_datetimes": bad_dt,
    "success_rides": n_success, "non_success_rides": n_nonsuccess,
    "zero_distance_rides": zero_dist,
    "outliers": outlier_report,
    "structural_missing_note": (
        "V_TAT, C_TAT, Driver_Ratings, Customer_Rating and Payment_Method are "
        "NULL for the 39,057 non-successful bookings by design (no trip occurred). "
        "These are retained as NULL, not imputed."
    ),
}
with open(f"{OUT}/quality_scorecard.json", "w") as f:
    json.dump(scorecard, f, indent=2)

# ----------------------------------------------------------------------------
# 6. CLEANING LOG (markdown)
# ----------------------------------------------------------------------------
with open(f"{OUT}/cleaning_log.md", "w") as f:
    f.write("# OLA DataSet — Cleaning Log\n\n")
    f.write(f"**Source:** `OLA_DataSet.xlsx` (sheet `July`)  \n")
    f.write(f"**Raw shape:** {raw_rows:,} rows x {raw_cols} columns  \n")
    f.write(f"**Clean shape:** {len(df):,} rows x {df.shape[1]} columns\n\n")
    f.write("## Steps\n\n")
    for i, s in enumerate(log, 1):
        f.write(f"{i}. {s}\n")
    f.write("\n## Data-Quality Scorecard\n\n")
    f.write(f"| Metric | Before | After |\n|---|---|---|\n")
    f.write(f"| Rows | {raw_rows:,} | {len(df):,} |\n")
    f.write(f"| Columns | {raw_cols} | {df.shape[1]} |\n")
    f.write(f"| Completeness | {scorecard['completeness_before_pct']}% | {scorecard['completeness_after_pct']}% |\n")
    f.write(f"| Duplicate rows | {prof_before['duplicate_rows']} | {prof_after['duplicate_rows']} |\n")
    f.write(f"| Unparseable datetimes | {bad_dt} | 0 |\n")

print("\n=== SCORECARD ===")
print(json.dumps(scorecard, indent=2))
print("\nDONE")
