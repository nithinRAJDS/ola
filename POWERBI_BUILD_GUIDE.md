# OLA Rides Analytics — Power BI Build Guide

**Deliverable:** a complete, reproducible Power BI report for the cleaned OLA
July-2024 booking dataset (`ola_cleaned.csv`, 103,024 rows × 29 columns).

**Files in this folder**
| File | Purpose |
|---|---|
| `POWERBI_BUILD_GUIDE.md` | This step-by-step guide |
| `ola_theme.json` | Power BI theme matching the Ola slide template palette |
| `dax_measures.md` | All DAX measures, copy-paste ready |
| `ola_pbit_template.md` | `.pbit` template description (data-source + model spec) |

> **Why not a `.pbix`?** A `.pbix` is a proprietary binary that can only be
> authored inside Power BI Desktop. Everything needed to rebuild the report
> byte-for-byte is specified below; the theme JSON and DAX file drop straight in.

---

## 0. Prerequisites

- Power BI Desktop (free, Windows) — latest version.
- The cleaned file `ola_cleaned.csv` (in the `data/` folder of this package).
- Optional: a Power BI Pro licence to publish to a workspace.

---

## 1. Data import

1. **Home → Get data → Text/CSV** → select `ola_cleaned.csv` → **Transform Data**
   (do *not* click Load yet — we clean in Power Query first).
2. Confirm the delimiter is comma and encoding UTF-8.
3. Rename the query to **`bookings`** (right-click the query in the left pane → Rename).

### 1.1 Column types to set in Power Query
| Column | Type |
|---|---|
| Booking_ID, Customer_ID, Booking_Status, Vehicle_Type, Pickup_Location, Drop_Location, Payment_Method, Incomplete_Rides, Incomplete_Rides_Reason, Canceled_Rides_by_Customer, Canceled_Rides_by_Driver | Text |
| Booking_Datetime | Date/Time |
| Booking_Date | Date |
| Booking_Hour, Is_Weekend, Has_TAT, Zero_Distance_Flag, *_is_outlier | Whole Number |
| Ride_Distance, Booking_Value | Whole Number |
| V_TAT, C_TAT, Driver_Ratings, Customer_Rating | Decimal Number |

---

## 2. Power Query cleaning steps (M)

The CSV is already cleaned, but these steps make the model robust and are the
exact transformations to record. In **Transform Data → Advanced Editor**, the
query should read:

```m
let
    Source = Csv.Document(File.Contents("ola_cleaned.csv"),
                [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    PromoteHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(PromoteHeaders,{
        {"Booking_ID", type text}, {"Booking_Datetime", type datetime},
        {"Booking_Date", type date}, {"Booking_Hour", Int64.Type},
        {"Booking_DayOfWeek", type text}, {"Is_Weekend", Int64.Type},
        {"Booking_Status", type text}, {"Customer_ID", type text},
        {"Vehicle_Type", type text}, {"Pickup_Location", type text},
        {"Drop_Location", type text}, {"Ride_Distance", Int64.Type},
        {"Booking_Value", Int64.Type}, {"Payment_Method", type text},
        {"V_TAT", type number}, {"C_TAT", type number},
        {"Driver_Ratings", type number}, {"Customer_Rating", type number},
        {"Incomplete_Rides", type text}, {"Incomplete_Rides_Reason", type text},
        {"Canceled_Rides_by_Customer", type text}, {"Canceled_Rides_by_Driver", type text},
        {"Has_TAT", Int64.Type}, {"Zero_Distance_Flag", Int64.Type},
        {"V_TAT_is_outlier", Int64.Type}, {"C_TAT_is_outlier", Int64.Type},
        {"Booking_Value_is_outlier", Int64.Type}, {"Ride_Distance_is_outlier", Int64.Type}
    }),
    TrimText = Table.TransformColumns(Typed, {
        {"Booking_Status", Text.Trim}, {"Vehicle_Type", Text.Trim},
        {"Pickup_Location", Text.Trim}, {"Drop_Location", Text.Trim},
        {"Payment_Method", Text.Trim}
    }),
    // Guard: drop any row without a booking id
    RemovedBlank = Table.SelectRows(TrimText, each [Booking_ID] <> null and [Booking_ID] <> ""),
    // Add a numeric success flag for easy aggregation
    AddSuccess = Table.AddColumn(RemovedBlank, "Is_Success",
                    each if [Booking_Status] = "Success" then 1 else 0, Int64.Type)
in
    AddSuccess
```

**Cleaning steps applied upstream (documented in `data/cleaning_log.md`):**
1. Parsed `Date` + `Time` → `Booking_Datetime`; derived hour / day-of-week / weekend flag.
2. Trimmed whitespace on all categorical text.
3. Normalised `eBike` → `E-Bike`.
4. Filled `Incomplete_Rides` blanks with `No`; `Payment_Method` and cancellation
   reasons with `Not Applicable`.
5. Kept TAT / ratings as NULL for non-successful rides (no fake imputation).
6. IQR outlier flags on `Booking_Value` (8,468 flagged) and zero-distance flag (39,057).
7. De-duplicated on `Booking_ID` (0 removed).

---

## 3. Data model

### 3.1 Tables
- **`bookings`** — the fact table (grain: one row per booking).
- **`Date`** — a calculated date dimension (DAX in `dax_measures.md` §9).

### 3.2 Relationships
| From | To | Cardinality | Cross-filter |
|---|---|---|---|
| `Date`[Date] | `bookings`[Booking_Date] | 1 → many | Single |

Mark `Date` as the official date table (**Table tools → Mark as date table → Date[Date]**).

### 3.3 Optional star-schema split (recommended for scale)
Create three dimension tables with **Reference** queries and keep only the key
in the fact table:

```m
// Dim_Vehicle
let S = bookings, K = Table.Distinct(Table.SelectColumns(S,{"Vehicle_Type"})) in K
// Dim_Location  (union of pickup + drop)
let P = Table.Distinct(Table.SelectColumns(bookings,{"Pickup_Location"})),
    D = Table.Distinct(Table.SelectColumns(bookings,{"Drop_Location"})),
    U = Table.Distinct(Table.Combine({Table.RenameColumns(P,{{"Pickup_Location","Location"}}),
                                      Table.RenameColumns(D,{{"Drop_Location","Location"}})})),
    Idx = Table.AddIndexColumn(U, "LocationKey", 1, 1, Int64.Type)
in Idx
```
Then relate `Dim_Vehicle[Vehicle_Type]` → `bookings[Vehicle_Type]` and
`Dim_Location[Location]` → `bookings[Pickup_Location]` / `bookings[Drop_Location]`
(one active, one inactive relationship).

---

## 4. Theme

**View → Themes → Browse for themes** → select **`ola_theme.json`**.

Palette (from the Ola slide template):
| Role | Hex |
|---|---|
| Primary / dark navy | `#082836` |
| Accent green | `#92D050` |
| Accent blue | `#058DC7` |
| Orange | `#ED561B` |
| Light green | `#50B432` |
| Cyan | `#24CBE5` |
| Yellow | `#EDEF00` |
| Page background | `#F3F3F3` |
| Card background | `#FFFFFF` |
| Font | **Poppins** (fallback Arial) |

---

## 5. Report pages & visuals

Canvas: **16:9 (1280 × 720)**. Page background `#F3F3F3`. Every page has a
top banner rectangle (`#082836`, height 60 px) with the page title in white
Poppins 18 pt, and the Ola logo top-right.

### Page 1 — Executive Overview
| # | Visual | Fields / measures | Notes |
|---|---|---|---|
| 1 | **Card** ×5 | Total Bookings · Total Revenue · Success Rate % · Avg Booking Value · Avg Driver Rating | Row of KPI cards, green callout numbers |
| 2 | **Line chart** | Axis `Date[Date]`, Values `Total Bookings`, `Total Revenue` (secondary) | Daily trend, 7-day moving avg line |
| 3 | **Donut** | Legend `Booking_Status`, Values `Total Bookings` | Status mix |
| 4 | **Bar (clustered)** | Axis `Vehicle_Type`, Values `Total Revenue` | Revenue by vehicle |
| 5 | **Slicer** | `Date[Date]` (between), `Vehicle_Type`, `Pickup_Location` | Top-right filter panel |

### Page 2 — Vehicle Type Analysis
| # | Visual | Fields / measures |
|---|---|---|
| 1 | **Matrix** | Rows `Vehicle_Type`; Values: Total Bookings, Successful Bookings, Total Revenue, Avg Booking Value, Avg Ride Distance, Success Rate %, Avg Driver Rating |
| 2 | **Bar** | Axis `Vehicle_Type`, Values `Total Revenue` (data labels on) |
| 3 | **Scatter** | X `Avg Ride Distance (km)`, Y `Avg Booking Value`, Size `Total Bookings`, Legend `Vehicle_Type` |
| 4 | **Bar** | Axis `Vehicle_Type`, Values `Success Rate %` (conditional colour by `Success Rate Colour`) |

### Page 3 — Revenue & Payment
| # | Visual | Fields / measures |
|---|---|---|
| 1 | **Card** ×3 | Total Revenue · Revenue per Booking · Revenue per km |
| 2 | **Pie** | Legend `Payment_Method`, Values `Total Revenue` |
| 3 | **Bar** | Axis `Payment_Method`, Values `Successful Bookings` |
| 4 | **Column** | Axis `Revenue Band` (calc column), Values `Total Bookings` |
| 5 | **Table** | `Payment_Method`, rides, revenue, avg value, share % |

### Page 4 — Cancellations & Service Quality
| # | Visual | Fields / measures |
|---|---|---|
| 1 | **Card** ×4 | Canceled Bookings · Cancellation Rate % · Driver Not Found Bookings · Incomplete Rides |
| 2 | **Bar** | Axis `Canceled_Rides_by_Customer`, Values `Total Bookings` (filter status = Canceled by Customer) |
| 3 | **Bar** | Axis `Canceled_Rides_by_Driver`, Values `Total Bookings` (filter status = Canceled by Driver) |
| 4 | **Bar** | Axis `Incomplete_Rides_Reason`, Values `Total Bookings` |
| 5 | **Gauge** | Value `Success Rate %`, target 0.70 |

### Page 5 — Geography (City)
| # | Visual | Fields / measures |
|---|---|---|
| 1 | **Map (filled)** | Location `Pickup_Location`, Colour saturation `Total Revenue` | Bengaluru areas |
| 2 | **Bar (Top N = 10)** | Axis `Pickup_Location`, Values `Total Revenue` |
| 3 | **Table** | `Pickup_Location`, bookings, revenue, avg value, avg distance, success rate |
| 4 | **Slicer** | `Pickup_Location` (dropdown, multi-select) |

### Page 6 — Time Patterns
| # | Visual | Fields / measures |
|---|---|---|
| 1 | **Column** | Axis `Booking_Hour`, Values `Total Bookings` | Peak-hour profile |
| 2 | **Column** | Axis `Booking_DayOfWeek` (sort by WeekdayNo), Values `Total Bookings` |
| 3 | **Matrix** | Rows `Time of Day`, Columns `Is_Weekend`, Values `Total Bookings`, `Total Revenue` |
| 4 | **Line** | Axis `Date[Date]`, Values `Revenue 7-day Moving Avg` |

### Page 7 — Data Quality
| # | Visual | Fields / measures |
|---|---|---|
| 1 | **Card** ×4 | Rows · Completeness % · Duplicate rows · Unparseable dates |
| 2 | **Bar** | Axis column name, Values missing % (from a small `dq_missing` table) |
| 3 | **Table** | Outlier flags: column, flagged count |
| 4 | **Text box** | Structural-missingness note |

---

## 6. Slicers & interactions

- **Global slicers** (sync across pages via **View → Sync slicers**):
  `Date[Date]`, `Vehicle_Type`, `Pickup_Location`, `Payment_Method`, `Booking_Status`.
- **Edit interactions**: KPI cards ignore the status slicer (they are already
  status-scoped); charts respond to all slicers.
- Add a **bookmark** "Reset filters" and a **Clear all slicers** button.

---

## 7. Formatting checklist

- [ ] Theme applied (`ola_theme.json`).
- [ ] All card callout values: Poppins, `#082836`, 32 pt.
- [ ] Chart titles: Poppins 13 pt, `#082836`, left-aligned.
- [ ] Data labels on all bar/column charts; thousands separator on currency.
- [ ] Currency format `₹#,##0`; percentages 1 decimal.
- [ ] Gridlines light `#EDEDED`; axis labels `#3A3A3A`.
- [ ] Consistent 8 px card corner radius, 1 px `#E3E3E3` border.
- [ ] Alt-text on every visual (accessibility).
- [ ] Page size 16:9; background `#F3F3F3`.

---

## 8. Publish & refresh

1. **File → Publish →** choose a workspace.
2. In the Service, **Settings → Scheduled refresh** (daily) if the CSV is on a
   gateway-accessible path; otherwise use a **OneDrive/SharePoint** source for
   automatic refresh.
3. Pin the KPI cards to a **Dashboard** for the executive view.

---

## 9. Reference KPI values (July 2024) — for validation

| KPI | Value |
|---|---|
| Total bookings | 103,024 |
| Successful bookings | 63,967 |
| Success rate | 62.09 % |
| Canceled by driver | 18,434 |
| Canceled by customer | 10,499 |
| Driver not found | 10,124 |
| Total revenue | ₹35,080,467 |
| Avg booking value | ₹548.42 |
| Avg ride distance | 22.85 km |
| Total distance | 1,461,903 km |
| Avg driver rating | 4.00 |
| Avg customer rating | 4.00 |
| Avg V_TAT / C_TAT | 170.9 / 84.9 min |
| Unique customers | 94,544 |
| Repeat customers | 7,954 (8.41 %) |
| Incomplete rides | 3,926 |
| Cities (pickup areas) | 50 |
| Peak booking hour | 12:00 (4,408 bookings) |
| Top route | Majestic → Hennur (67 rides) |

> If your visuals don't match these numbers, check that revenue measures filter
> `Booking_Status = "Success"`.
