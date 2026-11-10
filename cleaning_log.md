# OLA DataSet — Cleaning Log

**Source:** `OLA_DataSet.xlsx` (sheet `July`)  
**Raw shape:** 103,024 rows x 20 columns  
**Clean shape:** 103,024 rows x 29 columns

## Steps

1. Loaded sheet 'July': 103,024 rows x 20 columns.
2. Parsed Date+Time -> Booking_Datetime (unparseable: 0).
3. Derived Booking_Hour, Booking_DayOfWeek, Booking_Date, Is_Weekend.
4. Stripped whitespace on all categorical text columns.
5. Normalised vehicle label 'eBike' -> 'E-Bike' (matches slide template).
6. Booking_Status split: 63,967 Success / 39,057 non-success.
7. Filled Incomplete_Rides blanks with 'No' (blank = completed ride).
8. Filled Payment_Method blanks with 'Not Applicable' (non-successful rides).
9. Filled cancellation / incomplete reason blanks with 'Not Applicable'.
10. Kept V_TAT/C_TAT/ratings as NULL for non-successful rides (no fake imputation); added Has_TAT flag.
11. IQR outlier flags computed: V_TAT=0, C_TAT=0, Booking_Value=8468, Ride_Distance=0
12. Flagged 39,057 zero-distance rides (Zero_Distance_Flag).
13. De-duplicated on Booking_ID: removed 0 rows.
14. Saved cleaned dataset -> data/ola_cleaned.csv (103,024 rows x 29 cols).

## Data-Quality Scorecard

| Metric | Before | After |
|---|---|---|
| Rows | 103,024 | 103,024 |
| Columns | 20 | 29 |
| Completeness | 75.22% | 94.77% |
| Duplicate rows | 0 | 0 |
| Unparseable datetimes | 0 | 0 |
