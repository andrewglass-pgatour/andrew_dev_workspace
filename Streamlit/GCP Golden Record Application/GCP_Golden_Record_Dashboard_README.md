# Golf Course Properties (GCP) Golden Record Dashboard

Streamlit application for viewing Golf Course Properties Golden Record size, source breakdowns, demographic composition, and EZLinks tee sheet / rounds analytics proof-of-concept.

## Features

### 🏠 Home Page: Golden Record Overview & Demographics
- **Key Scale Metrics**: Total Golden Record Profiles, Unique Emails, Unique Phone Numbers, Geocoded State Coverage %, Omnichannel Matched Profiles.
- **Source System Breakdown**: Visual bar chart & table of records contributed by source system (EZLinks, Jonas Club Datamart, Inntopia, TPC Network, TPC Passport, Formstack, Gigya, Archtics, etc.) and source depth integration analysis.
- **Demographic Composition**:
  - Geographic distribution (Top 12 States, Top 10 DMAs, Cities).
  - Age & Generational distribution (histogram, age brackets, average/median age).
  - Contactability & Identity health (Email/Phone/Postal address coverage %, Phone Type breakdown).
  - Profile Creation Timeline (Monthly profile acquisition growth over time).

### ⛳ Proof of Concept: EZLinks Golf Analytics
- **Dynamic Filter Controls**:
  - TPC Properties quick toggle (`[x] TPC Properties Only`).
  - Facility / Club multi-select (TPC Sawgrass, TPC Scottsdale, TPC River Highlands, TPC San Antonio, TPC Southwind, TPC Deere Run, TPC Boston, etc.).
  - Course multi-select.
  - Time Frame presets (All Time, Last 30 Days, Last 60 Days, Last 90 Days, YTD, Custom Date Range).
  - Membership category filter.
- **Dynamic KPIs**: Total Unique Golfers, Total Rounds Played, Average Rounds per Golfer, Active Facilities & Courses, Total Fee Revenue ($).
- **Interactive Analytics Sub-Tabs**:
  1. **📊 Club & Course Performance**: Top facilities by rounds & revenue, course breakdowns, tee time reservation sources (Online, Call Center, Mobile, Phone, Walk-in).
  2. **📈 Rounds Over Time & Seasonality**: Monthly rounds trend line, day-of-week playing patterns, hour-of-day tee time slot distribution.
  3. **🏌️ Golfer Segments & Behavior**: Golfer frequency segments (Casual, Active, Frequent, Heavy), membership category breakdown, group size, walk vs ride ratio.
  4. **📋 Golfer Leaderboard & Directory**: Interactive golfer table sorted by rounds/spend with search by name/email/ID and CSV export capability.

### ℹ️ Data Model Documentation
- Documents underlying dbt models (`GCP_GOLDEN_FAN_MASTER`, `EZLINKS_SUMMARY`, `EZLINKS_ROUNDS_SUMMARY`, `FIRST_PARTY_HEALTH_SUMMARY`), table schemas, join logic, and source system mappings.

---

## App File

- `dbt_snowflake/streamlit_apps/gcp_golden_record_dashboard.py`

---

## How to Run in Snowflake Streamlit

1. Create or open a Streamlit App in Snowflake.
2. Upload or paste the contents of `gcp_golden_record_dashboard.py`.
3. Ensure your Snowflake role has `SELECT` privileges on the following dbt materialized views/tables:
   - `ANALYTICS.PROD_GCP_GOLDEN.GCP_GOLDEN_FAN_MASTER`
   - `ANALYTICS.PROD_EZLINKS.EZLINKS_SUMMARY`
   - `ANALYTICS.PROD_EZLINKS.EZLINKS_ROUNDS_SUMMARY`
   - `ANALYTICS.PROD_GOLDEN.FIRST_PARTY_HEALTH_SUMMARY`

---

## How to Run Locally

```bash
# Install dependencies
pip install streamlit snowflake-snowpark-python pandas altair

# Launch Streamlit app
streamlit run dbt_snowflake/streamlit_apps/gcp_golden_record_dashboard.py
```
