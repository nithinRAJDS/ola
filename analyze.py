"""Compute all KPIs / analytics for the OLA dataset -> data/analytics.json"""
import json
import numpy as np
import pandas as pd

df = pd.read_csv("data/ola_cleaned.csv", parse_dates=["Booking_Datetime"])
A = {}

# ---- Overall KPIs -----------------------------------------------------------
total = len(df)
succ = df[df.Booking_Status == "Success"]
A["total_bookings"] = int(total)
A["success_bookings"] = int(len(succ))
A["success_rate"] = round(100 * len(succ) / total, 2)
A["canceled_by_customer"] = int((df.Booking_Status == "Canceled by Customer").sum())
A["canceled_by_driver"] = int((df.Booking_Status == "Canceled by Driver").sum())
A["driver_not_found"] = int((df.Booking_Status == "Driver Not Found").sum())
A["total_revenue"] = round(float(succ.Booking_Value.sum()), 2)
A["avg_booking_value"] = round(float(succ.Booking_Value.mean()), 2)
A["avg_ride_distance"] = round(float(succ.Ride_Distance.mean()), 2)
A["total_distance"] = int(succ.Ride_Distance.sum())
A["avg_driver_rating"] = round(float(succ.Driver_Ratings.mean()), 2)
A["avg_customer_rating"] = round(float(succ.Customer_Rating.mean()), 2)
A["avg_v_tat"] = round(float(succ.V_TAT.mean()), 2)
A["avg_c_tat"] = round(float(succ.C_TAT.mean()), 2)
A["unique_customers"] = int(df.Customer_ID.nunique())
A["repeat_customers"] = int((df.Customer_ID.value_counts() > 1).sum())
A["repeat_rate"] = round(100 * A["repeat_customers"] / A["unique_customers"], 2)
A["incomplete_rides"] = int((df.Incomplete_Rides == "Yes").sum())

# ---- By vehicle type --------------------------------------------------------
vt = df.groupby("Vehicle_Type").agg(
    bookings=("Booking_ID", "count"),
    revenue=("Booking_Value", "sum"),
).reset_index()
vt_succ = succ.groupby("Vehicle_Type").agg(
    success=("Booking_ID", "count"),
    avg_value=("Booking_Value", "mean"),
    avg_dist=("Ride_Distance", "mean"),
    avg_driver_rating=("Driver_Ratings", "mean"),
    avg_cust_rating=("Customer_Rating", "mean"),
).reset_index()
vt = vt.merge(vt_succ, on="Vehicle_Type", how="left")
vt["success_rate"] = (100 * vt.success / vt.bookings).round(2)
vt["revenue"] = vt.revenue.round(2)
vt["avg_value"] = vt.avg_value.round(2)
vt["avg_dist"] = vt.avg_dist.round(2)
vt["avg_driver_rating"] = vt.avg_driver_rating.round(2)
vt["avg_cust_rating"] = vt.avg_cust_rating.round(2)
vt = vt.sort_values("revenue", ascending=False)
A["by_vehicle"] = vt.to_dict("records")

# ---- By payment method ------------------------------------------------------
pm = succ.groupby("Payment_Method").agg(
    rides=("Booking_ID", "count"),
    revenue=("Booking_Value", "sum"),
    avg_value=("Booking_Value", "mean"),
).reset_index()
pm["revenue"] = pm.revenue.round(2)
pm["avg_value"] = pm.avg_value.round(2)
pm["share_pct"] = (100 * pm.rides / pm.rides.sum()).round(2)
pm = pm.sort_values("revenue", ascending=False)
A["by_payment"] = pm.to_dict("records")

# ---- By city (pickup) -------------------------------------------------------
city = df.groupby("Pickup_Location").agg(
    bookings=("Booking_ID", "count"),
).reset_index()
city_s = succ.groupby("Pickup_Location").agg(
    success=("Booking_ID", "count"),
    revenue=("Booking_Value", "sum"),
    avg_value=("Booking_Value", "mean"),
    avg_dist=("Ride_Distance", "mean"),
).reset_index()
city = city.merge(city_s, on="Pickup_Location", how="left")
city["success_rate"] = (100 * city.success.fillna(0) / city.bookings).round(2)
city["revenue"] = city.revenue.round(2)
city["avg_value"] = city.avg_value.round(2)
city["avg_dist"] = city.avg_dist.round(2)
city = city.sort_values("revenue", ascending=False)
A["by_city_top10"] = city.head(10).to_dict("records")
A["by_city_bottom5"] = city.tail(5).to_dict("records")
A["n_cities"] = int(city.shape[0])

# ---- Cancellation reasons ---------------------------------------------------
A["cancel_customer_reasons"] = (
    df[df.Booking_Status == "Canceled by Customer"]
    .Canceled_Rides_by_Customer.value_counts().to_dict())
A["cancel_driver_reasons"] = (
    df[df.Booking_Status == "Canceled by Driver"]
    .Canceled_Rides_by_Driver.value_counts().to_dict())
A["incomplete_reasons"] = (
    df[df.Incomplete_Rides == "Yes"]
    .Incomplete_Rides_Reason.value_counts().to_dict())

# ---- Trends over time -------------------------------------------------------
daily = df.groupby("Booking_Date").agg(bookings=("Booking_ID", "count")).reset_index()
daily_s = succ.groupby("Booking_Date").agg(revenue=("Booking_Value", "sum")).reset_index()
daily = daily.merge(daily_s, on="Booking_Date", how="left").fillna(0)
daily["revenue"] = daily.revenue.round(2)
A["daily"] = daily.to_dict("records")

hourly = df.groupby("Booking_Hour").agg(bookings=("Booking_ID", "count")).reset_index()
A["hourly"] = hourly.to_dict("records")

dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
dow = df.groupby("Booking_DayOfWeek").agg(bookings=("Booking_ID", "count")).reindex(dow_order).reset_index()
A["by_dow"] = dow.to_dict("records")

# ---- Status distribution ----------------------------------------------------
A["status_dist"] = df.Booking_Status.value_counts().to_dict()

# ---- Top routes -------------------------------------------------------------
routes = df.groupby(["Pickup_Location", "Drop_Location"]).size().reset_index(name="rides")
routes = routes.sort_values("rides", ascending=False).head(10)
A["top_routes"] = routes.to_dict("records")

with open("data/analytics.json", "w") as f:
    json.dump(A, f, indent=2, default=str)

print(json.dumps({k: v for k, v in A.items() if not isinstance(v, list)}, indent=2))
print("\nby_vehicle:")
print(vt.to_string(index=False))
print("\nby_payment:")
print(pm.to_string(index=False))
print("\nby_city_top10:")
print(city.head(10).to_string(index=False))
print("\nDONE")
