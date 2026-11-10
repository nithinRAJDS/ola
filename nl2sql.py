"""
nl2sql.py — Natural-language -> SQL translation layer for the OLA dataset.

Two engines:
  1. LLM engine  — used automatically when OPENAI_API_KEY (or ANTHROPIC_API_KEY)
                   is present in the environment. Sends the schema + question to
                   the model and asks for a single read-only SQLite SELECT.
  2. Rule engine — a robust keyword/pattern mapper that covers the common
                   question types (totals, averages, counts, group-bys by
                   date/city/vehicle/payment, top-N, trends). No API key needed.

`translate(question)` returns (sql, engine_name, explanation).
"""
from __future__ import annotations
import os
import re

SCHEMA = """
Table: bookings  (one row per Ola booking, July 2024, Bengaluru)
  Booking_ID            TEXT   -- unique booking id (CNR...)
  Booking_Datetime      TEXT   -- ISO timestamp of booking
  Booking_Date          TEXT   -- YYYY-MM-DD
  Booking_Hour          INT    -- 0-23
  Booking_DayOfWeek     TEXT   -- Monday..Sunday
  Is_Weekend            INT    -- 1 if Sat/Sun else 0
  Booking_Status        TEXT   -- Success | Canceled by Customer | Canceled by Driver | Driver Not Found
  Customer_ID           TEXT
  Vehicle_Type          TEXT   -- Prime Sedan | Prime SUV | Prime Plus | Mini | Auto | Bike | E-Bike
  Pickup_Location       TEXT   -- 50 Bengaluru areas
  Drop_Location         TEXT
  Ride_Distance         INT    -- km (0 for non-successful rides)
  Booking_Value         INT    -- fare in INR
  Payment_Method        TEXT   -- Cash | UPI | Credit Card | Debit Card | Not Applicable
  V_TAT                 REAL   -- vehicle turnaround time (min), NULL for non-success
  C_TAT                 REAL   -- customer turnaround time (min), NULL for non-success
  Driver_Ratings        REAL   -- 3.0-5.0, NULL for non-success
  Customer_Rating       REAL   -- 3.0-5.0, NULL for non-success
  Incomplete_Rides      TEXT   -- Yes | No
  Incomplete_Rides_Reason TEXT
  Canceled_Rides_by_Customer TEXT
  Canceled_Rides_by_Driver   TEXT
  Has_TAT               INT
  Zero_Distance_Flag    INT
Views: successful_rides (Booking_Status='Success'), cancellations (Booking_Status LIKE 'Canceled%')
"""

VEHICLES = ["Prime Sedan", "Prime SUV", "Prime Plus", "Mini", "Auto", "Bike", "E-Bike"]
PAYMENTS = ["Cash", "UPI", "Credit Card", "Debit Card"]
CITIES = ['BTM Layout', 'Banashankari', 'Bannerghatta Road', 'Basavanagudi', 'Bellandur',
          'Chamarajpet', 'Chickpet', 'Cox Town', 'Devanahalli', 'Electronic City',
          'Frazer Town', 'HSR Layout', 'Hebbal', 'Hennur', 'Hosur Road', 'Hulimavu',
          'Indiranagar', 'JP Nagar', 'Jayanagar', 'KR Puram', 'Kadugodi', 'Kammanahalli',
          'Kengeri', 'Koramangala', 'Langford Town', 'MG Road', 'Magadi Road', 'Majestic',
          'Malleshwaram', 'Marathahalli', 'Mysore Road', 'Nagarbhavi', 'Padmanabhanagar',
          'Peenya', 'RT Nagar', 'Rajajinagar', 'Rajarajeshwari Nagar', 'Ramamurthy Nagar',
          'Richmond Town', 'Sahakar Nagar', 'Sarjapur Road', 'Shantinagar', 'Shivajinagar',
          'Tumkur Road', 'Ulsoor', 'Varthur', 'Vijayanagar', 'Whitefield', 'Yelahanka',
          'Yeshwanthpur']

VEH_ALIAS = {"ebike": "E-Bike", "e-bike": "E-Bike", "e bike": "E-Bike",
             "sedan": "Prime Sedan", "suv": "Prime SUV", "auto": "Auto",
             "bike": "Bike", "mini": "Mini", "prime plus": "Prime Plus"}
PAY_ALIAS = {"credit": "Credit Card", "debit": "Debit Card", "upi": "UPI", "cash": "Cash"}


# ---------------------------------------------------------------------------
# LLM engine
# ---------------------------------------------------------------------------
def _llm_translate(question: str):
    key = os.getenv("OPENAI_API_KEY")
    akey = os.getenv("ANTHROPIC_API_KEY")
    if not (key or akey):
        return None
    prompt = (
        "You are a SQLite expert. Given the schema below, write ONE read-only "
        "SQLite SELECT query that answers the user's question. Return ONLY the SQL, "
        "no markdown, no explanation. Use the table `bookings` (or the views). "
        "For revenue use SUM(Booking_Value) over successful rides. "
        "Always add a sensible LIMIT (<=100) unless it is an aggregate.\n\n"
        f"SCHEMA:\n{SCHEMA}\n\nQUESTION: {question}\nSQL:"
    )
    try:
        if key:
            from openai import OpenAI
            client = OpenAI()
            r = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}], temperature=0)
            sql = r.choices[0].message.content.strip()
        else:
            import anthropic
            client = anthropic.Anthropic()
            r = client.messages.create(
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
                max_tokens=600, messages=[{"role": "user", "content": prompt}])
            sql = r.content[0].text.strip()
        sql = re.sub(r"^```(sql)?|```$", "", sql, flags=re.M).strip().rstrip(";")
        if not sql.lower().startswith(("select", "with")):
            return None
        return sql
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------
def _find_vehicle(q):
    for v in VEHICLES:
        if v.lower() in q:
            return v
    for k, v in VEH_ALIAS.items():
        if k in q:
            return v
    return None


def _find_payment(q):
    for p in PAYMENTS:
        if p.lower() in q:
            return p
    for k, v in PAY_ALIAS.items():
        if k in q:
            return v
    return None


def _find_city(q):
    for c in CITIES:
        if c.lower() in q:
            return c
    return None


def _rule_translate(question: str):
    q = question.lower().strip()
    where = []

    veh = _find_vehicle(q)
    pay = _find_payment(q)
    city = _find_city(q)
    if veh:
        where.append(f"Vehicle_Type = '{veh}'")
    if pay:
        where.append(f"Payment_Method = '{pay}'")
    if city:
        where.append(f"Pickup_Location = '{city}'")

    # status filter (robust to "by the driver" etc.)
    if "cancel" in q and "driver" in q:
        where.append("Booking_Status = 'Canceled by Driver'")
    elif "cancel" in q and "customer" in q:
        where.append("Booking_Status = 'Canceled by Customer'")
    elif "driver not found" in q:
        where.append("Booking_Status = 'Driver Not Found'")
    elif "success" in q or "completed" in q:
        where.append("Booking_Status = 'Success'")

    W = (" WHERE " + " AND ".join(where)) if where else ""
    Ws = (" WHERE Booking_Status='Success'" +
          (" AND " + " AND ".join(where) if where else "")) if True else ""

    def has(*words):
        return any(w in q for w in words)

    # ---- 1. TRENDS over time ---------------------------------------------
    if has("trend", "over time", "by day", "daily", "per day", "by date", "time series", "by month"):
        return (f"SELECT Booking_Date, COUNT(*) AS bookings, "
                f"ROUND(SUM(CASE WHEN Booking_Status='Success' THEN Booking_Value ELSE 0 END),2) AS revenue "
                f"FROM bookings{W} GROUP BY Booking_Date ORDER BY Booking_Date", "trend by date")
    if has("by hour", "hourly", "per hour", "peak hour", "busiest hour", "what time"):
        return (f"SELECT Booking_Hour, COUNT(*) AS bookings FROM bookings{W} "
                f"GROUP BY Booking_Hour ORDER BY Booking_Hour", "trend by hour")
    if has("day of week", "weekday", "by day name", "which day", "busiest day"):
        return (f"SELECT Booking_DayOfWeek, COUNT(*) AS bookings FROM bookings{W} "
                f"GROUP BY Booking_DayOfWeek ORDER BY bookings DESC", "by day of week")

    # ---- 2. GROUP-BY intents ---------------------------------------------
    if has("by city", "by location", "by area", "per city", "top city", "top cities",
           "which city", "which area", "cities", "city", "location", "area", "pickup"):
        return (f"SELECT Pickup_Location, COUNT(*) AS bookings, "
                f"ROUND(SUM(CASE WHEN Booking_Status='Success' THEN Booking_Value ELSE 0 END),2) AS revenue "
                f"FROM bookings{W} GROUP BY Pickup_Location ORDER BY revenue DESC LIMIT 10", "by city")
    if has("by vehicle", "vehicle type", "per vehicle", "which vehicle", "top vehicle", "vehicle"):
        return (f"SELECT Vehicle_Type, COUNT(*) AS bookings, "
                f"ROUND(SUM(CASE WHEN Booking_Status='Success' THEN Booking_Value ELSE 0 END),2) AS revenue, "
                f"ROUND(AVG(CASE WHEN Booking_Status='Success' THEN Booking_Value END),2) AS avg_value "
                f"FROM bookings{W} GROUP BY Vehicle_Type ORDER BY revenue DESC", "by vehicle")
    if has("by payment", "payment method", "per payment", "which payment", "payment"):
        return (f"SELECT Payment_Method, COUNT(*) AS rides, "
                f"ROUND(SUM(Booking_Value),2) AS revenue FROM bookings "
                f"WHERE Booking_Status='Success' GROUP BY Payment_Method ORDER BY revenue DESC", "by payment")
    if has("by status", "status breakdown", "booking status", "status mix", "status distribution"):
        return (f"SELECT Booking_Status, COUNT(*) AS bookings, "
                f"ROUND(100.0*COUNT(*)/(SELECT COUNT(*) FROM bookings),2) AS pct "
                f"FROM bookings GROUP BY Booking_Status ORDER BY bookings DESC", "by status")

    # ---- 3. TOP-N ---------------------------------------------------------
    m = re.search(r"top\s+(\d+)", q)
    n = int(m.group(1)) if m else 10
    if has("top", "highest", "best", "most", "busiest") and has("route", "trip", "journey", "corridor"):
        return (f"SELECT Pickup_Location, Drop_Location, COUNT(*) AS rides FROM bookings{W} "
                f"GROUP BY Pickup_Location, Drop_Location ORDER BY rides DESC LIMIT {n}", "top routes")
    if has("top", "highest", "best", "most") and has("customer", "rider", "user"):
        return (f"SELECT Customer_ID, COUNT(*) AS bookings FROM bookings{W} "
                f"GROUP BY Customer_ID ORDER BY bookings DESC LIMIT {n}", "top customers")

    # ---- 4. AVERAGES ------------------------------------------------------
    if has("average", "avg", "mean"):
        if has("rating"):
            return (f"SELECT ROUND(AVG(Driver_Ratings),2) AS avg_driver_rating, "
                    f"ROUND(AVG(Customer_Rating),2) AS avg_customer_rating FROM bookings{W}", "avg ratings")
        if has("distance", "km"):
            return (f"SELECT ROUND(AVG(Ride_Distance),2) AS avg_distance_km FROM bookings{W}", "avg distance")
        if has("fare", "value", "price", "ticket", "cost"):
            return (f"SELECT ROUND(AVG(Booking_Value),2) AS avg_booking_value FROM bookings{W}", "avg fare")
        if has("tat", "turnaround", "wait"):
            return (f"SELECT ROUND(AVG(V_TAT),2) AS avg_v_tat, ROUND(AVG(C_TAT),2) AS avg_c_tat FROM bookings{W}", "avg TAT")
        return (f"SELECT ROUND(AVG(Booking_Value),2) AS avg_booking_value, "
                f"ROUND(AVG(Ride_Distance),2) AS avg_distance FROM bookings{W}", "avg")

    # ---- 5. TOTALS --------------------------------------------------------
    if has("revenue", "total value", "total fare", "earnings", "sales", "money", "income", "how much"):
        return (f"SELECT ROUND(SUM(Booking_Value),2) AS total_revenue, COUNT(*) AS rides "
                f"FROM bookings WHERE Booking_Status='Success'"
                + (f" AND {' AND '.join(where)}" if where else ""), "total revenue")
    if has("total distance", "distance travelled", "distance traveled"):
        return (f"SELECT SUM(Ride_Distance) AS total_distance_km FROM bookings{W}", "total distance")

    # ---- 6. CANCELLATION REASONS -----------------------------------------
    if has("why", "reason") and has("cancel"):
        return ("SELECT Canceled_Rides_by_Customer AS reason, COUNT(*) AS n FROM bookings "
                "WHERE Booking_Status='Canceled by Customer' GROUP BY reason "
                "UNION ALL SELECT Canceled_Rides_by_Driver, COUNT(*) FROM bookings "
                "WHERE Booking_Status='Canceled by Driver' GROUP BY Canceled_Rides_by_Driver "
                "ORDER BY n DESC", "cancellation reasons")

    # ---- 7. COUNTS --------------------------------------------------------
    if has("how many", "count", "number of", "total bookings", "total rides", "how often"):
        return (f"SELECT COUNT(*) AS bookings FROM bookings{W}", "count")

    # ---- fallback ---------------------------------------------------------
    return (f"SELECT * FROM bookings{W} LIMIT 20", "sample rows")


def translate(question: str):
    """Return (sql, engine, explanation)."""
    sql = _llm_translate(question)
    if sql:
        return sql, "LLM", "Generated by the LLM engine."
    sql, expl = _rule_translate(question)
    return sql, "Rule-based", expl


if __name__ == "__main__":
    tests = [
        "What is the total revenue?",
        "How many bookings were canceled by the driver?",
        "Show revenue by vehicle type",
        "Top 5 pickup cities by revenue",
        "What is the average fare for Bike rides?",
        "Show the daily booking trend",
        "Which payment method is most used?",
        "How many bookings are there in total?",
        "Average driver rating",
        "Why do customers cancel?",
        "Bookings in Whitefield",
        "What is the busiest hour?",
        "Top 10 routes",
    ]
    for t in tests:
        sql, eng, ex = translate(t)
        print(f"\nQ: {t}\n[{eng} | {ex}]\n{sql}")
