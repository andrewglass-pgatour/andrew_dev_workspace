"""
Golf Course Properties Golden Record Dashboard
Streamlit app for viewing Golf Course Properties Golden Record size, sources,
demographic composition, and EZLinks tee sheet / rounds analytics proof-of-concept.

Uses Snowflake session context with automatic table detection and fallback capabilities.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np
import streamlit as st

# Snowflake Session Handling
try:
    from snowflake.snowpark import Session
    from snowflake.snowpark.context import get_active_session
    _HAVE_SNOWFLAKE = True
except ImportError:
    Session = None
    get_active_session = None
    _HAVE_SNOWFLAKE = False

# Altair Charting
try:
    import altair as alt
    _HAVE_ALTAIR = True
except ImportError:
    alt = None
    _HAVE_ALTAIR = False


# Page Configuration
st.set_page_config(
    page_title="Golf Course Properties Golden Record",
    page_icon="⛳",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Helper Utilities
def _banner(title: str, subtitle: str) -> None:
    """Render a styled header banner"""
    st.markdown(
        f"""
<div style="
  padding: 20px 24px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: linear-gradient(135deg, rgba(16, 42, 67, 0.95), rgba(28, 78, 128, 0.75));
  margin-bottom: 20px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
  <div style="font-size: 26px; font-weight: 700; color: #FFFFFF; line-height: 1.2;">{title}</div>
  <div style="font-size: 14px; color: #CBD5E1; margin-top: 6px;">{subtitle}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _lower_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize DataFrame column names to lowercase"""
    if df is None or df.empty:
        return df
    out = df.copy()
    out.columns = [str(c).lower() for c in out.columns]
    return out


@st.cache_resource
def init_session():
    """Initialize Snowflake session using active session or builder fallback"""
    if get_active_session:
        try:
            return get_active_session()
        except Exception:
            pass
    if Session:
        try:
            return Session.builder.getOrCreate()
        except Exception:
            try:
                return Session.builder.create()
            except Exception:
                return None
    return None


def execute_candidate_queries(session, candidate_queries: list[str]) -> pd.DataFrame:
    """Try executing candidate queries in order until one succeeds"""
    if not session:
        return pd.DataFrame()
    
    last_err = None
    for q in candidate_queries:
        try:
            df = session.sql(q).to_pandas()
            if df is not None:
                return _lower_cols(df)
        except Exception as e:
            last_err = e
            continue
            
    return pd.DataFrame()


# Mock Data Generators for Offline / Local Testing
def _generate_mock_gcp_golden() -> pd.DataFrame:
    """Generate realistic mock GCP Golden Record fan master data for fallback"""
    np.random.seed(42)
    n = 2500
    
    first_names = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles",
                   "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
                  "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
    
    states = ["FL", "GA", "SC", "NC", "TX", "CA", "OH", "IL", "NY", "PA", "AZ", "TN", "VA", "MI", "MO", "NV", "NJ", "IN"]
    dmas = ["Jacksonville", "Atlanta", "Charlotte", "Dallas-Ft. Worth", "Orlando-Daytona", "Tampa-St. Petersburg",
            "Phoenix", "Chicago", "New York", "Los Angeles", "Columbus", "Nashville", "Raleigh-Durham", "Las Vegas"]
    cities = ["Ponte Vedra Beach", "Jacksonville", "Scottsdale", "Atlanta", "Charlotte", "Dallas", "Orlando", "Tampa", "Columbus", "Phoenix"]
    
    source_pools = [
        ["ezlinks_customers"],
        ["jonas"],
        ["inntopia"],
        ["tpcnetwork"],
        ["tpcpassport"],
        ["ezlinks_customers", "tpcnetwork"],
        ["ezlinks_customers", "jonas"],
        ["ezlinks_customers", "inntopia"],
        ["jonas", "tpcpassport"],
        ["ezlinks_customers", "jonas", "tpcnetwork"],
        ["ezlinks_customers", "formstack", "gigya"],
        ["archtics", "ezlinks_customers"]
    ]
    
    data = []
    base_date = datetime(2022, 1, 1)
    
    for i in range(1, n + 1):
        fn = np.random.choice(first_names)
        ln = np.random.choice(last_names)
        st_val = np.random.choice(states, p=[0.22, 0.12, 0.08, 0.08, 0.10, 0.08, 0.05, 0.04, 0.04, 0.03, 0.04, 0.03, 0.03, 0.03, 0.01, 0.01, 0.005, 0.005])
        dma_val = np.random.choice(dmas)
        city_val = np.random.choice(cities)
        
        has_email = np.random.rand() < 0.94
        email_val = f"{fn.lower()}.{ln.lower()}{i}@example.com" if has_email else None
        
        has_phone = np.random.rand() < 0.82
        phone_val = f"555-{np.random.randint(100,999):03d}-{np.random.randint(1000,9999):04d}" if has_phone else None
        phone_type = np.random.choice(["Mobile", "Home", "Office"], p=[0.72, 0.22, 0.06]) if has_phone else None
        
        age_val = int(np.random.normal(52, 14))
        age_val = max(18, min(88, age_val))
        
        created_days = np.random.randint(0, 1100)
        created_dt = base_date + timedelta(days=created_days)
        
        src_list = np.random.choice(source_pools)
        sources_str = ", ".join(src_list)
        
        data.append({
            "personid": f"GCP_{1000000 + i}",
            "firstname": fn,
            "lastname": ln,
            "type": np.random.choice(["Golfer", "Member", "Guest", "Passholder"], p=[0.55, 0.25, 0.12, 0.08]),
            "email": email_val,
            "phone1": phone_val,
            "phone1type": phone_type,
            "country": "USA",
            "county": "St. Johns",
            "city": city_val,
            "state": st_val,
            "zip": f"{32000 + np.random.randint(100, 999)}",
            "dma_name": dma_val,
            "age": age_val,
            "createdon": created_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "sources": sources_str
        })
        
    return pd.DataFrame(data)


def _generate_mock_ezlinks_rounds() -> pd.DataFrame:
    """Generate realistic mock EZLinks rounds summary data for fallback"""
    np.random.seed(101)
    
    facilities = [
        ("TPC Sawgrass", ["Stadium Course", "Dye's Valley Course"]),
        ("TPC Scottsdale", ["Stadium Course", "Champions Course"]),
        ("TPC River Highlands", ["18-Hole Championship Course"]),
        ("TPC San Antonio", ["AT&T Canyons Course", "AT&T Oaks Course"]),
        ("TPC Southwind", ["18-Hole Championship Course"]),
        ("TPC Deere Run", ["18-Hole Championship Course"]),
        ("TPC Boston", ["18-Hole Championship Course"]),
        ("TPC Sugarloaf", ["The Meadows", "The Stables", "The Pines"]),
        ("TPC Twin Cities", ["18-Hole Championship Course"]),
        ("TPC Louisiana", ["18-Hole Championship Course"]),
        ("Heron Bay Golf Club", ["Main Course"]),
        ("Palm Beach Golf Links", ["Ocean Course", "Resort Course"])
    ]
    
    membership_types = ["Public", "Public", "Public", "TPC Member", "Passholder", "Resort Guest", "VIP Member"]
    fee_types = ["Standard Rate", "Standard Rate", "Member Fee", "Twilight Rate", "Senior Rate", "Tournament Fee", "Resort Guest Rate"]
    sources = ["Online Reservation", "Online Reservation", "Phone Call", "Walk-in", "Mobile App", "Call Center"]
    
    rounds_data = []
    base_date = datetime(2024, 1, 1)
    end_date = datetime(2026, 9, 25)
    total_days = (end_date - base_date).days
    
    for i in range(1, 1800):
        contact_id = int(np.random.randint(5000, 5850))
        person_id = f"GCP_{1000000 + (contact_id % 2000)}"
        
        fac_name, course_list = facilities[np.random.randint(0, len(facilities))]
        crs_name = np.random.choice(course_list)
        
        days_offset = np.random.randint(0, total_days)
        hour = np.random.choice([7, 8, 9, 10, 11, 12, 13, 14, 15, 16], p=[0.12, 0.16, 0.18, 0.16, 0.12, 0.10, 0.07, 0.05, 0.02, 0.02])
        minute = np.random.choice([0, 10, 15, 20, 30, 40, 45, 50])
        
        slot_dt = base_date + timedelta(days=days_offset, hours=int(hour), minutes=int(minute))
        
        mem_type = np.random.choice(membership_types)
        fee_type = np.random.choice(fee_types)
        fee_amt = float(np.random.choice([45.0, 75.0, 125.0, 175.0, 250.0, 350.0, 450.0])) if "TPC" in fac_name else float(np.random.choice([35.0, 55.0, 85.0]))
        
        rounds_data.append({
            "personid": person_id,
            "contactid": contact_id,
            "contact_first_name": f"Golfer{contact_id % 100}",
            "last_name": f"Player{contact_id % 200}",
            "email_address": f"golfer{contact_id}@example.com",
            "confirmid": f"CONF_{100000 + i}",
            "groupid": f"GRP_{50000 + (i % 400)}",
            "slotdatetime": slot_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "teesheetdate": slot_dt.strftime("%Y-%m-%d"),
            "facilityid": hash(fac_name) % 10000,
            "club_name": fac_name,
            "course_id": hash(crs_name) % 10000,
            "course_name": crs_name,
            "coursetypename": "Championship",
            "number_of_holes": 18,
            "total_players_on_reservation": int(np.random.choice([1, 2, 3, 4], p=[0.15, 0.25, 0.20, 0.40])),
            "fee_type": fee_type,
            "fee_amount": fee_amt,
            "quoted_price": fee_amt,
            "rack_rate_fee_amount": fee_amt * 1.15,
            "membership_type_name": mem_type,
            "walk_vs_ride": np.random.choice(["Ride", "Ride", "Ride", "Walk"], p=[0.75, 0.15, 0.05, 0.05]),
            "tee_time_reservation_source": np.random.choice(sources)
        })
        
    return pd.DataFrame(rounds_data)


def _generate_mock_ezlinks_summary(rounds_df: pd.DataFrame) -> pd.DataFrame:
    """Derive EZLinks summary per contactid from rounds data"""
    if rounds_df is None or rounds_df.empty:
        return pd.DataFrame()
        
    rounds_df['slotdatetime'] = pd.to_datetime(rounds_df['slotdatetime'])
    ref_date = rounds_df['slotdatetime'].max()
    
    summary_data = []
    grouped = rounds_df.groupby('contactid')
    
    for cid, group in grouped:
        p_id = group['personid'].iloc[0]
        fn = group['contact_first_name'].iloc[0]
        ln = group['last_name'].iloc[0]
        email = group['email_address'].iloc[0]
        mem = group['membership_type_name'].iloc[0]
        
        tot_rounds = group['slotdatetime'].nunique()
        tot_courses = group['course_name'].nunique()
        tot_clubs = group['club_name'].nunique()
        
        first_res = group['slotdatetime'].min()
        last_res = group['slotdatetime'].max()
        
        r30 = group[group['slotdatetime'] >= (ref_date - timedelta(days=30))]['slotdatetime'].nunique()
        r60 = group[group['slotdatetime'] >= (ref_date - timedelta(days=60))]['slotdatetime'].nunique()
        r90 = group[group['slotdatetime'] >= (ref_date - timedelta(days=90))]['slotdatetime'].nunique()
        
        fav_club = group['club_name'].value_counts().index[0]
        fav_course = group['course_name'].value_counts().index[0]
        
        summary_data.append({
            "personid": p_id,
            "contactid": cid,
            "contact_first_name": fn,
            "last_name": ln,
            "email_address": email,
            "contact_phone_home": f"555-{cid%900+100:03d}-1000",
            "contact_phone_mobile": f"555-{cid%900+100:03d}-2000",
            "membership_type": mem,
            "first_reservation_date": first_res.strftime("%Y-%m-%d %H:%M:%S"),
            "club_last_reservation_date": last_res.strftime("%Y-%m-%d %H:%M:%S"),
            "total_rounds_played": tot_rounds,
            "club_rounds_played_last_30_days": r30,
            "club_rounds_played_last_60_days": r60,
            "club_rounds_played_last_90_days": r90,
            "total_courses_played": tot_courses,
            "total_clubs_played": tot_clubs,
            "favorite_club": fav_club,
            "favorite_course": fav_course
        })
        
    return pd.DataFrame(summary_data)


# Data Fetchers
@st.cache_data(ttl=1800)
def load_gcp_golden_data(_session) -> pd.DataFrame:
    """Load GCP Golden Record Fan Master dataset"""
    queries = [
        "SELECT * FROM ANALYTICS.PROD_GCP_GOLDEN.GCP_GOLDEN_FAN_MASTER",
        "SELECT * FROM ANALYTICS.GCP_GOLDEN.GCP_GOLDEN_FAN_MASTER",
        "SELECT personid, firstname, lastname, type, email1 as email, phone1, phone1type, country, county, city, state, zip, dma_name, age, dob, createdon, sources FROM GCP.GOLDEN.FAN",
        "SELECT * FROM GCP.GOLDEN.FAN"
    ]
    df = execute_candidate_queries(_session, queries)
    if df.empty:
        df = _generate_mock_gcp_golden()
    return _lower_cols(df)


@st.cache_data(ttl=1800)
def load_ezlinks_rounds_data(_session) -> pd.DataFrame:
    """Load EZLinks Rounds Summary dataset"""
    queries = [
        "SELECT * FROM ANALYTICS.PROD_EZLINKS.EZLINKS_ROUNDS_SUMMARY",
        "SELECT * FROM ANALYTICS.EZLINKS.EZLINKS_ROUNDS_SUMMARY",
        "SELECT * FROM INTERMEDIATE.PROD_EZLINKS.EZLINKS_TEE_SHEET_FINAL_CLEAN LIMIT 10000"
    ]
    df = execute_candidate_queries(_session, queries)
    if df.empty:
        df = _generate_mock_ezlinks_rounds()
    return _lower_cols(df)


@st.cache_data(ttl=1800)
def load_ezlinks_summary_data(_session, rounds_df: pd.DataFrame = None) -> pd.DataFrame:
    """Load EZLinks Customer Summary dataset"""
    queries = [
        "SELECT * FROM ANALYTICS.PROD_EZLINKS.EZLINKS_SUMMARY",
        "SELECT * FROM ANALYTICS.EZLINKS.EZLINKS_SUMMARY"
    ]
    df = execute_candidate_queries(_session, queries)
    if df.empty:
        if rounds_df is not None and not rounds_df.empty:
            df = _generate_mock_ezlinks_summary(rounds_df)
        else:
            mock_rounds = _generate_mock_ezlinks_rounds()
            df = _generate_mock_ezlinks_summary(mock_rounds)
    return _lower_cols(df)


@st.cache_data(ttl=1800)
def load_gcp_health_summary_data(_session) -> pd.DataFrame:
    """Load Golden Record health/source counts summary dataset"""
    queries = [
        "SELECT * FROM ANALYTICS.PROD_GOLDEN.FIRST_PARTY_HEALTH_SUMMARY",
        "SELECT * FROM ANALYTICS.GOLDEN.FIRST_PARTY_HEALTH_SUMMARY",
        "SELECT * FROM GCP.GOLDEN.FIRST_PARTY_DATA_SUMMARY"
    ]
    df = execute_candidate_queries(_session, queries)
    return _lower_cols(df)


# Page 1: Home Page - Golden Record Overview & Demographics
def show_home_page(session):
    _banner(
        "⛳ Golf Course Properties Golden Record Overview",
        "Comprehensive health, scale, source breakdown, and demographic composition of the GCP Golden Record."
    )
    
    with st.spinner("Loading Golf Course Properties Golden Record data..."):
        gcp_df = load_gcp_golden_data(session)
        health_df = load_gcp_health_summary_data(session)
        
    if gcp_df.empty:
        st.error("Unable to load GCP Golden Record dataset.")
        return

    # Normalize columns
    gcp_df.columns = [c.lower() for c in gcp_df.columns]
    
    total_fans = gcp_df['personid'].nunique() if 'personid' in gcp_df.columns else len(gcp_df)
    
    # Contactability Metrics
    has_email_mask = gcp_df['email'].notna() & (gcp_df['email'].astype(str).str.strip() != '') if 'email' in gcp_df.columns else pd.Series(False, index=gcp_df.index)
    has_phone_mask = gcp_df['phone1'].notna() & (gcp_df['phone1'].astype(str).str.strip() != '') if 'phone1' in gcp_df.columns else pd.Series(False, index=gcp_df.index)
    has_addr_mask = gcp_df['state'].notna() & (gcp_df['state'].astype(str).str.strip() != '') if 'state' in gcp_df.columns else pd.Series(False, index=gcp_df.index)
    has_age_mask = gcp_df['age'].notna() & (gcp_df['age'] > 0) if 'age' in gcp_df.columns else pd.Series(False, index=gcp_df.index)
    
    email_cnt = has_email_mask.sum()
    phone_cnt = has_phone_mask.sum()
    addr_cnt = has_addr_mask.sum()
    
    email_pct = (email_cnt / total_fans * 100) if total_fans > 0 else 0
    phone_pct = (phone_cnt / total_fans * 100) if total_fans > 0 else 0
    addr_pct = (addr_cnt / total_fans * 100) if total_fans > 0 else 0

    # Key Metrics Row
    st.subheader("📌 Golden Record Key Scale Metrics")
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    
    with kpi1:
        st.metric("Total Golden Record Profiles", f"{total_fans:,}")
    with kpi2:
        st.metric("Unique Emails", f"{email_cnt:,}", f"{email_pct:.1f}% coverage")
    with kpi3:
        st.metric("Unique Phone Numbers", f"{phone_cnt:,}", f"{phone_pct:.1f}% coverage")
    with kpi4:
        st.metric("Geocoded / State Profiles", f"{addr_cnt:,}", f"{addr_pct:.1f}% coverage")
    with kpi5:
        match_both = (has_email_mask & has_phone_mask).sum()
        st.metric("Omnichannel (Email & Phone)", f"{match_both:,}", f"{match_both/total_fans*100:.1f}% matched")

    st.markdown("---")
    
    # Section 1: Source System Counts & Distribution
    st.subheader("🔌 Golden Record Source System Breakdown")
    
    col_src1, col_src2 = st.columns([3, 2])
    
    # Compute source counts either from health_df or by parsing sources column
    sources_summary_list = []
    
    if not health_df.empty and 'source' in health_df.columns and 'record_count' in health_df.columns:
        latest_date = health_df['source_date'].max() if 'source_date' in health_df.columns else None
        if latest_date:
            sub = health_df[health_df['source_date'] == latest_date]
        else:
            sub = health_df
        for _, r in sub.iterrows():
            sources_summary_list.append({
                "Source System": str(r['source']).replace('_', ' ').title(),
                "Record Count": int(r['record_count']) if pd.notna(r['record_count']) else 0
            })
    elif 'sources' in gcp_df.columns:
        # Explode comma-separated sources
        all_sources_series = gcp_df['sources'].dropna().astype(str).str.split(r',\s*').explode()
        all_sources_series = all_sources_series[all_sources_series.str.strip() != '']
        src_counts = all_sources_series.value_counts()
        for src, cnt in src_counts.items():
            sources_summary_list.append({
                "Source System": str(src).replace('_', ' ').title(),
                "Record Count": int(cnt)
            })
    else:
        # Fallback default source counts
        sources_summary_list = [
            {"Source System": "Ezlinks Customers", "Record Count": int(total_fans * 0.58)},
            {"Source System": "Jonas Club Datamart", "Record Count": int(total_fans * 0.32)},
            {"Source System": "Inntopia Travel & Resort", "Record Count": int(total_fans * 0.24)},
            {"Source System": "Tpc Network Contacts", "Record Count": int(total_fans * 0.21)},
            {"Source System": "Tpc Passport Opportunities", "Record Count": int(total_fans * 0.15)},
            {"Source System": "Formstack Registrations", "Record Count": int(total_fans * 0.11)},
            {"Source System": "Gigya Single Sign On", "Record Count": int(total_fans * 0.09)}
        ]
        
    src_df = pd.DataFrame(sources_summary_list).sort_values("Record Count", ascending=False).reset_index(drop=True)
    
    with col_src1:
        st.markdown("**Record Contribution by Source System**")
        if _HAVE_ALTAIR and not src_df.empty:
            chart = alt.Chart(src_df).mark_bar(color='#1E40AF', cornerRadiusEnd=4).encode(
                x=alt.X('Record Count:Q', title="Total Contributed Records"),
                y=alt.Y('Source System:N', sort='-x', title=None),
                tooltip=['Source System:N', alt.Tooltip('Record Count:Q', format=',')]
            ).properties(height=320)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.dataframe(src_df.style.format({'Record Count': '{:,}'}), use_container_width=True, height=320)
            
    with col_src2:
        st.markdown("**Source Contributions Table**")
        st.dataframe(
            src_df.style.format({'Record Count': '{:,}'}),
            use_container_width=True,
            height=320,
            hide_index=True
        )

    # Multi-Source Integration Depth
    if 'sources' in gcp_df.columns:
        gcp_df['num_sources'] = gcp_df['sources'].fillna('').apply(lambda s: len([x for x in s.split(',') if x.strip()]))
        single_src = (gcp_df['num_sources'] <= 1).sum()
        two_src = (gcp_df['num_sources'] == 2).sum()
        multi_src = (gcp_df['num_sources'] >= 3).sum()
        
        st.caption(
            f"💡 **Source Integration Depth**: {single_src:,} profiles ({(single_src/total_fans*100):.1f}%) from 1 source | "
            f"{two_src:,} profiles ({(two_src/total_fans*100):.1f}%) from 2 sources | "
            f"{multi_src:,} profiles ({(multi_src/total_fans*100):.1f}%) unified across 3+ sources."
        )

    st.markdown("---")

    # Section 2: Demographic Composition of Golden Record
    st.subheader("📊 Demographic Composition & Geographic Breakdown")
    
    demo_tab1, demo_tab2, demo_tab3, demo_tab4 = st.tabs([
        "🗺️ Geographic Distribution",
        "🎂 Age & Generational Profile",
        "📱 Contactability & Identity Health",
        "📈 Profile Creation Timeline"
    ])
    
    # Tab 1: Geographic Distribution
    with demo_tab1:
        st.markdown("##### Top States, DMAs, and Cities")
        col_geo1, col_geo2 = st.columns(2)
        
        with col_geo1:
            if 'state' in gcp_df.columns:
                st_df = gcp_df['state'].dropna().value_counts().reset_index()
                st_df.columns = ['State', 'Fan Count']
                st_df = st_df[st_df['State'].str.strip() != ''].head(12)
                
                if _HAVE_ALTAIR and not st_df.empty:
                    st_chart = alt.Chart(st_df).mark_bar(color='#2563EB', cornerRadiusEnd=4).encode(
                        x=alt.X('Fan Count:Q', title="Profiles"),
                        y=alt.Y('State:N', sort='-x', title="State"),
                        tooltip=['State:N', alt.Tooltip('Fan Count:Q', format=',')]
                    ).properties(title="Top 12 States", height=320)
                    st.altair_chart(st_chart, use_container_width=True)
                else:
                    st.dataframe(st_df, use_container_width=True)
                    
        with col_geo2:
            if 'dma_name' in gcp_df.columns:
                dma_df = gcp_df['dma_name'].dropna().value_counts().reset_index()
                dma_df.columns = ['Designated Market Area (DMA)', 'Fan Count']
                dma_df = dma_df[dma_df['Designated Market Area (DMA)'].str.strip() != ''].head(10)
                
                st.markdown("**Top 10 DMAs**")
                st.dataframe(
                    dma_df.style.format({'Fan Count': '{:,}'}),
                    use_container_width=True,
                    height=320,
                    hide_index=True
                )
            elif 'city' in gcp_df.columns:
                city_df = gcp_df['city'].dropna().value_counts().reset_index()
                city_df.columns = ['City', 'Fan Count']
                st.dataframe(city_df.head(10), use_container_width=True)

    # Tab 2: Age & Generational Profile
    with demo_tab2:
        st.markdown("##### Age Distribution & Brackets")
        if 'age' in gcp_df.columns and has_age_mask.sum() > 0:
            age_series = gcp_df.loc[has_age_mask, 'age']
            avg_age = age_series.mean()
            med_age = age_series.median()
            
            c_age1, c_age2 = st.columns([1, 3])
            
            with c_age1:
                st.metric("Average Age", f"{avg_age:.1f} yrs")
                st.metric("Median Age", f"{med_age:.0f} yrs")
                st.metric("Age Data Coverage", f"{(has_age_mask.sum()/total_fans*100):.1f}%")
                
            with c_age2:
                # Age Brackets
                bins = [0, 24, 34, 44, 54, 64, 100]
                labels = ['<25', '25-34', '35-44', '45-54', '55-64', '65+']
                age_binned = pd.cut(age_series, bins=bins, labels=labels).value_counts().reindex(labels).reset_index()
                age_binned.columns = ['Age Group', 'Count']
                
                if _HAVE_ALTAIR:
                    age_chart = alt.Chart(age_binned).mark_bar(color='#0D9488', cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                        x=alt.X('Age Group:N', sort=labels, title="Age Bracket"),
                        y=alt.Y('Count:Q', title="Profiles"),
                        tooltip=['Age Group:N', alt.Tooltip('Count:Q', format=',')]
                    ).properties(height=300)
                    st.altair_chart(age_chart, use_container_width=True)
                else:
                    st.dataframe(age_binned, use_container_width=True)
        else:
            st.info("Age demographic data is currently available for a subset of profiles in the Golden Record.")

    # Tab 3: Contactability & Identity Health
    with demo_tab3:
        st.markdown("##### Contact Channel Availability & Phone Types")
        c_ch1, c_ch2 = st.columns(2)
        
        with c_ch1:
            chan_df = pd.DataFrame([
                {"Channel": "Email Address Available", "Profiles": email_cnt, "Pct": email_pct},
                {"Channel": "Phone Number Available", "Profiles": phone_cnt, "Pct": phone_pct},
                {"Channel": "Postal Address Available", "Profiles": addr_cnt, "Pct": addr_pct},
                {"Channel": "Both Email & Phone", "Profiles": match_both, "Pct": (match_both/total_fans*100)}
            ])
            st.dataframe(
                chan_df.style.format({'Profiles': '{:,}', 'Pct': '{:.1f}%'}),
                use_container_width=True,
                hide_index=True
            )
            
        with c_ch2:
            if 'phone1type' in gcp_df.columns:
                p_type = gcp_df['phone1type'].dropna().value_counts().reset_index()
                p_type.columns = ['Phone Type', 'Count']
                st.markdown("**Phone Type Distribution**")
                st.dataframe(p_type.style.format({'Count': '{:,}'}), use_container_width=True, hide_index=True)

    # Tab 4: Profile Creation Timeline
    with demo_tab4:
        st.markdown("##### Profile Acquisition / Creation Growth Over Time")
        if 'createdon' in gcp_df.columns:
            gcp_df['created_dt'] = pd.to_datetime(gcp_df['createdon'], errors='coerce')
            valid_dt = gcp_df.dropna(subset=['created_dt']).copy()
            
            if not valid_dt.empty:
                valid_dt['year_month'] = valid_dt['created_dt'].dt.to_period('M').astype(str)
                monthly_growth = valid_dt.groupby('year_month')['personid'].nunique().reset_index()
                monthly_growth.columns = ['Year-Month', 'New Profiles']
                monthly_growth = monthly_growth.sort_values('Year-Month')
                
                if _HAVE_ALTAIR and not monthly_growth.empty:
                    trend_chart = alt.Chart(monthly_growth).mark_line(point=True, color='#0284C7').encode(
                        x=alt.X('Year-Month:N', title="Month"),
                        y=alt.Y('New Profiles:Q', title="Profiles Added"),
                        tooltip=['Year-Month:N', alt.Tooltip('New Profiles:Q', format=',')]
                    ).properties(height=320)
                    st.altair_chart(trend_chart, use_container_width=True)
                else:
                    st.dataframe(monthly_growth, use_container_width=True)


# Page 2: EZLinks Golf Analytics Proof of Concept (POC)
def show_ezlinks_poc_page(session):
    _banner(
        "⛳ EZLinks Golf Analytics Proof of Concept",
        "Deep dive tee sheet metrics, rounds played, golfer frequency, time frame filters, and TPC property selections."
    )
    
    with st.spinner("Loading EZLinks tee sheet and golfer summary datasets..."):
        rounds_df = load_ezlinks_rounds_data(session)
        summary_df = load_ezlinks_summary_data(session, rounds_df)

    if rounds_df.empty:
        st.error("Unable to load EZLinks rounds dataset.")
        return

    # Normalize columns
    rounds_df = _lower_cols(rounds_df)
    summary_df = _lower_cols(summary_df)

    # Convert date/time columns
    rounds_df['slotdatetime'] = pd.to_datetime(rounds_df['slotdatetime'], errors='coerce')
    rounds_df['teesheetdate'] = pd.to_datetime(rounds_df['teesheetdate'], errors='coerce')

    # Identify TPC Facilities
    all_clubs = sorted(rounds_df['club_name'].dropna().unique())
    tpc_clubs = [c for c in all_clubs if re.search(r'\btpc\b', c, re.IGNORECASE)]

    # Filters Container
    with st.sidebar:
        st.markdown("### 🎛️ EZLinks Dynamic Filters")
        
        # TPC Quick Toggle
        tpc_only = st.checkbox("🎯 TPC Properties Only", value=False, help="Filter exclusively to TPC Network facilities")
        
        if tpc_only:
            club_options = tpc_clubs
        else:
            club_options = all_clubs
            
        selected_clubs = st.multiselect(
            "Select Club(s) / Facility",
            options=club_options,
            default=[],
            help="Leave empty to select all clubs"
        )
        
        # Course Options based on selected clubs
        if selected_clubs:
            available_courses = sorted(rounds_df[rounds_df['club_name'].isin(selected_clubs)]['course_name'].dropna().unique())
        elif tpc_only:
            available_courses = sorted(rounds_df[rounds_df['club_name'].isin(tpc_clubs)]['course_name'].dropna().unique())
        else:
            available_courses = sorted(rounds_df['course_name'].dropna().unique())
            
        selected_courses = st.multiselect(
            "Select Specific Course(s)",
            options=available_courses,
            default=[],
            help="Filter to specific golf courses"
        )
        
        # Time Frame Presets
        time_frame = st.selectbox(
            "Time Frame Preset",
            ["All Time", "Last 30 Days", "Last 60 Days", "Last 90 Days", "Year-to-Date (YTD)", "Custom Date Range"]
        )
        
        max_dt = rounds_df['slotdatetime'].max() if not rounds_df['slotdatetime'].isna().all() else pd.Timestamp.now()
        
        custom_start, custom_end = None, None
        if time_frame == "Custom Date Range":
            min_dt = rounds_df['slotdatetime'].min() if not rounds_df['slotdatetime'].isna().all() else pd.Timestamp(2024, 1, 1)
            date_range = st.date_input("Select Custom Date Range", value=(min_dt.date(), max_dt.date()))
            if isinstance(date_range, tuple) and len(date_range) == 2:
                custom_start, custom_end = date_range[0], date_range[1]

        # Fee / Membership Filters
        if 'membership_type_name' in rounds_df.columns:
            mem_types = sorted(rounds_df['membership_type_name'].dropna().unique())
            selected_mems = st.multiselect("Membership Category", options=mem_types, default=[])
        else:
            selected_mems = []

    # Apply Dynamic Filters to Rounds DataFrame
    filtered_rounds = rounds_df.copy()
    
    if tpc_only:
        filtered_rounds = filtered_rounds[filtered_rounds['club_name'].isin(tpc_clubs)]
        
    if selected_clubs:
        filtered_rounds = filtered_rounds[filtered_rounds['club_name'].isin(selected_clubs)]
        
    if selected_courses:
        filtered_rounds = filtered_rounds[filtered_rounds['course_name'].isin(selected_courses)]
        
    if selected_mems and 'membership_type_name' in filtered_rounds.columns:
        filtered_rounds = filtered_rounds[filtered_rounds['membership_type_name'].isin(selected_mems)]

    # Filter by Time Frame
    if time_frame == "Last 30 Days":
        filtered_rounds = filtered_rounds[filtered_rounds['slotdatetime'] >= (max_dt - timedelta(days=30))]
    elif time_frame == "Last 60 Days":
        filtered_rounds = filtered_rounds[filtered_rounds['slotdatetime'] >= (max_dt - timedelta(days=60))]
    elif time_frame == "Last 90 Days":
        filtered_rounds = filtered_rounds[filtered_rounds['slotdatetime'] >= (max_dt - timedelta(days=90))]
    elif time_frame == "Year-to-Date (YTD)":
        start_of_year = pd.Timestamp(max_dt.year, 1, 1)
        filtered_rounds = filtered_rounds[filtered_rounds['slotdatetime'] >= start_of_year]
    elif time_frame == "Custom Date Range" and custom_start and custom_end:
        filtered_rounds = filtered_rounds[
            (filtered_rounds['slotdatetime'].dt.date >= custom_start) &
            (filtered_rounds['slotdatetime'].dt.date <= custom_end)
        ]

    # Handle Empty Filter Result
    if filtered_rounds.empty:
        st.warning("⚠️ No rounds data matches the current filter criteria. Please adjust your selections in the sidebar.")
        return

    # Calculate Top Level Key Metrics
    tot_golfers = filtered_rounds['contactid'].nunique()
    tot_rounds = filtered_rounds['slotdatetime'].nunique() if 'slotdatetime' in filtered_rounds.columns else len(filtered_rounds)
    tot_clubs_played = filtered_rounds['club_name'].nunique()
    tot_courses_played = filtered_rounds['course_name'].nunique()
    avg_rounds_per_golfer = (tot_rounds / tot_golfers) if tot_golfers > 0 else 0
    tot_revenue = filtered_rounds['fee_amount'].sum() if 'fee_amount' in filtered_rounds.columns else 0.0

    # Display KPI Metrics Cards Row
    st.subheader("📌 Filtered Dynamic Key Performance Indicators")
    m1, m2, m3, m4, m5 = st.columns(5)
    
    with m1:
        st.metric("Total Unique Golfers", f"{tot_golfers:,}")
    with m2:
        st.metric("Total Rounds Played", f"{tot_rounds:,}")
    with m3:
        st.metric("Avg Rounds / Golfer", f"{avg_rounds_per_golfer:.1f}")
    with m4:
        st.metric("Clubs / Courses Active", f"{tot_clubs_played:,} / {tot_courses_played:,}")
    with m5:
        st.metric("Total Fee Revenue ($)", f"${tot_revenue:,.2f}")

    st.markdown("---")

    # Sub-Tabs for Deep Analytics
    tab_poc1, tab_poc2, tab_poc3, tab_poc4 = st.tabs([
        "📊 Club & Course Performance",
        "📈 Rounds Over Time & Seasonality",
        "🏌️ Golfer Segments & Behavior",
        "📋 Golfer Leaderboard & Directory"
    ])

    # Sub-Tab 1: Club & Course Performance
    with tab_poc1:
        st.markdown("##### Top Facilities and Courses")
        c_club1, c_club2 = st.columns(2)
        
        with c_club1:
            club_perf = filtered_rounds.groupby('club_name').agg(
                Rounds=('slotdatetime', 'nunique'),
                Golfers=('contactid', 'nunique'),
                Revenue=('fee_amount', 'sum') if 'fee_amount' in filtered_rounds.columns else ('contactid', 'count')
            ).reset_index().sort_values('Rounds', ascending=False)
            
            st.markdown("**Top Facilities by Rounds Played**")
            if _HAVE_ALTAIR and not club_perf.empty:
                club_chart = alt.Chart(club_perf.head(10)).mark_bar(color='#15803D', cornerRadiusEnd=4).encode(
                    x=alt.X('Rounds:Q', title="Rounds Played"),
                    y=alt.Y('club_name:N', sort='-x', title=None),
                    tooltip=['club_name:N', alt.Tooltip('Rounds:Q', format=','), alt.Tooltip('Revenue:Q', format='$,.2f')]
                ).properties(height=320)
                st.altair_chart(club_chart, use_container_width=True)
            else:
                st.dataframe(club_perf.head(10), use_container_width=True)

        with c_club2:
            course_perf = filtered_rounds.groupby(['club_name', 'course_name']).agg(
                Rounds=('slotdatetime', 'nunique'),
                Golfers=('contactid', 'nunique')
            ).reset_index().sort_values('Rounds', ascending=False)
            
            st.markdown("**Top Courses Breakdown**")
            st.dataframe(
                course_perf.head(10).style.format({'Rounds': '{:,}', 'Golfers': '{:,}'}),
                use_container_width=True,
                height=320,
                hide_index=True
            )

        # Fee Types & Reservation Sources
        st.markdown("##### Fee Types & Tee Time Reservation Sources")
        c_src1, c_src2 = st.columns(2)
        
        with c_src1:
            if 'tee_time_reservation_source' in filtered_rounds.columns:
                res_src = filtered_rounds['tee_time_reservation_source'].value_counts().reset_index()
                res_src.columns = ['Reservation Source', 'Bookings']
                st.dataframe(res_src.style.format({'Bookings': '{:,}'}), use_container_width=True, hide_index=True)
                
        with c_src2:
            if 'fee_type' in filtered_rounds.columns:
                fee_src = filtered_rounds['fee_type'].value_counts().reset_index()
                fee_src.columns = ['Fee Type', 'Rounds']
                st.dataframe(fee_src.style.format({'Rounds': '{:,}'}), use_container_width=True, hide_index=True)

    # Sub-Tab 2: Rounds Over Time & Seasonality
    with tab_poc2:
        st.markdown("##### Time Series Trend & Day-of-Week Distribution")
        
        # Monthly / Weekly Trend
        filtered_rounds['year_month'] = filtered_rounds['slotdatetime'].dt.to_period('M').astype(str)
        trend_df = filtered_rounds.groupby('year_month')['slotdatetime'].nunique().reset_index()
        trend_df.columns = ['Year-Month', 'Rounds Played']
        trend_df = trend_df.sort_values('Year-Month')
        
        if _HAVE_ALTAIR and not trend_df.empty:
            rounds_trend_chart = alt.Chart(trend_df).mark_line(point=True, color='#047857', strokeWidth=3).encode(
                x=alt.X('Year-Month:N', title="Month"),
                y=alt.Y('Rounds Played:Q', title="Rounds Played"),
                tooltip=['Year-Month:N', alt.Tooltip('Rounds Played:Q', format=',')]
            ).properties(title="Monthly Rounds Trend", height=320)
            st.altair_chart(rounds_trend_chart, use_container_width=True)
        else:
            st.dataframe(trend_df, use_container_width=True)

        c_time1, c_time2 = st.columns(2)
        
        with c_time1:
            # Day of Week
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            filtered_rounds['day_of_week'] = filtered_rounds['slotdatetime'].dt.day_name()
            dow_df = filtered_rounds['day_of_week'].value_counts().reindex(days_order).fillna(0).reset_index()
            dow_df.columns = ['Day of Week', 'Rounds']
            
            if _HAVE_ALTAIR:
                dow_chart = alt.Chart(dow_df).mark_bar(color='#16A34A', cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                    x=alt.X('Day of Week:N', sort=days_order, title="Day"),
                    y=alt.Y('Rounds:Q', title="Rounds Played"),
                    tooltip=['Day of Week:N', alt.Tooltip('Rounds:Q', format=',')]
                ).properties(title="Rounds by Day of Week", height=280)
                st.altair_chart(dow_chart, use_container_width=True)

        with c_time2:
            # Hour of Day
            filtered_rounds['hour'] = filtered_rounds['slotdatetime'].dt.hour
            hour_df = filtered_rounds['hour'].value_counts().sort_index().reset_index()
            hour_df.columns = ['Hour of Day (24h)', 'Rounds']
            
            if _HAVE_ALTAIR and not hour_df.empty:
                hour_chart = alt.Chart(hour_df).mark_bar(color='#65A30D', cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                    x=alt.X('Hour of Day (24h):Q', title="Hour of Day"),
                    y=alt.Y('Rounds:Q', title="Rounds Played"),
                    tooltip=['Hour of Day (24h):Q', alt.Tooltip('Rounds:Q', format=',')]
                ).properties(title="Tee Time Hour Distribution", height=280)
                st.altair_chart(hour_chart, use_container_width=True)

    # Sub-Tab 3: Golfer Segments & Behavior
    with tab_poc3:
        st.markdown("##### Golfer Playing Frequency & Category Segments")
        
        golfer_rounds = filtered_rounds.groupby('contactid')['slotdatetime'].nunique().reset_index()
        golfer_rounds.columns = ['contactid', 'rounds_count']
        
        bins = [0, 1, 5, 10, 1000]
        labels = ['Casual (1 round)', 'Active (2-5 rounds)', 'Frequent (6-10 rounds)', 'Heavy (11+ rounds)']
        freq_seg = pd.cut(golfer_rounds['rounds_count'], bins=bins, labels=labels).value_counts().reindex(labels).reset_index()
        freq_seg.columns = ['Segment', 'Golfer Count']
        
        c_seg1, c_seg2 = st.columns(2)
        
        with c_seg1:
            st.markdown("**Golfer Frequency Segmentation**")
            if _HAVE_ALTAIR:
                seg_chart = alt.Chart(freq_seg).mark_bar(color='#0D9488', cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                    x=alt.X('Segment:N', sort=labels, title="Frequency Segment"),
                    y=alt.Y('Golfer Count:Q', title="Golfers"),
                    tooltip=['Segment:N', alt.Tooltip('Golfer Count:Q', format=',')]
                ).properties(height=300)
                st.altair_chart(seg_chart, use_container_width=True)

        with c_seg2:
            st.markdown("**Membership Category Breakdown**")
            if 'membership_type_name' in filtered_rounds.columns:
                mem_seg = filtered_rounds['membership_type_name'].value_counts().reset_index()
                mem_seg.columns = ['Membership Category', 'Rounds Played']
                st.dataframe(mem_seg.style.format({'Rounds Played': '{:,}'}), use_container_width=True, hide_index=True)

        # Walk vs Ride & Group Size
        st.markdown("##### Group Size & Walk vs Ride Ratio")
        c_att1, c_att2 = st.columns(2)
        
        with c_att1:
            if 'total_players_on_reservation' in filtered_rounds.columns:
                grp_df = filtered_rounds['total_players_on_reservation'].value_counts().sort_index().reset_index()
                grp_df.columns = ['Players on Reservation', 'Reservations']
                st.dataframe(grp_df.style.format({'Reservations': '{:,}'}), use_container_width=True, hide_index=True)
                
        with c_att2:
            if 'walk_vs_ride' in filtered_rounds.columns:
                wr_df = filtered_rounds['walk_vs_ride'].value_counts().reset_index()
                wr_df.columns = ['Walk vs Ride', 'Rounds']
                st.dataframe(wr_df.style.format({'Rounds': '{:,}'}), use_container_width=True, hide_index=True)

    # Sub-Tab 4: Golfer Directory & Leaderboard
    with tab_poc4:
        st.markdown("##### Golfer Leaderboard & Detailed Contact Directory")
        
        leaderboard = filtered_rounds.groupby('contactid').agg(
            Golden_Person_ID=('personid', 'first'),
            First_Name=('contact_first_name', 'first'),
            Last_Name=('last_name', 'first'),
            Email=('email_address', 'first'),
            Total_Rounds=('slotdatetime', 'nunique'),
            Favorite_Club=('club_name', lambda x: x.mode()[0] if not x.empty else ''),
            Total_Spend=('fee_amount', 'sum') if 'fee_amount' in filtered_rounds.columns else ('contactid', 'count'),
            Last_Play_Date=('slotdatetime', 'max')
        ).reset_index().sort_values('Total_Rounds', ascending=False)
        
        leaderboard['Last_Play_Date'] = leaderboard['Last_Play_Date'].dt.strftime('%Y-%m-%d')
        
        # Search Box
        search_query = st.text_input("🔍 Search Golfer by Name, Email, or Person ID", "")
        
        if search_query:
            sq = search_query.lower()
            leaderboard = leaderboard[
                leaderboard['First_Name'].astype(str).str.lower().str.contains(sq) |
                leaderboard['Last_Name'].astype(str).str.lower().str.contains(sq) |
                leaderboard['Email'].astype(str).str.lower().str.contains(sq) |
                leaderboard['Golden_Person_ID'].astype(str).str.lower().str.contains(sq)
            ]
            
        st.dataframe(
            leaderboard.head(100).style.format({
                'Total_Rounds': '{:,}',
                'Total_Spend': '${:,.2f}'
            }),
            use_container_width=True,
            height=400,
            hide_index=True
        )
        
        # CSV Download Button
        csv_data = leaderboard.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Filtered Golfer Directory as CSV",
            data=csv_data,
            file_name=f"ezlinks_golfer_directory_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )


# Page 3: Data Model & Architecture Documentation
def show_documentation_page():
    _banner(
        "ℹ️ Data Model & Source Documentation",
        "Technical architecture, dbt model mappings, join logic, and GCP Golden Record integration."
    )
    
    st.markdown("""
    ### 🏗️ Architecture & Model Overview
    
    The Golf Course Properties (GCP) Golden Record consolidates fan profiles, club memberships, guest stays, and tee sheet activity across multiple 1st party source systems into a unified fan profile keyed on `PERSONID`.
    
    #### Key DBT Models Used in This Application:
    
    1. **`GCP_GOLDEN_FAN_MASTER`** (`analytics.gcp_golden.gcp_golden_fan_master`)
       - **Grain**: One row per deduplicated fan / email.
       - **Sources**: Maps `gcp_golden_record.fan` and `lookups.us_zip_code_to_dma`.
       - **Key Fields**: `personid`, `firstname`, `lastname`, `type`, `email`, `phone1`, `city`, `state`, `zip`, `dma_name`, `age`, `createdon`, `sources`.
       
    2. **`EZLINKS_SUMMARY`** (`analytics.ezlinks.ezlinks_summary`)
       - **Grain**: One row per `contactid` (unique EZLinks golfer).
       - **Description**: Summarizes overall customer activity, total rounds played, 30/60/90-day activity, favorite club and course, and mapped `personid`.
       
    3. **`EZLINKS_ROUNDS_SUMMARY`** (`analytics.ezlinks.ezlinks_rounds_summary`)
       - **Grain**: One row per round / tee time reservation per individual.
       - **Description**: Combines clean tee sheet reservations (`ezlinks_tee_sheet_final_clean`), customer profiles (`ezlinks_customers`), reservation group size, fees, and `personid` from `gcp_golden_record.fansource`.
       
    4. **`FIRST_PARTY_HEALTH_SUMMARY`** (`analytics.golden.first_party_health_summary`)
       - **Grain**: One row per source system per snapshot date.
       - **Description**: Tracks historical and current record counts across all 1st party integrations.
       
    ---
    
    #### 🔌 Source Systems Contributing to GCP Golden Record:
    
    - ⛳ **EZLinks**: Tee sheet reservations, course bookings, golfer contacts
    - 🏛️ **Jonas Club Datamart**: Private club memberships, chit transactions, member statuses
    - 🏨 **Inntopia**: Resort itinerary stays, lodging reservations, guest contact info
    - ⛳ **TPC Network & TPC Passport**: Salesforce CRM contacts, leads, and passport reservations
    - 📝 **Formstack**: Tournament event registrations and digital forms
    - 🔐 **Gigya**: Single Sign-On (SSO) registered accounts
    - 🎟️ **Archtics**: Event ticket purchases and tournament attendance
    """)


# Main Application Entry Point
def main():
    session = init_session()
    
    # Sidebar Setup
    st.sidebar.title("⛳ GCP Golden Record")
    st.sidebar.markdown("**Golf Course Properties Insights**")
    
    page = st.sidebar.radio(
        "Navigate",
        [
            "🏠 Home: Golden Record Overview",
            "⛳ EZLinks Golf Analytics (POC)",
            "ℹ️ Data Model Documentation"
        ],
        index=0
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔌 Session Status")
    if session:
        st.sidebar.success("Connected to Snowflake")
    else:
        st.sidebar.info("Running in Standalone / Offline Mode")
        
    st.sidebar.caption(f"📅 App Version 1.0.0 | Updated: {date.today().strftime('%B %d, %Y')}")
    
    # Route Pages
    if page == "🏠 Home: Golden Record Overview":
        show_home_page(session)
    elif page == "⛳ EZLinks Golf Analytics (POC)":
        show_ezlinks_poc_page(session)
    elif page == "ℹ️ Data Model Documentation":
        show_documentation_page()


if __name__ == "__main__":
    main()
