# OLA Rides Analytics — Complete Data Analysis Deliverable

End-to-end analysis of the **OLA July-2024 booking dataset** (103,024 bookings,
Bengaluru): data cleaning, a natural-language Q&A Streamlit app, a Power BI
build kit, a slide deck, and a written report.

## 📁 Package contents

```
ola_project/
├── raw/                      # original source files (xlsx + pptx template)
├── data/                     # cleaned dataset + quality artifacts
│   ├── ola_cleaned.csv       # 103,024 rows × 29 cols (cleaned)
│   ├── ola_cleaned.sqlite    # SQLite copy
│   ├── cleaning_log.md       # every cleaning step
│   ├── quality_scorecard.json
│   ├── profile_before.json / profile_after.json
│   └── analytics.json        # all computed KPIs
├── app/                      # Streamlit NL→SQL app
│   ├── app.py                # main app (3 tabs)
│   ├── nl2sql.py             # NL→SQL translation (LLM + rule engine)
│   ├── build_db.py           # builds ola.db from the cleaned CSV
│   ├── ola.db                # SQLite database (table: bookings)
│   └── requirements.txt
├── powerbi/                  # Power BI kit
│   ├── POWERBI_BUILD_GUIDE.md
│   ├── ola_theme.json
│   ├── dax_measures.md
│   └── ola_pbit_template.md
├── report/
│   └── ANALYSIS_REPORT.md    # executive report
├── presentations/ola_rides_analytics/   # 12-slide deck (Ola template style)
├── clean_data.py             # cleaning pipeline
├── analyze.py                # KPI computation
└── make_charts.py            # chart generation
```

## 🚀 Quick start

### 1. Rebuild the cleaned data (optional — already included)
```bash
pip install pandas openpyxl
python clean_data.py      # -> data/ola_cleaned.csv + scorecard
python analyze.py         # -> data/analytics.json
```

### 2. Run the Streamlit app
```bash
cd app
pip install -r requirements.txt
python build_db.py        # builds ola.db (already included)
streamlit run app.py
```
Then open http://localhost:8501.

**Optional — enable the LLM translation engine:**
```bash
export OPENAI_API_KEY=sk-...        # or ANTHROPIC_API_KEY=...
streamlit run app.py
```
Without a key the app uses the built-in rule-based NL→SQL mapper (covers
totals, averages, counts, group-bys by date/city/vehicle/payment, top-N, trends).

### 3. Power BI
Follow `powerbi/POWERBI_BUILD_GUIDE.md`. Import `data/ola_cleaned.csv`, apply
`powerbi/ola_theme.json`, and paste the measures from `powerbi/dax_measures.md`.

## 📊 Headline numbers (July 2024)
| KPI | Value |
|---|---|
| Total bookings | 103,024 |
| Successful bookings | 63,967 (62.1%) |
| Total revenue | ₹35,080,467 |
| Avg booking value | ₹548.42 |
| Avg ride distance | 22.85 km |
| Avg driver rating | 4.00 |
| Repeat rate | 8.41% |
| Data completeness | 75.2% → 94.8% |
