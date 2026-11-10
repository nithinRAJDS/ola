# OLA Rides — Power BI DAX Measures (copy-paste ready)

> Create these as **New Measure** on the `bookings` table (or a dedicated
> `_Measures` table). Format strings are noted in `[brackets]`.

---

## 1. Core volume & revenue

```dax
Total Bookings = COUNTROWS ( bookings )
```
`[Whole number, thousands separator]`

```dax
Successful Bookings =
CALCULATE ( COUNTROWS ( bookings ), bookings[Booking_Status] = "Success" )
```

```dax
Canceled Bookings =
CALCULATE ( COUNTROWS ( bookings ), bookings[Booking_Status] IN { "Canceled by Customer", "Canceled by Driver" } )
```

```dax
Driver Not Found Bookings =
CALCULATE ( COUNTROWS ( bookings ), bookings[Booking_Status] = "Driver Not Found" )
```

```dax
Total Revenue =
CALCULATE ( SUM ( bookings[Booking_Value] ), bookings[Booking_Status] = "Success" )
```
`[Currency ₹, 0 decimals]`

```dax
Avg Booking Value =
CALCULATE ( AVERAGE ( bookings[Booking_Value] ), bookings[Booking_Status] = "Success" )
```
`[Currency ₹, 0 decimals]`

```dax
Total Distance (km) =
CALCULATE ( SUM ( bookings[Ride_Distance] ), bookings[Booking_Status] = "Success" )
```

```dax
Avg Ride Distance (km) =
CALCULATE ( AVERAGE ( bookings[Ride_Distance] ), bookings[Booking_Status] = "Success" )
```
`[Decimal, 2 places]`

---

## 2. Rates & ratios

```dax
Success Rate % =
DIVIDE ( [Successful Bookings], [Total Bookings] )
```
`[Percentage, 1 decimal]`

```dax
Cancellation Rate % =
DIVIDE ( [Canceled Bookings], [Total Bookings] )
```
`[Percentage, 1 decimal]`

```dax
Driver Not Found Rate % =
DIVIDE ( [Driver Not Found Bookings], [Total Bookings] )
```
`[Percentage, 1 decimal]`

```dax
Revenue per Booking =
DIVIDE ( [Total Revenue], [Successful Bookings] )
```
`[Currency ₹, 0 decimals]`

```dax
Revenue per km =
DIVIDE ( [Total Revenue], [Total Distance (km)] )
```
`[Currency ₹, 2 decimals]`

---

## 3. Ratings & turnaround

```dax
Avg Driver Rating =
CALCULATE ( AVERAGE ( bookings[Driver_Ratings] ), bookings[Booking_Status] = "Success" )
```
`[Decimal, 2 places]`

```dax
Avg Customer Rating =
CALCULATE ( AVERAGE ( bookings[Customer_Rating] ), bookings[Booking_Status] = "Success" )
```
`[Decimal, 2 places]`

```dax
Avg V_TAT (min) =
CALCULATE ( AVERAGE ( bookings[V_TAT] ), bookings[Booking_Status] = "Success" )
```
`[Decimal, 1 place]`

```dax
Avg C_TAT (min) =
CALCULATE ( AVERAGE ( bookings[C_TAT] ), bookings[Booking_Status] = "Success" )
```
`[Decimal, 1 place]`

```dax
Incomplete Rides =
CALCULATE ( COUNTROWS ( bookings ), bookings[Incomplete_Rides] = "Yes" )
```

---

## 4. Time intelligence

```dax
Bookings MTD =
TOTALMTD ( [Total Bookings], 'Date'[Date] )
```

```dax
Revenue MTD =
TOTALMTD ( [Total Revenue], 'Date'[Date] )
```

```dax
Revenue PM (Prev Month) =
CALCULATE ( [Total Revenue], DATEADD ( 'Date'[Date], -1, MONTH ) )
```

```dax
Revenue MoM % =
VAR Cur = [Total Revenue]
VAR Prev = [Revenue PM (Prev Month)]
RETURN DIVIDE ( Cur - Prev, Prev )
```
`[Percentage, 1 decimal]`

```dax
Bookings 7-day Moving Avg =
AVERAGEX (
    DATESINPERIOD ( 'Date'[Date], MAX ( 'Date'[Date] ), -7, DAY ),
    [Total Bookings]
)
```

```dax
Revenue 7-day Moving Avg =
AVERAGEX (
    DATESINPERIOD ( 'Date'[Date], MAX ( 'Date'[Date] ), -7, DAY ),
    [Total Revenue]
)
```

```dax
Weekend Bookings =
CALCULATE ( [Total Bookings], bookings[Is_Weekend] = 1 )
```

```dax
Weekday Bookings =
CALCULATE ( [Total Bookings], bookings[Is_Weekend] = 0 )
```

---

## 5. Ranking & share

```dax
Revenue Rank by City =
RANKX ( ALL ( bookings[Pickup_Location] ), [Total Revenue], , DESC, DENSE )
```

```dax
Revenue Rank by Vehicle =
RANKX ( ALL ( bookings[Vehicle_Type] ), [Total Revenue], , DESC, DENSE )
```

```dax
Revenue Share % =
DIVIDE ( [Total Revenue], CALCULATE ( [Total Revenue], ALL ( bookings ) ) )
```
`[Percentage, 1 decimal]`

```dax
Top City Revenue =
MAXX ( TOPN ( 1, ALL ( bookings[Pickup_Location] ), [Total Revenue], DESC ), [Total Revenue] )
```

```dax
Top City Name =
VAR t = TOPN ( 1, ALL ( bookings[Pickup_Location] ), [Total Revenue], DESC )
RETURN CONCATENATEX ( t, bookings[Pickup_Location], ", " )
```

```dax
Top Vehicle Type =
VAR t = TOPN ( 1, ALL ( bookings[Vehicle_Type] ), [Total Revenue], DESC )
RETURN CONCATENATEX ( t, bookings[Vehicle_Type], ", " )
```

---

## 6. Dynamic titles & KPI helpers

```dax
KPI Revenue Title =
"Total Revenue: " & FORMAT ( [Total Revenue], "₹#,##0" )
```

```dax
KPI Success Title =
"Success Rate: " & FORMAT ( [Success Rate %], "0.0%" )
```

```dax
Revenue vs Target =
VAR Target = 1.0e9   -- ₹1.0 bn illustrative target
RETURN DIVIDE ( [Total Revenue], Target )
```
`[Percentage, 1 decimal]`

```dax
Revenue Status =
VAR r = [Revenue vs Target]
RETURN SWITCH ( TRUE (), r >= 1, "On Track", r >= 0.8, "Watch", "Below Target" )
```

---

## 7. Conditional-formatting colour measure

```dax
Success Rate Colour =
VAR v = [Success Rate %]
RETURN SWITCH ( TRUE (), v >= 0.65, "#50B432", v >= 0.60, "#EDEF00", "#ED561B" )
```

---

## 8. Calculated columns (on `bookings`)

```dax
Revenue Band =
SWITCH (
    TRUE (),
    bookings[Booking_Value] < 300, "Low (<₹300)",
    bookings[Booking_Value] < 600, "Mid (₹300–600)",
    bookings[Booking_Value] < 1000, "High (₹600–1000)",
    "Premium (₹1000+)"
)
```

```dax
Time of Day =
SWITCH (
    TRUE (),
    bookings[Booking_Hour] < 6, "Night (0–6)",
    bookings[Booking_Hour] < 12, "Morning (6–12)",
    bookings[Booking_Hour] < 17, "Afternoon (12–17)",
    bookings[Booking_Hour] < 21, "Evening (17–21)",
    "Late (21–24)"
)
```

```dax
Is Successful = IF ( bookings[Booking_Status] = "Success", 1, 0 )
```

---

## 9. Date table (calculated table)

```dax
Date =
VAR MinD = MIN ( bookings[Booking_Date] )
VAR MaxD = MAX ( bookings[Booking_Date] )
RETURN
ADDCOLUMNS (
    CALENDAR ( MinD, MaxD ),
    "Year", YEAR ( [Date] ),
    "Month", FORMAT ( [Date], "mmm" ),
    "MonthNo", MONTH ( [Date] ),
    "Day", DAY ( [Date] ),
    "DayName", FORMAT ( [Date], "ddd" ),
    "WeekdayNo", WEEKDAY ( [Date], 2 ),
    "IsWeekend", IF ( WEEKDAY ( [Date], 2 ) >= 6, 1, 0 )
)
```
Then **Mark as date table** on `Date[Date]` and relate `Date[Date]` → `bookings[Booking_Date]` (many-to-one).
