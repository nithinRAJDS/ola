"""Generate charts for the slide deck in the Ola template palette."""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = "presentations/ola_rides_analytics/images"
os.makedirs(OUT, exist_ok=True)
A = json.load(open("data/analytics.json"))

NAVY = "#082836"; GREEN = "#92D050"; BLUE = "#058DC7"; ORANGE = "#ED561B"
CYAN = "#24CBE5"; YELLOW = "#EDEF00"; LGREEN = "#50B432"; GREY = "#AEAEAE"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": "white",
                     "axes.labelcolor": "white", "xtick.color": "white",
                     "ytick.color": "white", "axes.edgecolor": "#3A3A3A"})

def style(ax, title):
    ax.set_facecolor(NAVY)
    for s in ax.spines.values(): s.set_color("#3A3A3A")
    ax.set_title(title, color="white", fontsize=20, fontweight="bold", pad=14)
    ax.grid(axis="y", color="#1c3a48", linewidth=0.8)
    ax.set_axisbelow(True)

def save(fig, name):
    fig.patch.set_facecolor(NAVY)
    fig.savefig(f"{OUT}/{name}", dpi=110, facecolor=NAVY, bbox_inches="tight")
    plt.close(fig)
    print("saved", name)

# 1. Daily trend -------------------------------------------------------------
d = A["daily"]
dates = [x["Booking_Date"][5:] for x in d]
bk = [x["bookings"] for x in d]
rev = [x["revenue"] for x in d]
fig, ax = plt.subplots(figsize=(11, 4.2))
style(ax, "Daily Bookings & Revenue — July 2024")
ax.plot(dates, bk, color=GREEN, linewidth=3, marker="o", markersize=4, label="Bookings")
ax.set_ylabel("Bookings", color=GREEN)
ax2 = ax.twinx()
ax2.plot(dates, rev, color=BLUE, linewidth=2, alpha=.8, label="Revenue")
ax2.set_ylabel("Revenue (₹)", color=BLUE)
ax2.tick_params(colors=BLUE)
ax.set_xticks(range(0, len(dates), 3)); ax.set_xticklabels(dates[::3], rotation=0, fontsize=11)
save(fig, "chart_trend.png")

# 2. Revenue by vehicle ------------------------------------------------------
v = A["by_vehicle"]
names = [x["Vehicle_Type"] for x in v][::-1]
vals = [x["revenue"]/1e6 for x in v][::-1]
fig, ax = plt.subplots(figsize=(9, 4.6))
style(ax, "Revenue by Vehicle Type (₹ millions)")
bars = ax.barh(names, vals, color=[GREEN, BLUE, CYAN, LGREEN, YELLOW, ORANGE, GREY][:len(names)])
for b, val in zip(bars, vals):
    ax.text(b.get_width()+0.05, b.get_y()+b.get_height()/2, f"₹{val:.2f}M",
            va="center", color="white", fontsize=12, fontweight="bold")
ax.set_xlim(0, max(vals)*1.18)
save(fig, "chart_vehicle.png")

# 3. Status donut ------------------------------------------------------------
sd = A["status_dist"]
labels = list(sd.keys()); sizes = list(sd.values())
fig, ax = plt.subplots(figsize=(6.4, 5))
ax.set_facecolor(NAVY)
w, t, at = ax.pie(sizes, labels=None, autopct=lambda p: f"{p:.1f}%",
                  colors=[GREEN, ORANGE, BLUE, YELLOW], startangle=90,
                  wedgeprops=dict(width=0.42, edgecolor=NAVY, linewidth=2),
                  textprops=dict(color="white", fontsize=13, fontweight="bold"))
ax.legend(w, [f"{l} ({s:,})" for l, s in zip(labels, sizes)],
          loc="center", fontsize=11, frameon=False, labelcolor="white")
ax.set_title("Booking Status Mix", color="white", fontsize=20, fontweight="bold")
save(fig, "chart_status.png")

# 4. Payment ----------------------------------------------------------------
p = A["by_payment"]
pn = [x["Payment_Method"] for x in p]; pv = [x["revenue"]/1e6 for x in p]
fig, ax = plt.subplots(figsize=(8, 4.4))
style(ax, "Revenue by Payment Method (₹ millions)")
bars = ax.bar(pn, pv, color=[GREEN, BLUE, CYAN, ORANGE])
for b, val in zip(bars, pv):
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.15, f"₹{val:.2f}M",
            ha="center", color="white", fontsize=12, fontweight="bold")
ax.set_ylim(0, max(pv)*1.15)
save(fig, "chart_payment.png")

# 5. Top cities -------------------------------------------------------------
c = A["by_city_top10"]
cn = [x["Pickup_Location"] for x in c][::-1]; cv = [x["revenue"]/1e3 for x in c][::-1]
fig, ax = plt.subplots(figsize=(9, 5))
style(ax, "Top 10 Pickup Areas by Revenue (₹ thousands)")
ax.barh(cn, cv, color=GREEN)
for i, val in enumerate(cv):
    ax.text(val+3, i, f"₹{val:.0f}k", va="center", color="white", fontsize=11)
ax.set_xlim(0, max(cv)*1.15)
save(fig, "chart_city.png")

# 6. Hourly -----------------------------------------------------------------
h = A["hourly"]
hn = [x["Booking_Hour"] for x in h]; hv = [x["bookings"] for x in h]
fig, ax = plt.subplots(figsize=(11, 4))
style(ax, "Bookings by Hour of Day")
ax.bar(hn, hv, color=[GREEN if v == max(hv) else BLUE for v in hv])
ax.set_xticks(range(0, 24)); ax.set_xlabel("Hour (0–23)")
save(fig, "chart_hourly.png")

# 7. Quality before/after ---------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 4.4))
style(ax, "Data Completeness: Before vs After Cleaning")
bars = ax.bar(["Before", "After"], [75.22, 94.77], color=[ORANGE, GREEN], width=0.5)
for b, val in zip(bars, [75.22, 94.77]):
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+1, f"{val}%",
            ha="center", color="white", fontsize=16, fontweight="bold")
ax.set_ylim(0, 110); ax.set_ylabel("Completeness %")
save(fig, "chart_quality.png")

# 8. Vehicle success rate ---------------------------------------------------
fig, ax = plt.subplots(figsize=(9, 4.4))
style(ax, "Success Rate by Vehicle Type (%)")
vn = [x["Vehicle_Type"] for x in v]; vs = [x["success_rate"] for x in v]
bars = ax.bar(vn, vs, color=GREEN)
for b, val in zip(bars, vs):
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.3, f"{val:.1f}%",
            ha="center", color="white", fontsize=12, fontweight="bold")
ax.set_ylim(0, 70)
save(fig, "chart_success.png")

print("ALL CHARTS DONE")
