"""
app.py — OLA Rides Analytics: Natural-Language Q&A over SQL
===========================================================
A Streamlit app that loads the cleaned OLA dataset into SQLite and lets a
customer ask questions in plain English, see the generated SQL, the result
table and an auto-selected chart.

Tabs:
  • Ask the Data   — NL -> SQL Q&A with example buttons
  • Data Explorer  — filterable table + quick charts
  • Data Quality   — scorecard, missingness, outliers

Run:  streamlit run app.py
"""
import os
import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px

from nl2sql import translate, SCHEMA

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "ola.db")

st.set_page_config(page_title="OLA Rides Analytics", page_icon="🚕", layout="wide")

# ---- Ola brand palette (from the slide template) ---------------------------
NAVY = "#082836"
GREEN = "#92D050"
ACCENT = "#058DC7"

st.markdown(f"""
<style>
  .stApp {{ background: #F3F3F3; }}
  h1, h2, h3 {{ color: {NAVY}; font-family: Poppins, sans-serif; }}
  .kpi {{ background:{NAVY}; color:white; border-radius:12px; padding:16px 20px; }}
  .kpi .v {{ font-size:30px; font-weight:700; color:{GREEN}; }}
  .kpi .l {{ font-size:13px; opacity:.85; }}
  .stButton>button {{ background:{GREEN}; color:{NAVY}; font-weight:600; border:none; border-radius:8px; }}
  code {{ color:{ACCENT}; }}
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_df():
    con = sqlite3.connect(DB)
    df = pd.read_sql("SELECT * FROM bookings", con)
    con.close()
    return df


def run_sql(sql):
    con = sqlite3.connect(DB)
    try:
        out = pd.read_sql(sql, con)
        return out, None
    except Exception as e:
        return None, str(e)
    finally:
        con.close()


def auto_chart(df):
    """Pick a sensible chart from the result shape."""
    if df is None or df.empty or df.shape[1] < 2:
        return None
    num = df.select_dtypes("number").columns.tolist()
    cat = [c for c in df.columns if c not in num]
    if not num:
        return None
    y = num[0]
    if cat:
        x = cat[0]
        if len(df) <= 12:
            return px.bar(df, x=x, y=y, color=x, color_discrete_sequence=px.colors.qualitative.Set2)
        return px.line(df, x=x, y=y, markers=True)
    return px.histogram(df, x=y)


# ===========================================================================
st.title("🚕 OLA Rides Analytics")
st.caption("Natural-language Q&A over the cleaned July-2024 Ola booking dataset · "
           "103,024 bookings · Bengaluru")

df = load_df()
tab_ask, tab_explore, tab_quality = st.tabs(["💬 Ask the Data", "🔎 Data Explorer", "✅ Data Quality"])

# ---------------------------------------------------------------------------
# TAB 1 — ASK
# ---------------------------------------------------------------------------
with tab_ask:
    st.subheader("Ask a question in plain English")
    st.write("The app translates your question into SQL, runs it on the cleaned "
             "database, and charts the answer.")

    examples = [
        "What is the total revenue?",
        "How many bookings were canceled by the driver?",
        "Show revenue by vehicle type",
        "Top 10 pickup cities by revenue",
        "What is the average fare for Bike rides?",
        "Show the daily booking trend",
        "Which payment method is most used?",
        "Average driver rating",
        "Why do customers cancel?",
    ]
    cols = st.columns(3)
    clicked = None
    for i, ex in enumerate(examples):
        if cols[i % 3].button(ex, key=f"ex{i}", use_container_width=True):
            clicked = ex

    q = st.text_input("Your question", value=clicked or "",
                      placeholder="e.g. Which vehicle type earns the most revenue?")

    if q:
        sql, engine, expl = translate(q)
        st.markdown(f"**Generated SQL** &nbsp;·&nbsp; engine: `{engine}` ({expl})")
        st.code(sql, language="sql")
        res, err = run_sql(sql)
        if err:
            st.error(f"SQL error: {err}")
        else:
            st.markdown(f"**Result** — {len(res):,} row(s)")
            st.dataframe(res, use_container_width=True)
            fig = auto_chart(res)
            if fig:
                fig.update_layout(template="plotly_white", height=420,
                                  colorway=[GREEN, ACCENT, NAVY, "#ED561B", "#50B432"])
                st.plotly_chart(fig, use_container_width=True)
            csv = res.to_csv(index=False).encode()
            st.download_button("⬇ Download result CSV", csv, "ola_query_result.csv", "text/csv")

    with st.expander("ℹ️ How the translation works"):
        st.markdown(
            "- **LLM engine** — if `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` is set, the "
            "question + schema is sent to the model, which returns a read-only SQLite `SELECT`.\n"
            "- **Rule engine** — otherwise a keyword/pattern mapper covers totals, averages, "
            "counts, group-bys (date / city / vehicle / payment), top-N and trends.\n"
            "- Only read-only `SELECT` statements are executed.")

# ---------------------------------------------------------------------------
# TAB 2 — EXPLORER
# ---------------------------------------------------------------------------
with tab_explore:
    st.subheader("Explore the cleaned data")
    c1, c2, c3, c4 = st.columns(4)
    veh = c1.multiselect("Vehicle type", sorted(df.Vehicle_Type.unique()))
    stat = c2.multiselect("Booking status", sorted(df.Booking_Status.unique()))
    pay = c3.multiselect("Payment method", sorted(df.Payment_Method.unique()))
    city = c4.multiselect("Pickup location", sorted(df.Pickup_Location.unique()))

    f = df.copy()
    if veh:  f = f[f.Vehicle_Type.isin(veh)]
    if stat: f = f[f.Booking_Status.isin(stat)]
    if pay:  f = f[f.Payment_Method.isin(pay)]
    if city: f = f[f.Pickup_Location.isin(city)]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Bookings", f"{len(f):,}")
    m2.metric("Revenue (₹)", f"{f.loc[f.Booking_Status=='Success','Booking_Value'].sum():,.0f}")
    m3.metric("Success rate", f"{100*(f.Booking_Status=='Success').mean():.1f}%")
    m4.metric("Avg fare (₹)", f"{f.loc[f.Booking_Status=='Success','Booking_Value'].mean():.0f}")

    st.dataframe(f.head(500), use_container_width=True, height=320)

    g1, g2 = st.columns(2)
    with g1:
        vc = f.Vehicle_Type.value_counts().reset_index()
        vc.columns = ["Vehicle_Type", "bookings"]
        st.plotly_chart(px.bar(vc, x="Vehicle_Type", y="bookings", color="Vehicle_Type",
                               title="Bookings by vehicle type",
                               color_discrete_sequence=px.colors.qualitative.Set2),
                        use_container_width=True)
    with g2:
        sc = f.Booking_Status.value_counts().reset_index()
        sc.columns = ["Status", "n"]
        st.plotly_chart(px.pie(sc, names="Status", values="n", hole=.5,
                               title="Booking status mix",
                               color_discrete_sequence=[GREEN, ACCENT, "#ED561B", NAVY]),
                        use_container_width=True)

# ---------------------------------------------------------------------------
# TAB 3 — DATA QUALITY
# ---------------------------------------------------------------------------
with tab_quality:
    st.subheader("Data-quality scorecard")
    import json
    sc_path = os.path.join(HERE, "..", "data", "quality_scorecard.json")
    if os.path.exists(sc_path):
        sc = json.load(open(sc_path))
        a, b, c, d = st.columns(4)
        a.metric("Rows", f"{sc['rows_after']:,}")
        b.metric("Completeness", f"{sc['completeness_after_pct']}%",
                 f"+{sc['completeness_after_pct']-sc['completeness_before_pct']:.1f} pts")
        c.metric("Duplicate rows", sc["duplicate_rows_after"])
        d.metric("Unparseable dates", sc["unparseable_datetimes"])
        st.info(sc["structural_missing_note"])

    st.markdown("**Missing values per column (cleaned data)**")
    miss = df.isna().sum().reset_index()
    miss.columns = ["column", "missing"]
    miss["missing_pct"] = (100 * miss.missing / len(df)).round(2)
    miss = miss[miss.missing > 0].sort_values("missing", ascending=False)
    st.dataframe(miss, use_container_width=True)
    if not miss.empty:
        st.plotly_chart(px.bar(miss, x="column", y="missing_pct",
                               title="% missing by column (structural NULLs only)",
                               color_discrete_sequence=[ACCENT]), use_container_width=True)

    st.markdown("**Outlier flags (IQR method)**")
    ocols = [c for c in df.columns if c.endswith("_is_outlier")]
    if ocols:
        od = pd.DataFrame({"column": [c.replace("_is_outlier", "") for c in ocols],
                           "flagged": [int(df[c].sum()) for c in ocols]})
        st.dataframe(od, use_container_width=True)

    st.markdown("**Schema reference**")
    st.code(SCHEMA, language="text")
