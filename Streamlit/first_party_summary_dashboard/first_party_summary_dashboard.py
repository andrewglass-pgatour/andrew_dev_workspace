"""
Marketing Data Insights Dashboard
Streamlit app for viewing 1st party data health and campaign performance
Uses Snowflake's native session context (no secrets needed)
"""

import streamlit as st
from snowflake.snowpark import Session
import pandas as pd
from datetime import date, timedelta

try:
    import altair as alt  # type: ignore

    _HAVE_ALTAIR = True
except Exception:
    alt = None  # type: ignore
    _HAVE_ALTAIR = False

try:
    import pydeck as pdk  # type: ignore

    _HAVE_PYDECK = True
except Exception:
    pdk = None  # type: ignore
    _HAVE_PYDECK = False

# Fixed data sources. These are not user-editable: the app runs with its owner's
# privileges, so viewers must not be able to point queries at arbitrary tables.
WIT_RELATION = "ANALYTICS.PROD_WIT.WIT_ACTIVATIONS_SUMMARY"
SAFARI_RELATION = "ANALYTICS.PROD_SAFARI.MOPS_SAFARI_SUMMARY"
ACUITY_RELATION = "ANALYTICS.PROD_GOLDEN.UNIFIED_FAN_PROFILE_SOURCE_DISTRIBUTION"

# Page configuration
st.set_page_config(
    page_title="Marketing Data Insights",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Snowflake session
@st.cache_resource
def init_session():
    """Initialize Snowflake session using current user's session context"""
    try:
        # Container Runtime: the Snowflake connection is provided via st.connection
        return st.connection("snowflake").session()
    except Exception:
        pass
    try:
        # In Snowflake Streamlit, we can use getOrCreate() which uses the current user's session
        # No credentials needed - uses the current user's Snowflake session
        session = Session.builder.getOrCreate()
        return session
    except Exception as e:
        # Fallback: try creating with minimal config
        try:
            return Session.builder.create()
        except Exception as e2:
            st.error(f"Error connecting to Snowflake: {str(e2)}")
            return None

# Cache data queries
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_campaign_data(_session):
    """Get campaign performance data from DBT model
    Note: _session has leading underscore so Streamlit doesn't try to hash it
    """
    query = """
    SELECT 
        a.campaign,
        l.campaign_month_year,
        a.total_entries,
        a.unique_entries,
        a.net_new_golden_record_users,
        a.golden_record_net_new_rate_pct,
        a.email_opt_ins,
        a.net_new_email_subscribers,
        a.resubscribers_previous_optout,
        a.previously_subscribed,
        a.subscription_net_gain_pct
    FROM ANALYTICS.PROD_CUSTOM_IDENTITY.CUSTOM_IDENTITY_CAMPAIGN_ANALYSIS a
    LEFT JOIN PGAT.LOOKUP.CUSTOM_IDENTITY_CAMPAIGNS l
        ON a.campaign = l.campaign_name
    WHERE a.campaign <> 'DAZN Customers'  -- intentionally hidden from this dashboard
    ORDER BY a.total_entries DESC
    """
    return _session.sql(query).to_pandas()

def show_custom_identity_campaigns():
    """Display custom identity campaign metrics and visualizations"""
    st.header("🎯 Custom Identity Campaigns")
    
    session = st.session_state.get('session')
    if not session:
        session = init_session()
        if not session:
            st.error("Unable to connect to Snowflake. Please check your connection.")
            return
        st.session_state['session'] = session
    
    # Get data
    try:
        df = get_campaign_data(session)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return
    
    if df.empty:
        st.warning("No campaign data available.")
        return
    
    # Convert column names to lowercase for consistency (Snowflake may return uppercase)
    df.columns = df.columns.str.lower()

    # Campaign month/year (e.g. "June 2025") -> real date for sorting
    df['campaign_date'] = pd.to_datetime(df['campaign_month_year'], format='%B %Y', errors='coerce')

    # Check if required columns exist
    required_cols = ['campaign', 'total_entries', 'golden_record_net_new_rate_pct',
                     'email_opt_ins', 'subscription_net_gain_pct']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        st.error(f"Missing required columns: {', '.join(missing_cols)}")
        st.write("**Available columns:**", list(df.columns))
        return
    
    # Key Metrics Row
    st.subheader("Key Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Campaigns", df['campaign'].nunique())
    with col2:
        st.metric("Total Entries", f"{df['total_entries'].sum():,}")
    with col3:
        avg_rate = df['golden_record_net_new_rate_pct'].mean()
        st.metric("Avg Net New Rate", f"{avg_rate:.1f}%")
    with col4:
        st.metric("Total Opt-Ins", f"{df['email_opt_ins'].sum():,}")
    with col5:
        avg_gain = df['subscription_net_gain_pct'].mean()
        st.metric("Avg Subscription Gain", f"{avg_gain:.1f}%")
    
    # Filters
    st.subheader("Filters")
    campaign_options = sorted(df['campaign'].unique())
    
    select_all = st.checkbox("Select All Campaigns", value=True)
    
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        if select_all:
            st.multiselect(
                f"Filter Specific Campaigns (All {len(campaign_options)} selected)",
                options=campaign_options,
                default=[],
                disabled=True,
                help="Uncheck 'Select All Campaigns' above to select specific campaigns."
            )
            selected_campaigns = campaign_options
        else:
            selected_campaigns = st.multiselect(
                "Filter Specific Campaigns",
                options=campaign_options,
                default=[],
                help="Select one or more campaigns to filter."
            )
    
    with filter_col2:
        min_entries = st.number_input(
            "Minimum Entries",
            min_value=0,
            value=0,
            step=100
        )
    
    with filter_col3:
        sort_option = st.selectbox(
            "Sort By",
            ["Campaign Date (Newest First)", "Total Entries", "Net New Rate", "Subscription Net Gain", "Opt-Ins"]
        )

    # Filter and sort data (no selection => empty, not "all rows")
    filtered_df = df[
        df['campaign'].isin(selected_campaigns)
        & (df['total_entries'] >= min_entries)
    ].copy()

    if sort_option == "Campaign Date (Newest First)":
        filtered_df = filtered_df.sort_values(
            ['campaign_date', 'total_entries'], ascending=[False, False], na_position='last'
        )
    elif sort_option == "Total Entries":
        filtered_df = filtered_df.sort_values('total_entries', ascending=False)
    elif sort_option == "Net New Rate":
        filtered_df = filtered_df.sort_values('golden_record_net_new_rate_pct', ascending=False)
    elif sort_option == "Subscription Net Gain":
        filtered_df = filtered_df.sort_values('subscription_net_gain_pct', ascending=False)
    else:
        filtered_df = filtered_df.sort_values('email_opt_ins', ascending=False)
    
    if filtered_df.empty:
        if not selected_campaigns:
            st.info("Select one or more campaigns to view performance details in the tables and charts below.")
        else:
            st.info(
                "No campaigns match the current filters. Try lowering **Minimum Entries** or changing your selection."
            )
        st.caption(f"📅 Data last refreshed: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview Table", "📈 Visualizations", "🎯 Metrics Comparison", "📋 Detailed View"])
    
    with tab1:
        st.subheader("Campaign Performance Summary")
        display_cols = [
            'campaign', 'campaign_month_year', 'total_entries', 'unique_entries',
            'net_new_golden_record_users', 'golden_record_net_new_rate_pct',
            'email_opt_ins', 'net_new_email_subscribers',
            'resubscribers_previous_optout', 'subscription_net_gain_pct'
        ]
        
        display_df = filtered_df[display_cols].copy()
        
        st.dataframe(
            display_df.style.format({
                'total_entries': '{:,.0f}',
                'unique_entries': '{:,.0f}',
                'net_new_golden_record_users': '{:,.0f}',
                'golden_record_net_new_rate_pct': '{:.2f}%',
                'email_opt_ins': '{:,.0f}',
                'net_new_email_subscribers': '{:,.0f}',
                'resubscribers_previous_optout': '{:,.0f}',
                'subscription_net_gain_pct': '{:.2f}%'
            }),
            height=500,
            use_container_width=True,
        )
    
    with tab2:
        st.subheader("Performance Visualizations")
        
        # Net New Rate Chart
        st.subheader("Golden Record Net New Rate (Top 15)")
        top_15_rate = filtered_df.head(15).sort_values('golden_record_net_new_rate_pct', ascending=True)
        chart_data = top_15_rate.set_index('campaign')['golden_record_net_new_rate_pct']
        st.bar_chart(chart_data, height=400)
        
        # Subscription Performance
        st.subheader("Subscription Metrics Comparison")
        sub_col1, sub_col2 = st.columns(2)
        
        with sub_col1:
            st.write("**Net New Subscribers (Top 10)**")
            top_10_sub = filtered_df.head(10).set_index('campaign')['net_new_email_subscribers']
            st.bar_chart(top_10_sub, height=300)
        
        with sub_col2:
            st.write("**Re-Subscribers (Top 10)**")
            top_10_resub = filtered_df.head(10).set_index('campaign')['resubscribers_previous_optout']
            st.bar_chart(top_10_resub, height=300)
        
        # Subscription Net Gain
        st.subheader("Subscription Net Gain % (Top 15)")
        top_15_gain = filtered_df.head(15).sort_values('subscription_net_gain_pct', ascending=True)
        gain_chart = top_15_gain.set_index('campaign')['subscription_net_gain_pct']
        st.bar_chart(gain_chart, height=400)
        
        # Scatter-like view using metrics
        st.subheader("Campaign Performance Matrix")
        st.write("**Top 10 Campaigns by Total Entries vs Net New Rate**")
        matrix_df = filtered_df.head(10)[['campaign', 'total_entries', 'golden_record_net_new_rate_pct', 'subscription_net_gain_pct']].copy()
        matrix_df['entries_scaled'] = (matrix_df['total_entries'] / matrix_df['total_entries'].max() * 100).round(1)
        st.dataframe(
            matrix_df.style.format({
                'total_entries': '{:,.0f}',
                'golden_record_net_new_rate_pct': '{:.2f}%',
                'subscription_net_gain_pct': '{:.2f}%',
                'entries_scaled': '{:.1f}'
            }),
            use_container_width=True,
        )
    
    with tab3:
        st.subheader("Metrics Comparison")
        
        # Create comparison dataframe
        comparison_cols = ['campaign', 'total_entries', 'net_new_golden_record_users', 
                          'email_opt_ins', 'net_new_email_subscribers', 
                          'resubscribers_previous_optout']
        comparison_df = filtered_df[comparison_cols].head(10).copy()
        
        # Normalize for comparison (0-100 scale)
        for col in ['total_entries', 'net_new_golden_record_users', 'email_opt_ins', 
                   'net_new_email_subscribers', 'resubscribers_previous_optout']:
            max_val = comparison_df[col].max()
            if max_val > 0:
                comparison_df[f'{col}_normalized'] = (comparison_df[col] / max_val * 100).round(1)
        
        st.write("**Normalized Metrics Comparison (0-100 scale)**")
        normalized_cols = [col for col in comparison_df.columns if 'normalized' in col]
        normalized_df = comparison_df[['campaign'] + normalized_cols].copy()
        normalized_df.columns = [col.replace('_normalized', '') for col in normalized_df.columns]
        
        # Create a multi-metric chart
        chart_data = normalized_df.set_index('campaign')
        st.line_chart(chart_data, height=400)
        
        # Side-by-side comparison
        st.subheader("Raw Metrics Comparison")
        st.dataframe(
            comparison_df[comparison_cols].style.format({
                'total_entries': '{:,.0f}',
                'net_new_golden_record_users': '{:,.0f}',
                'email_opt_ins': '{:,.0f}',
                'net_new_email_subscribers': '{:,.0f}',
                'resubscribers_previous_optout': '{:,.0f}'
            }),
            use_container_width=True,
        )
    
    with tab4:
        st.subheader("Complete Campaign Details")
        
        # Full table with all columns
        st.dataframe(
            filtered_df.style.format({
                'total_entries': '{:,.0f}',
                'unique_entries': '{:,.0f}',
                'net_new_golden_record_users': '{:,.0f}',
                'golden_record_net_new_rate_pct': '{:.2f}%',
                'email_opt_ins': '{:,.0f}',
                'net_new_email_subscribers': '{:,.0f}',
                'resubscribers_previous_optout': '{:,.0f}',
                'previously_subscribed': '{:,.0f}',
                'subscription_net_gain_pct': '{:.2f}%'
            }),
            height=600,
            use_container_width=True,
        )
        
        # Export functionality
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"campaign_performance_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
        # Summary statistics
        st.subheader("Summary Statistics")
        summary_cols = ['total_entries', 'net_new_golden_record_users', 
                       'golden_record_net_new_rate_pct', 'email_opt_ins',
                       'net_new_email_subscribers', 'subscription_net_gain_pct']
        summary_stats = filtered_df[summary_cols].describe()
        st.dataframe(summary_stats.style.format('{:.2f}'), use_container_width=True)
    
    # Data freshness indicator
    st.caption(f"📅 Data last refreshed: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_first_party_health_data(_session):
    """Get first party health summary data"""
    query = """
    SELECT *
    FROM ANALYTICS.PROD_GOLDEN.FIRST_PARTY_HEALTH_SUMMARY
    ORDER BY source_date DESC
    """
    return _session.sql(query).to_pandas()

def show_data_health():
    """Display 1st party data health metrics"""
    st.header("💚 1st Party Data Health")
    
    session = st.session_state.get('session')
    if not session:
        session = init_session()
        if not session:
            st.error("Unable to connect to Snowflake.")
            return
        st.session_state['session'] = session
    
    # Get first party health data
    try:
        health_df = get_first_party_health_data(session)
        
        if health_df.empty:
            st.warning("No first party health data available.")
            return
        
        # Normalize column names to lowercase
        health_df.columns = health_df.columns.str.lower()

        # Remove Amplitude - Registered Users from this dashboard.
        # We match robustly across underscore/dash/space variants.
        if "source" in health_df.columns:
            src_raw = health_df["source"].astype(str)
            src_norm = (
                src_raw.str.strip()
                .str.lower()
                .str.replace("_", " ", regex=False)
                .str.replace(r"\s+", " ", regex=True)
            )

            exclude_exact = {
                "amplitude registered users",
                "amplitude - registered users",
            }
            exclude_pattern = (
                src_norm.str.contains(r"\bamplitude\b", regex=True)
                & src_norm.str.contains(r"\bregistered\b", regex=True)
                & src_norm.str.contains(r"\busers?\b", regex=True)
            )
            health_df = health_df.loc[~(src_norm.isin(exclude_exact) | exclude_pattern)].copy()
        
        # Ensure source_date column exists and convert to datetime
        if 'source_date' not in health_df.columns:
            st.error("source_date column not found in first_party_health_summary. Available columns: " + ", ".join(health_df.columns))
            return
        
        health_df['source_date'] = pd.to_datetime(health_df['source_date'])
        
        # Check for required columns
        if 'source' not in health_df.columns or 'record_count' not in health_df.columns:
            st.error(f"Required columns not found. Available columns: {', '.join(health_df.columns)}")
            return
        
        # Summary table by source (latest snapshot per source)
        st.subheader("📊 Current Status by Source")
        
        # Get the latest date for each source (sources may be updated on different dates)
        latest_by_source = health_df.groupby('source')['source_date'].max().reset_index()
        latest_by_source.columns = ['source', 'latest_date']
        
        # Get the record count for each source at its latest date
        summary_data = []
        for _, row in latest_by_source.iterrows():
            source = row['source']
            latest_date = row['latest_date']
            source_data = health_df[
                (health_df['source'] == source) & 
                (health_df['source_date'] == latest_date)
            ]
            if not source_data.empty:
                count = source_data['record_count'].iloc[0]
                summary_data.append({
                    'Source': source.replace('_', ' ').title(),
                    'Golden Record Members': int(count) if not pd.isna(count) else 0,
                    'Last Updated': latest_date.strftime('%Y-%m-%d')
                })
        
        if summary_data:
            summary_df = (
                pd.DataFrame(summary_data)
                .sort_values('Golden Record Members', ascending=False)
                .reset_index(drop=True)
            )
            st.dataframe(
                summary_df.style.format({'Golden Record Members': '{:,}'}),
                height=400,
                use_container_width=True,
            )
        else:
            st.warning("No source data available.")
        
        # Monthly snapshots for past year
        st.subheader("📅 Monthly Snapshots (Past 12 Months)")
        
        # Filter to past year
        one_year_ago = pd.Timestamp.now() - pd.DateOffset(years=1)
        past_year_df = health_df[health_df['source_date'] >= one_year_ago].copy()
        
        if not past_year_df.empty:
            # Get end of month dates for each month
            past_year_df['year_month'] = past_year_df['source_date'].dt.to_period('M')
            
            # Get all unique sources
            all_sources = sorted(health_df['source'].unique())
            
            # Create monthly summary - get latest date for each source within each month
            monthly_data = []
            for month_period in sorted(past_year_df['year_month'].unique()):
                month_data = {
                    'Month': str(month_period),
                    'Date': ''
                }
                
                # Get the latest date in this month (for display)
                month_dates = past_year_df[past_year_df['year_month'] == month_period]['source_date']
                if not month_dates.empty:
                    month_end_date = month_dates.max()
                    month_data['Date'] = month_end_date.strftime('%Y-%m-%d')
                
                # For each source, get the latest available date within this month
                for source in all_sources:
                    source_month_df = past_year_df[
                        (past_year_df['year_month'] == month_period) & 
                        (past_year_df['source'] == source)
                    ]
                    
                    if not source_month_df.empty:
                        # Get the latest date for this source in this month
                        latest_source_date = source_month_df['source_date'].max()
                        source_data = source_month_df[source_month_df['source_date'] == latest_source_date]
                        if not source_data.empty:
                            source_count = source_data['record_count'].iloc[0]
                            month_data[source.replace('_', ' ').title()] = int(source_count) if not pd.isna(source_count) else 0
                        else:
                            month_data[source.replace('_', ' ').title()] = 0
                    else:
                        month_data[source.replace('_', ' ').title()] = 0
                
                monthly_data.append(month_data)
            
            if monthly_data:
                monthly_df = pd.DataFrame(monthly_data)
                # Format numeric columns
                numeric_cols = [col for col in monthly_df.columns if col not in ['Month', 'Date']]
                st.dataframe(
                    monthly_df.style.format({col: '{:,}' for col in numeric_cols}),
                    height=500,
                    use_container_width=True,
                )
            else:
                st.info("No monthly snapshot data available.")
        else:
            st.info("No data available for the past year.")
        
        st.subheader("📈 Golden Record Growth Trends")
        
        if not health_df.empty:
            hc = health_df.copy()
            hc["record_count"] = pd.to_numeric(hc["record_count"], errors="coerce")
            hc = hc.dropna(subset=["source_date", "record_count"])

            if "source" not in hc.columns:
                st.info("No `source` column found in first_party_health_summary; cannot chart growth by source.")
                return

            hc["source_norm"] = hc["source"].astype(str).str.strip().str.lower()
            src_norms = sorted([s for s in hc["source_norm"].dropna().unique() if str(s).strip() != ""])
            if not src_norms:
                st.info("No sources available to chart.")
                return

            def _fmt_source(s: str) -> str:
                return str(s).replace("_", " ").strip().title()

            preferred_default = next(
                (
                    s
                    for s in [
                        "golden_record_total",
                        "mops_golden_fan_master",
                        "golden_fan_master",
                        "fan_master",
                        "golden_record",
                    ]
                    if s in src_norms
                ),
                src_norms[0],
            )

            selected_src = st.selectbox(
                "Source",
                options=src_norms,
                index=src_norms.index(preferred_default) if preferred_default in src_norms else 0,
                format_func=_fmt_source,
                help="Select the source series you want to trend over time.",
            )

            series_df = (
                hc.loc[hc["source_norm"] == selected_src, ["source_date", "record_count"]]
                .groupby("source_date", as_index=False)["record_count"]
                .max()
                .rename(columns={"source_date": "date", "record_count": "count"})
                .sort_values("date")
                .drop_duplicates(subset=["date"], keep="last")
            )

            if series_df.empty:
                st.info("No rows for the selected source.")
                return

            # Interactive chart (same style as Subscriber Information)
            if _HAVE_ALTAIR:
                chart_df = series_df.copy()
                chart_df["count"] = pd.to_numeric(chart_df["count"], errors="coerce")
                chart_df = chart_df.dropna(subset=["date", "count"]).sort_values("date")
                if chart_df.empty:
                    st.info("No chartable values for the selected source.")
                    return

                y_min = float(chart_df["count"].min())
                y_max = float(chart_df["count"].max())
                pad = max((y_max - y_min) * 0.06, 1.0)
                y_domain = [max(0.0, y_min - pad), y_max + pad]

                base = alt.Chart(chart_df).encode(
                    x=alt.X("date:T", title=None),
                    y=alt.Y("count:Q", title="Members", scale=alt.Scale(domain=y_domain, nice=False)),
                )

                if hasattr(alt, "selection_point"):
                    nearest = alt.selection_point(  # type: ignore[attr-defined]
                        nearest=True,
                        on="mouseover",
                        fields=["date"],
                        empty=False,
                    )
                    _attach = "params"
                else:
                    nearest = alt.selection_single(  # type: ignore[attr-defined]
                        nearest=True,
                        on="mouseover",
                        fields=["date"],
                        empty="none",
                    )
                    _attach = "selection"

                area = base.mark_area(opacity=0.12, color="#E53935")
                line = base.mark_line(interpolate="monotone", strokeWidth=2.8, color="#E53935")

                points = base.mark_point(size=80).encode(
                    opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
                    color=alt.value("#E53935"),
                )
                if _attach == "params":
                    points = points.add_params(nearest)  # type: ignore[union-attr]
                else:
                    points = points.add_selection(nearest)  # type: ignore[union-attr]

                rule = (
                    alt.Chart(chart_df)
                    .mark_rule(color="rgba(255,255,255,0.35)")
                    .encode(
                        x="date:T",
                        tooltip=[
                            alt.Tooltip("date:T", title="Date"),
                            alt.Tooltip("count:Q", title=_fmt_source(selected_src), format=",.0f"),
                        ],
                    )
                    .transform_filter(nearest)
                )

                growth_chart = (
                    alt.layer(area, line, points, rule)
                    .properties(height=420, title=f"{_fmt_source(selected_src)} growth trend")
                    .configure_view(strokeOpacity=0)
                ).interactive()

                st.altair_chart(growth_chart, use_container_width=True)
            else:
                fallback = series_df.copy()
                fallback = fallback.set_index("date")[["count"]]
                fallback.columns = [_fmt_source(selected_src)]
                st.line_chart(fallback, height=400)

            # YoY Growth metrics for selected source
            daily_totals = series_df.rename(columns={"date": "Date", "count": "Total Users"}).set_index("Date")
            
            # YoY Growth metrics (replace all-time + last-change metrics)
            if len(daily_totals) > 0:
                latest_chart_total = int(daily_totals["Total Users"].iloc[-1])
                daily_totals = daily_totals.sort_index()
                latest_date = daily_totals.index.max()
                cutoff = latest_date - pd.DateOffset(years=1)
                # Use nearest available date to avoid sparse/irregular snapshot schedules
                try:
                    prior_pos = daily_totals.index.get_indexer([cutoff], method="nearest")[0]
                    prior_total = int(daily_totals["Total Users"].iloc[int(prior_pos)])
                except Exception:
                    prior_total = None

                yoy_total: int | None
                yoy_rate: float | None
                if prior_total is not None:
                    yoy_total = latest_chart_total - int(prior_total)
                    yoy_rate = (yoy_total / int(prior_total) * 100) if int(prior_total) > 0 else None
                else:
                    yoy_total = None
                    yoy_rate = None

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("YoY Growth Total", f"{yoy_total:,}" if yoy_total is not None else "N/A")
                with col2:
                    st.metric("YoY Growth Rate", f"{yoy_rate:.2f}%" if yoy_rate is not None else "N/A")
        else:
            st.info("No growth data available.")
            
    except Exception as e:
        st.error(f"Error loading first party health data: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
    
    # Golden Record summary (keep existing)
    try:
        query = """
        SELECT 
            COUNT(DISTINCT personid) as total_fans,
            COUNT(DISTINCT email1) as total_emails,
            COUNT(DISTINCT phone1) as total_phones,
            COUNT(DISTINCT CASE WHEN email1 IS NOT NULL THEN personid END) as fans_with_email,
            COUNT(DISTINCT CASE WHEN phone1 IS NOT NULL THEN personid END) as fans_with_phone
        FROM ANALYTICS.PROD_GOLDEN.MOPS_GOLDEN_FAN_MASTER
        """
        df = session.sql(query).to_pandas()
        
        if not df.empty:
            # Normalize column names to lowercase (Snowflake may return uppercase)
            df.columns = df.columns.str.lower()
            
            st.subheader("Golden Record Overview")
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("Total Fans", f"{df['total_fans'].iloc[0]:,}")
            with col2:
                st.metric("Total Emails", f"{df['total_emails'].iloc[0]:,}")
            with col3:
                st.metric("Total Phones", f"{df['total_phones'].iloc[0]:,}")
            with col4:
                email_pct = (df['fans_with_email'].iloc[0] / df['total_fans'].iloc[0] * 100) if df['total_fans'].iloc[0] > 0 else 0
                st.metric("Fans with Email", f"{email_pct:.1f}%")
            with col5:
                phone_pct = (df['fans_with_phone'].iloc[0] / df['total_fans'].iloc[0] * 100) if df['total_fans'].iloc[0] > 0 else 0
                st.metric("Fans with Phone", f"{phone_pct:.1f}%")
    except Exception as e:
        st.warning(f"Could not load Golden Record data: {str(e)}")
    
    # Country breakdown
    try:
        country_query = """
        SELECT 
            country,
            COUNT(DISTINCT personid) as fan_count
        FROM PGAT.GOLDEN.FAN
        WHERE country IS NOT NULL
          AND country != ''
        GROUP BY country
        ORDER BY fan_count DESC
        LIMIT 50
        """
        country_df = session.sql(country_query).to_pandas()
        
        if not country_df.empty:
            # Normalize column names to lowercase
            country_df.columns = country_df.columns.str.lower()
            
            st.subheader("🌍 Country Distribution (Top 50)")

            st.write("**Country Breakdown Table**")
            display_country_df = country_df.copy()
            display_country_df.columns = ["Country", "Fan Count"]
            st.dataframe(
                display_country_df.style.format({"Fan Count": "{:,}"}),
                height=600,
                use_container_width=True,
            )
            
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                total_fans = country_df['fan_count'].sum()
                st.metric("Total Fans (Top 50)", f"{total_fans:,}")
            with col2:
                top_country = country_df.iloc[0]
                st.metric("Top Country", f"{top_country['country']}")
            with col3:
                top_country_pct = (top_country['fan_count'] / total_fans * 100) if total_fans > 0 else 0
                st.metric("Top Country %", f"{top_country_pct:.1f}%")
    except Exception as e:
        st.warning(f"Could not load country data: {str(e)}")


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_wit_activations_summary_data(_session, relation: str) -> pd.DataFrame:
    """Get Wit activation summary data from dbt model"""
    return _session.sql(f"select * from {relation}").to_pandas()


def show_wit_data():
    """Display Wit activation summary information"""
    st.header("✨ Wit Data")
    st.markdown("### Activation-level entries, opt-ins, and participation summary")

    session = st.session_state.get("session")
    if not session:
        session = init_session()
        if not session:
            st.error("Unable to connect to Snowflake.")
            return
        st.session_state["session"] = session

    relation = WIT_RELATION

    try:
        wit_df = get_wit_activations_summary_data(session, relation)
    except Exception as e:
        st.error(f"Could not load `{relation}`: {str(e)}")
        return

    if wit_df.empty:
        st.warning("No Wit activation summary data available.")
        return

    wit_df.columns = wit_df.columns.str.lower()

    # Basic validation / best-effort rendering
    for c in ["start_at", "end_at", "first_entry_at", "last_entry_at"]:
        if c in wit_df.columns:
            wit_df[c] = pd.to_datetime(wit_df[c], errors="coerce")

    st.subheader("Key metrics")
    total_activations = int(wit_df["activation_id"].nunique()) if "activation_id" in wit_df.columns else 0
    total_entries = int(pd.to_numeric(wit_df.get("total_entries", 0), errors="coerce").fillna(0).sum())
    total_unique = int(
        pd.to_numeric(wit_df.get("total_unique_emails_normalized", 0), errors="coerce").fillna(0).sum()
    )
    opt_in_entries = int(
        pd.to_numeric(wit_df.get("total_email_opt_in_entries", 0), errors="coerce").fillna(0).sum()
    )
    opt_in_rate = (opt_in_entries / total_entries * 100) if total_entries > 0 else None

    season_start = pd.Timestamp("2026-01-01")
    season_end = pd.Timestamp("2026-12-31")
    unique_2026 = None
    if "first_entry_date" in wit_df.columns or "last_entry_date" in wit_df.columns:
        tmp = wit_df.copy()
        if "first_entry_date" in tmp.columns:
            tmp["first_entry_date"] = pd.to_datetime(tmp["first_entry_date"], errors="coerce")
        if "last_entry_date" in tmp.columns:
            tmp["last_entry_date"] = pd.to_datetime(tmp["last_entry_date"], errors="coerce")
        mask_2026 = True
        if "first_entry_date" in tmp.columns:
            mask_2026 = mask_2026 & (tmp["first_entry_date"] <= season_end)
        if "last_entry_date" in tmp.columns:
            mask_2026 = mask_2026 & (tmp["last_entry_date"] >= season_start)
        tmp_2026 = tmp.loc[mask_2026].copy()
        unique_2026 = int(
            pd.to_numeric(tmp_2026.get("total_unique_emails_normalized", 0), errors="coerce").fillna(0).sum()
        )

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("Activations", f"{total_activations:,}")
    with k2:
        st.metric("Total Entries", f"{total_entries:,}")
    with k3:
        st.metric("Unique Emails (normalized)", f"{total_unique:,}")
    with k4:
        st.metric("Email Opt-In Rate (entries)", f"{opt_in_rate:.2f}%" if opt_in_rate is not None else "N/A")
    with k5:
        st.metric(
            "Unique Entries During 2026 Season",
            f"{unique_2026:,}" if unique_2026 is not None else "N/A",
        )

    st.subheader("Activation summary table")
    active_only = st.checkbox("Show active activations only", value=False)
    df_view = wit_df.copy()
    if active_only and "is_active" in df_view.columns:
        df_view = df_view[df_view["is_active"] == True]  # noqa: E712

    sponsor_options = sorted([s for s in df_view.get("sponsor_name", pd.Series([])).dropna().astype(str).unique()])
    selected_sponsors = st.multiselect("Sponsor", options=sponsor_options, default=[])
    if selected_sponsors and "sponsor_name" in df_view.columns:
        df_view = df_view[df_view["sponsor_name"].astype(str).isin(selected_sponsors)]

    show_cols = [
        c
        for c in [
            "activation_code",
            "clean_activation_name",
            "sponsor_name",
            "activation_type",
            "subtype",
            "start_at",
            "end_at",
            "is_active",
            "total_entries",
            "total_unique_emails_normalized",
            "total_email_opt_in_entries",
            "total_email_opt_out_entries",
            "first_entry_at",
            "last_entry_at",
            "public_url",
        ]
        if c in df_view.columns
    ]
    sort_col = "start_at" if "start_at" in df_view.columns else (show_cols[0] if show_cols else df_view.columns[0])
    ascending = False if sort_col == "start_at" else True
    st.dataframe(
        df_view[show_cols].sort_values(sort_col, ascending=ascending, na_position="last"),
        height=650,
        use_container_width=True,
    )

    st.download_button(
        "Download CSV",
        data=df_view.to_csv(index=False),
        file_name=f"wit_activations_summary_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.caption(f"Source: `{relation}`")


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_safari_wifi_season_years(_session, relation: str) -> pd.DataFrame:
    """Return distinct season years available in Safari WiFi relation."""
    query = f"""
    select distinct season_year
    from {relation}
    where season_year is not null
    order by season_year desc
    """
    return _session.sql(query).to_pandas()


def _safari_wifi_where_clause(
    season_years: tuple[int, ...] | None,
    start_date: date | None,
    end_date: date | None,
) -> str:
    clauses: list[str] = ["email is not null"]
    if season_years:
        years_csv = ", ".join(str(int(y)) for y in season_years)
        clauses.append(f"season_year in ({years_csv})")
    if start_date is not None:
        clauses.append(f"event_date >= '{start_date.isoformat()}'")
    if end_date is not None:
        clauses.append(f"event_date <= '{end_date.isoformat()}'")
    return " where " + " and ".join(clauses)


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_safari_wifi_kpis(
    _session,
    relation: str,
    season_years: tuple[int, ...] | None,
    start_date: date | None,
    end_date: date | None,
) -> pd.DataFrame:
    """Get Safari WiFi KPI rollups for the given relation and filters."""
    where = _safari_wifi_where_clause(season_years, start_date, end_date)
    query = f"""
    select
        count(*) as total_wifi_events,
        count(distinct email) as unique_emails,
        count(distinct personid) as unique_personids,
        count(distinct tournament_id) as unique_tournaments,
        min(event_date) as first_event_date,
        max(event_date) as last_event_date
    from {relation}
    {where}
    """
    return _session.sql(query).to_pandas()


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_safari_wifi_tournament_breakdown(
    _session,
    relation: str,
    season_years: tuple[int, ...] | None,
    start_date: date | None,
    end_date: date | None,
) -> pd.DataFrame:
    """Get tournament-level breakdown for Safari WiFi usage."""
    where = _safari_wifi_where_clause(season_years, start_date, end_date)
    query = f"""
    select
        tournament_id,
        tournament,
        season_year,
        calendar_year,
        count(*) as total_wifi_events,
        count(distinct email) as unique_emails,
        count(distinct personid) as unique_personids,
        min(event_date) as first_event_date,
        max(event_date) as last_event_date
    from {relation}
    {where}
    group by all
    order by total_wifi_events desc
    """
    return _session.sql(query).to_pandas()


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_safari_wifi_daily_trend(
    _session,
    relation: str,
    season_years: tuple[int, ...] | None,
    start_date: date | None,
    end_date: date | None,
) -> pd.DataFrame:
    """Get daily event counts for Safari WiFi usage."""
    where = _safari_wifi_where_clause(season_years, start_date, end_date)
    query = f"""
    select
        event_date,
        count(*) as total_wifi_events,
        count(distinct email) as unique_emails,
        count(distinct personid) as unique_personids
    from {relation}
    {where}
    group by event_date
    order by event_date asc
    """
    return _session.sql(query).to_pandas()


def show_safari_wifi_data():
    """Display Safari tournament WiFi usage rollups."""
    st.header("📶 Safari WiFi Data")
    st.markdown("### Unique users, tournament breakdown, and usage trends")

    session = st.session_state.get("session")
    if not session:
        session = init_session()
        if not session:
            st.error("Unable to connect to Snowflake.")
            return
        st.session_state["session"] = session

    relation = SAFARI_RELATION

    # Filters
    season_years: tuple[int, ...] | None = None
    try:
        years_df = get_safari_wifi_season_years(session, relation)
        years_df.columns = years_df.columns.str.lower()
        available_years = (
            pd.to_numeric(years_df.get("season_year", pd.Series([])), errors="coerce")
            .dropna()
            .astype(int)
            .tolist()
        )
        default_years = available_years[:1] if available_years else []
        selected_years = st.sidebar.multiselect(
            "Season year",
            options=available_years,
            default=default_years,
        )
        season_years = tuple(int(y) for y in selected_years) if selected_years else None
    except Exception:
        st.sidebar.caption("Could not load available season years; showing all years.")

    filter_by_date = st.sidebar.checkbox("Filter by event date range", value=False)
    start_date: date | None = None
    end_date: date | None = None
    if filter_by_date:
        default_end = pd.Timestamp.now().date()
        default_start = (pd.Timestamp.now() - pd.Timedelta(days=30)).date()
        picked = st.sidebar.date_input(
            "Event date range",
            value=(default_start, default_end),
        )
        if isinstance(picked, tuple) and len(picked) == 2:
            start_date, end_date = picked
        else:
            start_date = picked

    # Fetch data
    try:
        kpi_df = get_safari_wifi_kpis(session, relation, season_years, start_date, end_date)
        breakdown_df = get_safari_wifi_tournament_breakdown(
            session, relation, season_years, start_date, end_date
        )
        trend_df = get_safari_wifi_daily_trend(session, relation, season_years, start_date, end_date)
    except Exception as e:
        st.error(f"Could not load `{relation}`: {str(e)}")
        return

    if kpi_df.empty:
        st.warning("No Safari WiFi data available for the selected filters.")
        st.caption(f"Source: `{relation}`")
        return

    kpi_df.columns = kpi_df.columns.str.lower()
    breakdown_df.columns = breakdown_df.columns.str.lower() if not breakdown_df.empty else breakdown_df.columns
    trend_df.columns = trend_df.columns.str.lower() if not trend_df.empty else trend_df.columns

    # KPIs
    st.subheader("Key metrics")
    total_events = int(pd.to_numeric(kpi_df.get("total_wifi_events", 0), errors="coerce").fillna(0).iloc[0])
    unique_emails = int(pd.to_numeric(kpi_df.get("unique_emails", 0), errors="coerce").fillna(0).iloc[0])
    unique_personids = int(
        pd.to_numeric(kpi_df.get("unique_personids", 0), errors="coerce").fillna(0).iloc[0]
    )
    unique_tournaments = int(
        pd.to_numeric(kpi_df.get("unique_tournaments", 0), errors="coerce").fillna(0).iloc[0]
    )
    first_date = kpi_df.get("first_event_date", pd.Series([None])).iloc[0]
    last_date = kpi_df.get("last_event_date", pd.Series([None])).iloc[0]

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Unique emails", f"{unique_emails:,}")
    with c2:
        st.metric("Unique users (personid)", f"{unique_personids:,}")
    with c3:
        st.metric("Total WiFi events", f"{total_events:,}")
    with c4:
        st.metric("Tournaments", f"{unique_tournaments:,}")
    with c5:
        date_range = "N/A"
        if pd.notna(first_date) and pd.notna(last_date):
            date_range = f"{pd.to_datetime(first_date).date()} → {pd.to_datetime(last_date).date()}"
        st.metric("Date range", date_range)

    # Tournament breakdown
    st.subheader("Tournament breakdown")
    if breakdown_df.empty:
        st.info("No tournament breakdown rows for the selected filters.")
    else:
        top_n = st.slider("Top tournaments to display", min_value=5, max_value=50, value=15, step=5)
        sort_metric = st.selectbox(
            "Sort by",
            options=["unique_personids", "unique_emails", "total_wifi_events"],
            index=0,
        )
        bdf = breakdown_df.copy()
        for c in ["unique_personids", "unique_emails", "total_wifi_events"]:
            if c in bdf.columns:
                bdf[c] = pd.to_numeric(bdf[c], errors="coerce").fillna(0).astype(int)
        bdf = bdf.sort_values(sort_metric, ascending=False, na_position="last").head(top_n)

        chart_df = bdf[["tournament", sort_metric]].copy() if "tournament" in bdf.columns else None
        if chart_df is not None and not chart_df.empty:
            if _HAVE_ALTAIR and alt is not None:
                chart = (
                    alt.Chart(chart_df)
                    .mark_bar()
                    .encode(
                        y=alt.Y("tournament:N", sort="-x", title="Tournament"),
                        x=alt.X(f"{sort_metric}:Q", title=sort_metric.replace("_", " ").title()),
                        tooltip=["tournament", sort_metric],
                    )
                    .properties(height=420)
                )
                st.altair_chart(chart, use_container_width=True)
            else:
                st.bar_chart(chart_df.set_index("tournament")[sort_metric])

        show_cols = [
            c
            for c in [
                "tournament",
                "tournament_id",
                "season_year",
                "calendar_year",
                "unique_personids",
                "unique_emails",
                "total_wifi_events",
                "first_event_date",
                "last_event_date",
            ]
            if c in breakdown_df.columns
        ]
        st.dataframe(
            breakdown_df[show_cols].sort_values("total_wifi_events", ascending=False, na_position="last"),
            height=550,
            use_container_width=True,
        )

        st.download_button(
            "Download tournament breakdown CSV",
            data=breakdown_df.to_csv(index=False),
            file_name=f"safari_wifi_tournament_breakdown_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # Trend
    st.subheader("Daily trend")
    if trend_df.empty or "event_date" not in trend_df.columns:
        st.info("No daily trend data available for the selected filters.")
    else:
        tdf = trend_df.copy()
        tdf["event_date"] = pd.to_datetime(tdf["event_date"], errors="coerce")
        for c in ["total_wifi_events", "unique_emails", "unique_personids"]:
            if c in tdf.columns:
                tdf[c] = pd.to_numeric(tdf[c], errors="coerce").fillna(0)
        tdf = tdf.sort_values("event_date")
        metric = st.selectbox(
            "Trend metric",
            options=["total_wifi_events", "unique_emails", "unique_personids"],
            index=0,
        )
        st.line_chart(tdf.set_index("event_date")[metric])

    st.caption(f"Source: `{relation}`")


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_fanatics_summary_data(_session):
    """Get Fanatics summary metrics"""
    query = """
    SELECT 
        COUNT(DISTINCT personid) as total_fans_with_purchases,
        COUNT(DISTINCT CASE WHEN total_orders > 0 THEN personid END) as fans_with_orders,
        SUM(total_orders) as total_orders,
        AVG(total_orders) as avg_orders_per_fan,
        SUM(total_spend) as total_spend,
        AVG(total_spend) as avg_spend_per_fan,
        COUNT(DISTINCT CASE WHEN total_orders > 1 THEN personid END) as repeat_purchasers,
        MAX(total_spend) as max_customer_spend,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_spend) as median_spend_per_fan
    FROM ANALYTICS.FANATICS.FANATICS_SUMMARY
    WHERE personid IS NOT NULL
    """
    try:
        return _session.sql(query).to_pandas()
    except Exception as e:
        # Try alternative schema pattern
        try:
            query_alt = query.replace('ANALYTICS.FANATICS.FANATICS_SUMMARY', 'ANALYTICS.PROD_FANATICS.FANATICS_SUMMARY')
            return _session.sql(query_alt).to_pandas()
        except Exception as e2:
            raise e

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_fanatics_detailed_data(_session):
    """Get detailed Fanatics purchase data for additional analysis"""
    query = """
    SELECT 
        COUNT(DISTINCT order_id) as total_unique_orders,
        COUNT(DISTINCT personid) as unique_customers,
        SUM(order_total) as total_revenue,
        AVG(order_total) as avg_order_value,
        MIN(order_date) as first_order_date,
        MAX(order_date) as last_order_date,
        COUNT(DISTINCT CASE WHEN is_repeat_purchaser = 'Yes' THEN personid END) as repeat_purchaser_count,
        SUM(quantity_sold) as total_items_sold,
        COUNT(DISTINCT product_name) as unique_products
    FROM ANALYTICS.FANATICS.FANATICS_PURCHASE_SUMMARY
    WHERE personid IS NOT NULL
    """
    try:
        return _session.sql(query).to_pandas()
    except Exception as e:
        # Try alternative schema pattern
        try:
            query_alt = query.replace('ANALYTICS.FANATICS.FANATICS_PURCHASE_SUMMARY', 'ANALYTICS.PROD_FANATICS.FANATICS_PURCHASE_SUMMARY')
            return _session.sql(query_alt).to_pandas()
        except Exception as e2:
            raise e

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_fanatics_yearly_data(_session):
    """Get yearly Fanatics purchase metrics"""
    query = """
    SELECT 
        YEAR(order_date) as purchase_year,
        COUNT(DISTINCT personid) as unique_customers,
        COUNT(DISTINCT order_id) as total_orders,
        SUM(order_total) as total_revenue,
        AVG(order_total) as avg_order_value,
        SUM(quantity_sold) as total_items_sold,
        COUNT(DISTINCT product_name) as unique_products,
        COUNT(DISTINCT CASE WHEN is_repeat_purchaser = 'Yes' THEN personid END) as repeat_purchaser_count
    FROM ANALYTICS.FANATICS.FANATICS_PURCHASE_SUMMARY
    WHERE personid IS NOT NULL AND order_date IS NOT NULL
    GROUP BY 1
    ORDER BY purchase_year DESC
    """
    try:
        return _session.sql(query).to_pandas()
    except Exception as e:
        # Try alternative schema pattern
        try:
            query_alt = query.replace('ANALYTICS.FANATICS.FANATICS_PURCHASE_SUMMARY', 'ANALYTICS.PROD_FANATICS.FANATICS_PURCHASE_SUMMARY')
            return _session.sql(query_alt).to_pandas()
        except Exception as e2:
            raise e

def show_fanatics_data():
    """Display Fanatics purchase data and metrics"""
    st.header("🛒 Fanatics Purchase Data")
    st.markdown("### Fan Shop Purchase Analytics & Metrics")
    
    session = st.session_state.get('session')
    if not session:
        session = init_session()
        if not session:
            st.error("Unable to connect to Snowflake. Please check your connection.")
            return
        st.session_state['session'] = session
    
    # Get summary data
    try:
        summary_df = get_fanatics_summary_data(session)
        detailed_df = get_fanatics_detailed_data(session)
        yearly_df = get_fanatics_yearly_data(session)
    except Exception as e:
        st.error(f"Error loading Fanatics data: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return
    
    if summary_df.empty or detailed_df.empty:
        st.warning("No Fanatics data available.")
        return
    
    # Normalize column names to lowercase
    summary_df.columns = summary_df.columns.str.lower()
    detailed_df.columns = detailed_df.columns.str.lower()
    if not yearly_df.empty:
        yearly_df.columns = yearly_df.columns.str.lower()
    
    # We can use tabs to separate Total and Yearly breakdowns
    tab_total, tab_yearly = st.tabs(["📊 Total Metrics", "📅 Yearly Breakdowns"])
    
    with tab_total:
        # Key Metrics Row
        st.subheader("📊 Key Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_fans = int(summary_df['total_fans_with_purchases'].iloc[0]) if 'total_fans_with_purchases' in summary_df.columns else 0
            st.metric("Total Fans with Purchases", f"{total_fans:,}")
        
        with col2:
            total_spend = float(summary_df['total_spend'].iloc[0]) if 'total_spend' in summary_df.columns else 0
            st.metric("Total Revenue", f"${total_spend:,.2f}")
        
        with col3:
            avg_spend = float(summary_df['avg_spend_per_fan'].iloc[0]) if 'avg_spend_per_fan' in summary_df.columns else 0
            st.metric("Avg Spend per Fan", f"${avg_spend:,.2f}")
        
        with col4:
            avg_orders = float(summary_df['avg_orders_per_fan'].iloc[0]) if 'avg_orders_per_fan' in summary_df.columns else 0
            st.metric("Avg Orders per Fan", f"{avg_orders:.2f}")
        
        # Additional metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_orders = int(summary_df['total_orders'].iloc[0]) if 'total_orders' in summary_df.columns else 0
            st.metric("Total Orders", f"{total_orders:,}")
        
        with col2:
            repeat_purchasers = int(summary_df['repeat_purchasers'].iloc[0]) if 'repeat_purchasers' in summary_df.columns else 0
            repeat_pct = (repeat_purchasers / total_fans * 100) if total_fans > 0 else 0
            st.metric("Repeat Purchasers", f"{repeat_purchasers:,}", delta=f"{repeat_pct:.1f}%")
        
        with col3:
            median_spend = float(summary_df['median_spend_per_fan'].iloc[0]) if 'median_spend_per_fan' in summary_df.columns else 0
            st.metric("Median Spend per Fan", f"${median_spend:,.2f}")
        
        with col4:
            max_spend = float(summary_df['max_customer_spend'].iloc[0]) if 'max_customer_spend' in summary_df.columns else 0
            st.metric("Max Customer Spend", f"${max_spend:,.2f}")
        
        # Detailed metrics from purchase summary
        st.subheader("📈 Purchase Summary Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            unique_orders = int(detailed_df['total_unique_orders'].iloc[0]) if 'total_unique_orders' in detailed_df.columns else 0
            st.metric("Unique Orders", f"{unique_orders:,}")
        
        with col2:
            avg_order_value = float(detailed_df['avg_order_value'].iloc[0]) if 'avg_order_value' in detailed_df.columns else 0
            st.metric("Avg Order Value", f"${avg_order_value:,.2f}")
        
        with col3:
            total_items = int(detailed_df['total_items_sold'].iloc[0]) if 'total_items_sold' in detailed_df.columns else 0
            st.metric("Total Items Sold", f"{total_items:,}")
        
        with col4:
            unique_products = int(detailed_df['unique_products'].iloc[0]) if 'unique_products' in detailed_df.columns else 0
            st.metric("Unique Products", f"{unique_products:,}")
        
        # Summary Table
        st.subheader("📋 Summary Table")
        
        summary_data = {
            'Metric': [
                'Total Fans with Purchases',
                'Total Orders',
                'Average Orders per Fan',
                'Total Revenue ($)',
                'Average Spend per Fan ($)',
                'Median Spend per Fan ($)',
                'Max Customer Spend ($)',
                'Repeat Purchasers',
                'Repeat Purchaser %',
                'Total Unique Orders',
                'Average Order Value ($)',
                'Total Items Sold',
                'Unique Products'
            ],
            'Value': [
                total_fans,
                total_orders,
                f"{avg_orders:.2f}",
                f"${total_spend:,.2f}",
                f"${avg_spend:,.2f}",
                f"${median_spend:,.2f}",
                f"${max_spend:,.2f}",
                repeat_purchasers,
                f"{repeat_pct:.1f}%",
                unique_orders,
                f"${avg_order_value:,.2f}",
                total_items,
                unique_products
            ]
        }
        
        summary_table_df = pd.DataFrame(summary_data)
        st.dataframe(
            summary_table_df,
            use_container_width=True,
        )
        
        # Date range information
        if 'first_order_date' in detailed_df.columns and 'last_order_date' in detailed_df.columns:
            first_date = detailed_df['first_order_date'].iloc[0]
            last_date = detailed_df['last_order_date'].iloc[0]
            
            if pd.notna(first_date) and pd.notna(last_date):
                st.subheader("📅 Date Range")
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**First Order Date:** {pd.to_datetime(first_date).strftime('%Y-%m-%d') if pd.notna(first_date) else 'N/A'}")
                with col2:
                    st.info(f"**Last Order Date:** {pd.to_datetime(last_date).strftime('%Y-%m-%d') if pd.notna(last_date) else 'N/A'}")
        
        # Export functionality
        st.subheader("📥 Export Data")
        csv = summary_table_df.to_csv(index=False)
        st.download_button(
            label="Download Summary Metrics as CSV",
            data=csv,
            file_name=f"fanatics_summary_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
    with tab_yearly:
        if yearly_df.empty:
            st.warning("No yearly Fanatics data available.")
        else:
            st.subheader("📊 Key Metrics")
            
            # Selectbox to choose year
            years = sorted(list(yearly_df['purchase_year'].dropna().astype(int).unique()), reverse=True)
            selected_year = st.selectbox("Select Year", options=years, key="fanatics_selected_year")
            
            # Filter data for selected year
            year_data = yearly_df[yearly_df['purchase_year'] == selected_year].iloc[0]
            
            y_fans = int(year_data['unique_customers']) if 'unique_customers' in year_data else 0
            y_revenue = float(year_data['total_revenue']) if 'total_revenue' in year_data else 0.0
            y_orders = int(year_data['total_orders']) if 'total_orders' in year_data else 0
            y_items = int(year_data['total_items_sold']) if 'total_items_sold' in year_data else 0
            y_products = int(year_data['unique_products']) if 'unique_products' in year_data else 0
            y_repeat = int(year_data['repeat_purchaser_count']) if 'repeat_purchaser_count' in year_data else 0
            y_avg_order_val = float(year_data['avg_order_value']) if 'avg_order_value' in year_data else 0.0
            
            y_avg_spend = y_revenue / y_fans if y_fans > 0 else 0.0
            y_avg_orders = y_orders / y_fans if y_fans > 0 else 0.0
            y_repeat_pct = (y_repeat / y_fans * 100) if y_fans > 0 else 0.0
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Fans with Purchases", f"{y_fans:,}")
            with col2:
                st.metric("Total Revenue", f"${y_revenue:,.2f}")
            with col3:
                st.metric("Avg Spend per Fan", f"${y_avg_spend:,.2f}")
            with col4:
                st.metric("Avg Orders per Fan", f"{y_avg_orders:.2f}")
                
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Orders", f"{y_orders:,}")
            with col2:
                st.metric("Repeat Purchasers", f"{y_repeat:,}", delta=f"{y_repeat_pct:.1f}%")
            with col3:
                st.metric("Avg Order Value", f"${y_avg_order_val:,.2f}")
            with col4:
                st.metric("Total Items Sold", f"{y_items:,}")
            
            st.markdown("---")
            
            st.subheader("📅 Yearly Purchase Summary")
            
            # Format the yearly dataframe for nice display
            yearly_display = pd.DataFrame()
            yearly_display['Year'] = yearly_df['purchase_year'].astype(str)
            yearly_display['Total Revenue'] = yearly_df['total_revenue'].map('${:,.2f}'.format)
            yearly_display['Unique Customers (Fans)'] = yearly_df['unique_customers'].map('{:,}'.format)
            yearly_display['Total Orders'] = yearly_df['total_orders'].map('{:,}'.format)
            
            # Calculate derived metrics safely
            avg_spend = yearly_df['total_revenue'] / yearly_df['unique_customers']
            yearly_display['Avg Spend per Fan'] = avg_spend.map('${:,.2f}'.format)
            
            avg_orders = yearly_df['total_orders'] / yearly_df['unique_customers']
            yearly_display['Avg Orders per Fan'] = avg_orders.map('{:.2f}'.format)
            
            yearly_display['Avg Order Value'] = yearly_df['avg_order_value'].map('${:,.2f}'.format)
            
            yearly_display['Repeat Purchasers'] = yearly_df['repeat_purchaser_count'].map('{:,}'.format)
            repeat_pct = (yearly_df['repeat_purchaser_count'] / yearly_df['unique_customers'] * 100)
            yearly_display['Repeat Purchaser %'] = repeat_pct.map('{:.1f}%'.format)
            
            yearly_display['Total Items Sold'] = yearly_df['total_items_sold'].map('{:,}'.format)
            yearly_display['Unique Products'] = yearly_df['unique_products'].map('{:,}'.format)
            
            st.dataframe(yearly_display, use_container_width=True)
            
            # Display charts
            st.subheader("📈 Yearly Performance Trends")
            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.markdown("**Revenue by Year**")
                # Sort ascending for chronological chart
                chart_df = yearly_df.sort_values('purchase_year')
                st.bar_chart(chart_df.set_index('purchase_year')['total_revenue'])
            with chart_col2:
                st.markdown("**Unique Customers by Year**")
                st.bar_chart(chart_df.set_index('purchase_year')['unique_customers'])
                
            # Export yearly data
            st.subheader("📥 Export Yearly Data")
            yearly_csv = yearly_df.to_csv(index=False)
            st.download_button(
                label="Download Yearly Metrics as CSV",
                data=yearly_csv,
                file_name=f"fanatics_yearly_summary_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
    # Data freshness indicator
    st.caption(f"📅 Data last refreshed: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_current_subscriber_counts(_session):
    """Get current unique email counts by newsletter subscription"""
    query = """
    SELECT 
        COUNT(DISTINCT CASE WHEN LOWER(COALESCE(CAST(THE_EARLY_CARD_SUBSCRIBER AS VARCHAR), 'False')) = 'true' THEN email END) as starter_count,
        COUNT(DISTINCT CASE WHEN LOWER(COALESCE(CAST(PARTNER_OFFERS_SUBSCRIBER AS VARCHAR), 'False')) = 'true' THEN email END) as partner_offers_count,
        COUNT(DISTINCT CASE WHEN LOWER(COALESCE(CAST(VIP_VOLUNTEER_SUBSCRIBER AS VARCHAR), 'False')) = 'true' THEN email END) as vip_volunteer_count,
        COUNT(DISTINCT CASE WHEN LOWER(COALESCE(CAST(CHAMPIONS_MONTHLY_MINUTE_SUBSCRIBER AS VARCHAR), 'False')) = 'true' THEN email END) as champs_monthly_count,
        COUNT(DISTINCT CASE WHEN LOWER(COALESCE(CAST(WIRE_TO_WIRE_SUBSCRIBER AS VARCHAR), 'False')) = 'true' THEN email END) as wire_to_wire_count,
        COUNT(DISTINCT CASE WHEN LOWER(COALESCE(CAST(SIGNATURE_SCROLL_SUBSCRIBER AS VARCHAR), 'False')) = 'true' THEN email END) as signature_scroll_count,
        COUNT(DISTINCT CASE WHEN LOWER(COALESCE(CAST(TRUIST_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'False')) = 'true' THEN email END) as truist_championship_count,
        COUNT(DISTINCT CASE WHEN LOWER(COALESCE(CAST(PLAYERS_SUBSCRIBER AS VARCHAR), 'False')) = 'true' THEN email END) as players_count,
        COUNT(DISTINCT CASE WHEN LOWER(COALESCE(CAST(COGNIZANT_SUBSCRIBER AS VARCHAR), 'False')) = 'true' THEN email END) as cognizant_count,
        COUNT(DISTINCT CASE WHEN LOWER(COALESCE(CAST(BILTMORE_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'False')) = 'true' THEN email END) as biltmore_championship_count,
        COUNT(DISTINCT CASE WHEN LOWER(COALESCE(CAST(CADILLAC_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'False')) = 'true' THEN email END) as cadillac_championship_count,
        COUNT(DISTINCT CASE WHEN LOWER(COALESCE(CAST(SOMPO_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'False')) = 'true' THEN email END) as sompo_championship_count,
        COUNT(DISTINCT CASE WHEN
            LOWER(COALESCE(CAST(THE_EARLY_CARD_SUBSCRIBER AS VARCHAR), 'False')) = 'true' OR
            LOWER(COALESCE(CAST(PARTNER_OFFERS_SUBSCRIBER AS VARCHAR), 'False')) = 'true' OR
            LOWER(COALESCE(CAST(VIP_VOLUNTEER_SUBSCRIBER AS VARCHAR), 'False')) = 'true' OR
            LOWER(COALESCE(CAST(CHAMPIONS_MONTHLY_MINUTE_SUBSCRIBER AS VARCHAR), 'False')) = 'true' OR
            LOWER(COALESCE(CAST(WIRE_TO_WIRE_SUBSCRIBER AS VARCHAR), 'False')) = 'true' OR
            LOWER(COALESCE(CAST(SIGNATURE_SCROLL_SUBSCRIBER AS VARCHAR), 'False')) = 'true' OR
            LOWER(COALESCE(CAST(TRUIST_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'False')) = 'true' OR
            LOWER(COALESCE(CAST(PLAYERS_SUBSCRIBER AS VARCHAR), 'False')) = 'true' OR
            LOWER(COALESCE(CAST(COGNIZANT_SUBSCRIBER AS VARCHAR), 'False')) = 'true' OR
            LOWER(COALESCE(CAST(BILTMORE_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'False')) = 'true' OR
            LOWER(COALESCE(CAST(CADILLAC_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'False')) = 'true' OR
            LOWER(COALESCE(CAST(SOMPO_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'False')) = 'true'
        THEN email END) as total_deduped_subscribers
    FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY
    WHERE email IS NOT NULL
    """
    try:
        return _session.sql(query).to_pandas()
    except Exception as e:
        # Try alternative schema pattern
        try:
            query_alt = query.replace('ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY', 'ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY')
            return _session.sql(query_alt).to_pandas()
        except Exception as e2:
            raise e

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_monthly_subscriber_breakdown(_session):
    """Get monthly breakdown of subscriber counts over time"""
    query = """
    WITH date_spine AS (
        SELECT DATEADD(month, seq4(), DATE_TRUNC('month', DATEADD(year, -2, CURRENT_DATE()))) as month_end
        FROM TABLE(GENERATOR(ROWCOUNT => 24))
    ),
    subscriber_events AS (
        SELECT 
            email,
            'The Early Card (Starter)' as newsletter,
            THE_EARLY_CARD_SUBSCRIBER_DATE as subscribe_date,
            CAST(NULL AS DATE) as unsubscribe_date
        FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY
        WHERE email IS NOT NULL
            AND THE_EARLY_CARD_SUBSCRIBER_DATE IS NOT NULL
        
        UNION ALL
        
        SELECT 
            email,
            'Partner_Offers' as newsletter,
            PARTNER_OFFERS_SUBSCRIBER_DATE as subscribe_date,
            CAST(NULL AS DATE) as unsubscribe_date
        FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY
        WHERE email IS NOT NULL
            AND PARTNER_OFFERS_SUBSCRIBER_DATE IS NOT NULL
        
        UNION ALL
        
        SELECT 
            email,
            'VIP_Volunteer' as newsletter,
            VIP_VOLUNTEER_SUBSCRIBER_DATE as subscribe_date,
            CAST(NULL AS DATE) as unsubscribe_date
        FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY
        WHERE email IS NOT NULL
            AND VIP_VOLUNTEER_SUBSCRIBER_DATE IS NOT NULL
        
        UNION ALL
        
        SELECT 
            email,
            'Champs_Monthly' as newsletter,
            CHAMPIONS_MONTHLY_MINUTE_SUBSCRIBER_DATE as subscribe_date,
            CAST(NULL AS DATE) as unsubscribe_date
        FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY
        WHERE email IS NOT NULL
            AND CHAMPIONS_MONTHLY_MINUTE_SUBSCRIBER_DATE IS NOT NULL
        
        UNION ALL
        
        SELECT 
            email,
            'Wire_to_Wire' as newsletter,
            WIRE_TO_WIRE_SUBSCRIBER_DATE as subscribe_date,
            CAST(NULL AS DATE) as unsubscribe_date
        FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY
        WHERE email IS NOT NULL
            AND WIRE_TO_WIRE_SUBSCRIBER_DATE IS NOT NULL

        UNION ALL
        
        SELECT 
            email,
            'Signature_Scroll' as newsletter,
            SIGNATURE_SCROLL_SUBSCRIBER_DATE as subscribe_date,
            CAST(NULL AS DATE) as unsubscribe_date
        FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY
        WHERE email IS NOT NULL
            AND SIGNATURE_SCROLL_SUBSCRIBER_DATE IS NOT NULL

        UNION ALL
        
        SELECT 
            email,
            'Truist_Championship' as newsletter,
            TRUIST_CHAMPIONSHIP_SUBSCRIBER_DATE as subscribe_date,
            CAST(NULL AS DATE) as unsubscribe_date
        FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY
        WHERE email IS NOT NULL
            AND TRUIST_CHAMPIONSHIP_SUBSCRIBER_DATE IS NOT NULL

        UNION ALL
        
        SELECT 
            email,
            'Players' as newsletter,
            PLAYERS_SUBSCRIBER_DATE as subscribe_date,
            CAST(NULL AS DATE) as unsubscribe_date
        FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY
        WHERE email IS NOT NULL
            AND PLAYERS_SUBSCRIBER_DATE IS NOT NULL

        UNION ALL
        
        SELECT 
            email,
            'Cognizant' as newsletter,
            COGNIZANT_SUBSCRIBER_DATE as subscribe_date,
            CAST(NULL AS DATE) as unsubscribe_date
        FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY
        WHERE email IS NOT NULL
            AND COGNIZANT_SUBSCRIBER_DATE IS NOT NULL

        UNION ALL
        
        SELECT 
            email,
            'Biltmore_Championship' as newsletter,
            BILTMORE_CHAMPIONSHIP_SUBSCRIBER_DATE as subscribe_date,
            CAST(NULL AS DATE) as unsubscribe_date
        FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY
        WHERE email IS NOT NULL
            AND BILTMORE_CHAMPIONSHIP_SUBSCRIBER_DATE IS NOT NULL

        UNION ALL
        
        SELECT 
            email,
            'Cadillac_Championship' as newsletter,
            CADILLAC_CHAMPIONSHIP_SUBSCRIBER_DATE as subscribe_date,
            CAST(NULL AS DATE) as unsubscribe_date
        FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY
        WHERE email IS NOT NULL
            AND CADILLAC_CHAMPIONSHIP_SUBSCRIBER_DATE IS NOT NULL

        UNION ALL

        SELECT
            email,
            'Sompo_Championship' as newsletter,
            SOMPO_CHAMPIONSHIP_SUBSCRIBER_DATE as subscribe_date,
            CAST(NULL AS DATE) as unsubscribe_date
        FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY
        WHERE email IS NOT NULL
            AND SOMPO_CHAMPIONSHIP_SUBSCRIBER_DATE IS NOT NULL
    ),
    monthly_counts AS (
        SELECT 
            ds.month_end,
            se.newsletter,
            COUNT(DISTINCT se.email) as subscriber_count
        FROM date_spine ds
        CROSS JOIN (SELECT DISTINCT newsletter FROM subscriber_events) n
        LEFT JOIN subscriber_events se ON se.newsletter = n.newsletter
            AND DATE_TRUNC('month', se.subscribe_date) <= ds.month_end
            AND (se.unsubscribe_date IS NULL OR DATE_TRUNC('month', se.unsubscribe_date) > ds.month_end)
        GROUP BY ds.month_end, se.newsletter
    )
    SELECT 
        month_end as month,
        COALESCE(SUM(CASE WHEN newsletter = 'The Early Card (Starter)' THEN subscriber_count END), 0) as starter_count,
        COALESCE(SUM(CASE WHEN newsletter = 'Partner_Offers' THEN subscriber_count END), 0) as partner_offers_count,
        COALESCE(SUM(CASE WHEN newsletter = 'VIP_Volunteer' THEN subscriber_count END), 0) as vip_volunteer_count,
        COALESCE(SUM(CASE WHEN newsletter = 'Champs_Monthly' THEN subscriber_count END), 0) as champs_monthly_count,
        COALESCE(SUM(CASE WHEN newsletter = 'Wire_to_Wire' THEN subscriber_count END), 0) as wire_to_wire_count,
        COALESCE(SUM(CASE WHEN newsletter = 'Signature_Scroll' THEN subscriber_count END), 0) as signature_scroll_count,
        COALESCE(SUM(CASE WHEN newsletter = 'Truist_Championship' THEN subscriber_count END), 0) as truist_championship_count,
        COALESCE(SUM(CASE WHEN newsletter = 'Players' THEN subscriber_count END), 0) as players_count,
        COALESCE(SUM(CASE WHEN newsletter = 'Cognizant' THEN subscriber_count END), 0) as cognizant_count,
        COALESCE(SUM(CASE WHEN newsletter = 'Biltmore_Championship' THEN subscriber_count END), 0) as biltmore_championship_count,
        COALESCE(SUM(CASE WHEN newsletter = 'Cadillac_Championship' THEN subscriber_count END), 0) as cadillac_championship_count,
        COALESCE(SUM(CASE WHEN newsletter = 'Sompo_Championship' THEN subscriber_count END), 0) as sompo_championship_count
    FROM monthly_counts
    GROUP BY month_end
    ORDER BY month_end DESC
    """
    try:
        return _session.sql(query).to_pandas()
    except Exception as e:
        # Try alternative schema pattern
        try:
            query_alt = query.replace('ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY', 'ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY')
            return _session.sql(query_alt).to_pandas()
        except Exception as e2:
            raise e

def show_subscriber_information():
    """Display subscriber information with current counts and monthly breakdown"""
    st.header("📧 Subscriber Information")
    st.markdown("### Newsletter Subscription Status & Growth Tracking")
    
    session = st.session_state.get('session')
    if not session:
        session = init_session()
        if not session:
            st.error("Unable to connect to Snowflake. Please check your connection.")
            return
        st.session_state['session'] = session
    
    # Get current subscriber counts
    try:
        current_df = get_current_subscriber_counts(session)
    except Exception as e:
        st.error(f"Error loading current subscriber data: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return
    
    if current_df.empty:
        st.warning("No subscriber data available.")
        return
    
    # Normalize column names to lowercase
    current_df.columns = current_df.columns.str.lower()
    
    # Get total deduped subscriber count
    total_deduped = int(current_df['total_deduped_subscribers'].iloc[0]) if 'total_deduped_subscribers' in current_df.columns else 0
    
    # Display headline metric
    st.metric("Total Deduped Subscribers", f"{total_deduped:,}")
    st.markdown("---")
    
    # Display current counts
    st.subheader("📊 Current Subscriber Counts")
    st.markdown("**Raw count of unique emails by subscription newsletter**")
    
    category_filter = st.radio(
        "Newsletter Category",
        options=["PGAT Newsletters", "Tournament Newsletters", "All Newsletters"],
        horizontal=True,
        key="subscriber_category_filter"
    )

    starter_count = int(current_df['starter_count'].iloc[0]) if 'starter_count' in current_df.columns else 0
    partner_offers_count = int(current_df['partner_offers_count'].iloc[0]) if 'partner_offers_count' in current_df.columns else 0
    vip_count = int(current_df['vip_volunteer_count'].iloc[0]) if 'vip_volunteer_count' in current_df.columns else 0
    champs_count = int(current_df['champs_monthly_count'].iloc[0]) if 'champs_monthly_count' in current_df.columns else 0
    wire_count = int(current_df['wire_to_wire_count'].iloc[0]) if 'wire_to_wire_count' in current_df.columns else 0
    sig_scroll_count = int(current_df['signature_scroll_count'].iloc[0]) if 'signature_scroll_count' in current_df.columns else 0
    truist_count = int(current_df['truist_championship_count'].iloc[0]) if 'truist_championship_count' in current_df.columns else 0
    players_count = int(current_df['players_count'].iloc[0]) if 'players_count' in current_df.columns else 0
    cognizant_count = int(current_df['cognizant_count'].iloc[0]) if 'cognizant_count' in current_df.columns else 0
    biltmore_count = int(current_df['biltmore_championship_count'].iloc[0]) if 'biltmore_championship_count' in current_df.columns else 0
    cadillac_count = int(current_df['cadillac_championship_count'].iloc[0]) if 'cadillac_championship_count' in current_df.columns else 0
    sompo_count = int(current_df['sompo_championship_count'].iloc[0]) if 'sompo_championship_count' in current_df.columns else 0

    if category_filter in ["PGAT Newsletters", "All Newsletters"]:
        if category_filter == "All Newsletters":
            st.markdown("##### 📢 PGAT Newsletters")
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            st.metric("The Early Card (Starter)", f"{starter_count:,}")
        with col2:
            st.metric("Partner Offers", f"{partner_offers_count:,}")
        with col3:
            st.metric("VIP Volunteer", f"{vip_count:,}")
        with col4:
            st.metric("Champs Monthly", f"{champs_count:,}")
        with col5:
            st.metric("Wire to Wire", f"{wire_count:,}")
        with col6:
            st.metric("Signature Scroll", f"{sig_scroll_count:,}")

    if category_filter in ["Tournament Newsletters", "All Newsletters"]:
        if category_filter == "All Newsletters":
            st.markdown("##### 🏆 Tournament Newsletters")
        t_col1, t_col2, t_col3, t_col4, t_col5, t_col6 = st.columns(6)
        with t_col1:
            st.metric("Truist Championship", f"{truist_count:,}")
        with t_col2:
            st.metric("The Players", f"{players_count:,}")
        with t_col3:
            st.metric("Cognizant Classic", f"{cognizant_count:,}")
        with t_col4:
            st.metric("Biltmore Championship", f"{biltmore_count:,}")
        with t_col5:
            st.metric("Cadillac Championship", f"{cadillac_count:,}")
        with t_col6:
            st.metric("Sompo Championship", f"{sompo_count:,}")
    
    # Summary table
    st.subheader("📋 Current Status Summary")
    pgat_rows = [
        {'Newsletter/Subscription': 'The Early Card (Starter)', 'Type': 'PGAT', 'Unique Emails': starter_count},
        {'Newsletter/Subscription': 'Partner Offers', 'Type': 'PGAT', 'Unique Emails': partner_offers_count},
        {'Newsletter/Subscription': 'VIP Volunteer', 'Type': 'PGAT', 'Unique Emails': vip_count},
        {'Newsletter/Subscription': 'Champs Monthly', 'Type': 'PGAT', 'Unique Emails': champs_count},
        {'Newsletter/Subscription': 'Wire to Wire', 'Type': 'PGAT', 'Unique Emails': wire_count},
        {'Newsletter/Subscription': 'Signature Scroll', 'Type': 'PGAT', 'Unique Emails': sig_scroll_count},
    ]
    tourn_rows = [
        {'Newsletter/Subscription': 'Truist Championship', 'Type': 'Tournament', 'Unique Emails': truist_count},
        {'Newsletter/Subscription': 'The Players', 'Type': 'Tournament', 'Unique Emails': players_count},
        {'Newsletter/Subscription': 'Cognizant Classic', 'Type': 'Tournament', 'Unique Emails': cognizant_count},
        {'Newsletter/Subscription': 'Biltmore Championship', 'Type': 'Tournament', 'Unique Emails': biltmore_count},
        {'Newsletter/Subscription': 'Cadillac Championship', 'Type': 'Tournament', 'Unique Emails': cadillac_count},
        {'Newsletter/Subscription': 'Sompo Championship', 'Type': 'Tournament', 'Unique Emails': sompo_count},
    ]

    if category_filter == "PGAT Newsletters":
        summary_data = pgat_rows
    elif category_filter == "Tournament Newsletters":
        summary_data = tourn_rows
    else:
        summary_data = pgat_rows + tourn_rows

    summary_df = pd.DataFrame(summary_data)
    st.dataframe(
        summary_df.style.format({'Unique Emails': '{:,}'}),
        use_container_width=True,
    )
    
    # Monthly breakdown
    st.subheader("📅 Monthly Breakdown Over Time")
    st.markdown("**Track growth and progress with monthly subscriber counts**")
    
    try:
        monthly_df = get_monthly_subscriber_breakdown(session)
    except Exception as e:
        st.error(f"Error loading monthly breakdown data: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return
    
    if monthly_df.empty:
        st.warning("No monthly breakdown data available.")
        return
    
    # Normalize column names to lowercase
    monthly_df.columns = monthly_df.columns.str.lower()
    
    # Convert month to datetime if needed
    if 'month' in monthly_df.columns:
        monthly_df['month'] = pd.to_datetime(monthly_df['month'])
        monthly_df = monthly_df.sort_values('month')
    
    # Format the monthly breakdown table
    display_cols = ['month']
    if 'starter_count' in monthly_df.columns:
        display_cols.append('starter_count')
    if 'partner_offers_count' in monthly_df.columns:
        display_cols.append('partner_offers_count')
    if 'vip_volunteer_count' in monthly_df.columns:
        display_cols.append('vip_volunteer_count')
    if 'champs_monthly_count' in monthly_df.columns:
        display_cols.append('champs_monthly_count')
    if 'wire_to_wire_count' in monthly_df.columns:
        display_cols.append('wire_to_wire_count')
    if 'signature_scroll_count' in monthly_df.columns:
        display_cols.append('signature_scroll_count')
    if 'truist_championship_count' in monthly_df.columns:
        display_cols.append('truist_championship_count')
    if 'players_count' in monthly_df.columns:
        display_cols.append('players_count')
    if 'cognizant_count' in monthly_df.columns:
        display_cols.append('cognizant_count')
    if 'biltmore_championship_count' in monthly_df.columns:
        display_cols.append('biltmore_championship_count')
    if 'cadillac_championship_count' in monthly_df.columns:
        display_cols.append('cadillac_championship_count')
    if 'sompo_championship_count' in monthly_df.columns:
        display_cols.append('sompo_championship_count')
    
    monthly_display = monthly_df[display_cols].copy()
    
    column_mapping = {'month': 'Month'}
    if 'starter_count' in monthly_df.columns:
        column_mapping['starter_count'] = 'The Early Card (Starter)'
    if 'partner_offers_count' in monthly_df.columns:
        column_mapping['partner_offers_count'] = 'Partner Offers'
    if 'vip_volunteer_count' in monthly_df.columns:
        column_mapping['vip_volunteer_count'] = 'VIP Volunteer'
    if 'champs_monthly_count' in monthly_df.columns:
        column_mapping['champs_monthly_count'] = 'Champs Monthly'
    if 'wire_to_wire_count' in monthly_df.columns:
        column_mapping['wire_to_wire_count'] = 'Wire to Wire'
    if 'signature_scroll_count' in monthly_df.columns:
        column_mapping['signature_scroll_count'] = 'Signature Scroll'
    if 'truist_championship_count' in monthly_df.columns:
        column_mapping['truist_championship_count'] = 'Truist Championship'
    if 'players_count' in monthly_df.columns:
        column_mapping['players_count'] = 'The Players'
    if 'cognizant_count' in monthly_df.columns:
        column_mapping['cognizant_count'] = 'Cognizant Classic'
    if 'biltmore_championship_count' in monthly_df.columns:
        column_mapping['biltmore_championship_count'] = 'Biltmore Championship'
    if 'cadillac_championship_count' in monthly_df.columns:
        column_mapping['cadillac_championship_count'] = 'Cadillac Championship'
    if 'sompo_championship_count' in monthly_df.columns:
        column_mapping['sompo_championship_count'] = 'Sompo Championship'
        
    monthly_display = monthly_display.rename(columns=column_mapping)
    
    # Format month column
    monthly_display['Month'] = monthly_display['Month'].dt.strftime('%Y-%m')
    
    format_dict = {col: '{:,}' for col in monthly_display.columns if col != 'Month'}
    
    st.dataframe(
        monthly_display.style.format(format_dict),
        height=600,
        use_container_width=True,
    )
    
    st.markdown("---")
    show_subscriber_geographic_breakdown(session)
    st.markdown("---")

    # Growth visualization
    st.subheader("📈 Growth Trends")

    newsletter_options = [c for c in monthly_display.columns if c != "Month"]
    selected_newsletter = st.selectbox(
        "Newsletter",
        options=newsletter_options,
        index=0,
        help="Select a single newsletter to view its growth trend.",
    )

    chart_df = monthly_display[["Month", selected_newsletter]].copy()
    chart_df["month"] = pd.to_datetime(chart_df["Month"].astype(str) + "-01", errors="coerce")
    chart_df["count"] = pd.to_numeric(chart_df[selected_newsletter], errors="coerce")
    chart_df = chart_df.dropna(subset=["month", "count"]).sort_values("month")

    if _HAVE_ALTAIR and not chart_df.empty:
        y_min = float(chart_df["count"].min())
        y_max = float(chart_df["count"].max())
        pad = max((y_max - y_min) * 0.06, 1.0)
        y_domain = [max(0.0, y_min - pad), y_max + pad]

        base = alt.Chart(chart_df).encode(
            x=alt.X("month:T", title=None),
            y=alt.Y("count:Q", title="Unique Emails", scale=alt.Scale(domain=y_domain, nice=False)),
        )

        if hasattr(alt, "selection_point"):
            nearest = alt.selection_point(  # type: ignore[attr-defined]
                nearest=True,
                on="mouseover",
                fields=["month"],
                empty=False,
            )
            _attach = "params"
        else:
            nearest = alt.selection_single(  # type: ignore[attr-defined]
                nearest=True,
                on="mouseover",
                fields=["month"],
                empty="none",
            )
            _attach = "selection"

        area = base.mark_area(opacity=0.12, color="#4DA3FF")
        line = base.mark_line(interpolate="monotone", strokeWidth=2.8, color="#4DA3FF")

        points = base.mark_point(size=80).encode(
            opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
            color=alt.value("#4DA3FF"),
        )
        if _attach == "params":
            points = points.add_params(nearest)  # type: ignore[union-attr]
        else:
            points = points.add_selection(nearest)  # type: ignore[union-attr]

        rule = (
            alt.Chart(chart_df)
            .mark_rule(color="rgba(255,255,255,0.35)")
            .encode(
                x="month:T",
                tooltip=[
                    alt.Tooltip("month:T", title="Month"),
                    alt.Tooltip("count:Q", title=selected_newsletter, format=",.0f"),
                ],
            )
            .transform_filter(nearest)
        )

        growth_chart = (
            alt.layer(area, line, points, rule)
            .properties(height=420, title=f"{selected_newsletter} growth trend")
            .configure_view(strokeOpacity=0)
        ).interactive()

        st.altair_chart(growth_chart, use_container_width=True)
    else:
        fallback = chart_df[["month", "count"]].copy()
        fallback = fallback.set_index("month")
        fallback.columns = [selected_newsletter]
        st.line_chart(fallback, height=400)
    
    # Calculate growth metrics
    if len(monthly_display) > 1:
        st.subheader("📊 Growth Metrics")
        month_idx = pd.to_datetime(monthly_display["Month"].astype(str) + "-01", errors="coerce")
        valid_months = month_idx.dropna()
        if len(valid_months) < 13:
            st.caption("YoY growth requires at least 13 months of data; showing N/A where unavailable.")
        else:
            latest_month = valid_months.iloc[-1]
            prior_target = latest_month - pd.DateOffset(years=1)
            try:
                prior_pos = valid_months.to_numpy().searchsorted(prior_target.to_datetime64(), side="left")
                if prior_pos >= len(valid_months):
                    prior_pos = len(valid_months) - 1
                if prior_pos > 0:
                    # choose nearest of left/right
                    left = valid_months.iloc[prior_pos - 1]
                    right = valid_months.iloc[prior_pos]
                    prior_month = left if abs((left - prior_target).days) <= abs((right - prior_target).days) else right
                else:
                    prior_month = valid_months.iloc[0]
            except Exception:
                prior_month = valid_months.iloc[-13]

            st.caption(
                f"YoY growth compares **{prior_month.strftime('%Y-%m')}** to **{latest_month.strftime('%Y-%m')}** "
                "(nearest available month)."
            )

        # Helper function to display growth metric
        def display_growth_metric(newsletter):
            if newsletter in monthly_display.columns:
                series = pd.to_numeric(monthly_display[newsletter], errors="coerce")
                latest_count = series.iloc[-1] if len(series) > 0 else None
                yoy_growth: int | None = None
                yoy_growth_pct: float | None = None

                if len(valid_months) >= 13 and latest_count is not None and not pd.isna(latest_count):
                    try:
                        latest_pos = int(valid_months.index[-1])
                    except Exception:
                        latest_pos = len(monthly_display) - 1

                    prior_pos_int = None
                    try:
                        prior_pos_int = int(month_idx[month_idx == prior_month].index[0])
                    except Exception:
                        prior_pos_int = latest_pos - 12

                    if prior_pos_int is not None and prior_pos_int >= 0 and prior_pos_int < len(series):
                        prior_count = series.iloc[prior_pos_int]
                        if prior_count is not None and not pd.isna(prior_count):
                            yoy_growth = int(latest_count - prior_count)
                            yoy_growth_pct = (
                                float(yoy_growth) / float(prior_count) * 100
                                if float(prior_count) > 0
                                else None
                            )

                st.metric(
                    newsletter,
                    f"{int(latest_count):,}" if latest_count is not None and not pd.isna(latest_count) else "N/A",
                    delta=(
                        f"{yoy_growth:+,} ({yoy_growth_pct:+.1f}%)"
                        if yoy_growth is not None and yoy_growth_pct is not None
                        else "N/A"
                    ),
                )

        pgat_newsletters = ['The Early Card (Starter)', 'Partner Offers', 'VIP Volunteer', 'Champs Monthly', 'Wire to Wire', 'Signature Scroll']
        tournament_newsletters = ['Truist Championship', 'The Players', 'Cognizant Classic', 'Biltmore Championship', 'Cadillac Championship', 'Sompo Championship']

        if category_filter in ["PGAT Newsletters", "All Newsletters"]:
            if category_filter == "All Newsletters":
                st.markdown("##### 📢 PGAT Newsletters Growth")
            growth_cols = st.columns(6)
            for idx, newsletter in enumerate(pgat_newsletters):
                with growth_cols[idx]:
                    display_growth_metric(newsletter)

        if category_filter in ["Tournament Newsletters", "All Newsletters"]:
            if category_filter == "All Newsletters":
                st.markdown("##### 🏆 Tournament Newsletters Growth")
            growth_cols_t = st.columns(6)
            for idx, newsletter in enumerate(tournament_newsletters):
                with growth_cols_t[idx]:
                    display_growth_metric(newsletter)
    
    # Export functionality
    st.subheader("📥 Export Data")
    csv = monthly_display.to_csv(index=False)
    st.download_button(
        label="Download Monthly Breakdown as CSV",
        data=csv,
        file_name=f"subscriber_monthly_breakdown_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
    
    # Data freshness indicator
    st.caption(f"📅 Data last refreshed: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")


def _render_subscriber_bar_chart(df: pd.DataFrame, category_col: str, value_col: str, title: str, height: int = 360) -> None:
    if df.empty:
        st.info("No chart data available.")
        return

    if _HAVE_ALTAIR:
        chart = (
            alt.Chart(df)
            .mark_bar(color="#1f77b4")
            .encode(
                x=alt.X(f"{value_col}:Q", title=None),
                y=alt.Y(f"{category_col}:N", sort="-x", title=None),
                tooltip=[
                    alt.Tooltip(f"{category_col}:N", title=category_col.title()),
                    alt.Tooltip(f"{value_col}:Q", title="Subscribers", format=",")
                ],
            )
            .properties(title=title, height=height)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.caption(title)
        st.bar_chart(df.set_index(category_col)[value_col], height=height)


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_newsletter_subscriber_geo_breakdown(_session):
    """
    Get geographic breakdown of newsletter subscribers by joining
    newsletter summary / int_fan_subscriber with GOLDEN_ACCOUNT_DEDUP_EMAIL and US_ZIP_CODE_TO_DMA.
    """
    queries = [
        # Candidate 1: ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY + GOLDEN_ACCOUNT_DEDUP_EMAIL + PGAT.LOOKUP.US_ZIP_CODE_TO_DMA
        """
        WITH subscriber_events AS (
            SELECT personid, email, 'The Early Card (Starter)' as newsletter FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(THE_EARLY_CARD_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Partner Offers' as newsletter FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(PARTNER_OFFERS_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'VIP Volunteer' as newsletter FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(VIP_VOLUNTEER_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Champs Monthly' as newsletter FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(CHAMPIONS_MONTHLY_MINUTE_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Wire to Wire' as newsletter FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(WIRE_TO_WIRE_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Signature Scroll' as newsletter FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(SIGNATURE_SCROLL_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Truist Championship' as newsletter FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(TRUIST_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'The Players' as newsletter FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(PLAYERS_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Cognizant Classic' as newsletter FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(COGNIZANT_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Biltmore Championship' as newsletter FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(BILTMORE_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Cadillac Championship' as newsletter FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(CADILLAC_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Sompo Championship' as newsletter FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(SOMPO_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'ALL Newsletters' as newsletter FROM ANALYTICS.PROD_GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE email IS NOT NULL AND (
                LOWER(COALESCE(CAST(THE_EARLY_CARD_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(PARTNER_OFFERS_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(VIP_VOLUNTEER_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(CHAMPIONS_MONTHLY_MINUTE_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(WIRE_TO_WIRE_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(SIGNATURE_SCROLL_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(TRUIST_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(PLAYERS_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(COGNIZANT_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(BILTMORE_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(CADILLAC_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(SOMPO_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'false')) = 'true'
            )
        ),
        joined AS (
            SELECT
                se.newsletter,
                se.email,
                COALESCE(NULLIF(TRIM(zp.country), ''), NULLIF(TRIM(g.country), ''), 'UNKNOWN') as country,
                COALESCE(NULLIF(TRIM(zp.state), ''), NULLIF(TRIM(g.state), ''), 'UNKNOWN') as state,
                COALESCE(NULLIF(TRIM(zp.dma_name), ''), 'UNKNOWN') as dma_name,
                zp.dma_code,
                zp.latitude,
                zp.longitude,
                COALESCE(NULLIF(TRIM(zp.primary_city), ''), NULLIF(TRIM(g.city), ''), 'UNKNOWN') as city,
                LEFT(TRIM(g.zip), 5) as zip
            FROM subscriber_events se
            LEFT JOIN ANALYTICS.PROD_GOLDEN.GOLDEN_ACCOUNT_DEDUP_EMAIL g ON LOWER(TRIM(se.email)) = g.email
            LEFT JOIN PGAT.LOOKUP.US_ZIP_CODE_TO_DMA zp ON LPAD(LEFT(TRIM(g.zip), 5), 5, '0') = zp.zip
        )
        SELECT
            newsletter,
            UPPER(country) as country,
            UPPER(state) as state,
            dma_code,
            UPPER(dma_name) as dma_name,
            UPPER(city) as city,
            zip,
            latitude,
            longitude,
            COUNT(DISTINCT email) as subscriber_count
        FROM joined
        GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9
        """,
        # Candidate 2: ANALYTICS.GOLDEN schema fallback
        """
        WITH subscriber_events AS (
            SELECT personid, email, 'The Early Card (Starter)' as newsletter FROM ANALYTICS.GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(THE_EARLY_CARD_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Partner Offers' as newsletter FROM ANALYTICS.GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(PARTNER_OFFERS_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'VIP Volunteer' as newsletter FROM ANALYTICS.GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(VIP_VOLUNTEER_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Champs Monthly' as newsletter FROM ANALYTICS.GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(CHAMPIONS_MONTHLY_MINUTE_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Wire to Wire' as newsletter FROM ANALYTICS.GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(WIRE_TO_WIRE_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Signature Scroll' as newsletter FROM ANALYTICS.GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(SIGNATURE_SCROLL_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Truist Championship' as newsletter FROM ANALYTICS.GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(TRUIST_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'The Players' as newsletter FROM ANALYTICS.GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(PLAYERS_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Cognizant Classic' as newsletter FROM ANALYTICS.GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(COGNIZANT_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Biltmore Championship' as newsletter FROM ANALYTICS.GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(BILTMORE_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Cadillac Championship' as newsletter FROM ANALYTICS.GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(CADILLAC_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Sompo Championship' as newsletter FROM ANALYTICS.GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE LOWER(COALESCE(CAST(SOMPO_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'ALL Newsletters' as newsletter FROM ANALYTICS.GOLDEN.NEWSLETTER_SUBSCRIPTION_SUMMARY WHERE email IS NOT NULL AND (
                LOWER(COALESCE(CAST(THE_EARLY_CARD_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(PARTNER_OFFERS_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(VIP_VOLUNTEER_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(CHAMPIONS_MONTHLY_MINUTE_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(WIRE_TO_WIRE_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(SIGNATURE_SCROLL_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(TRUIST_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(PLAYERS_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(COGNIZANT_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(BILTMORE_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(CADILLAC_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(SOMPO_CHAMPIONSHIP_SUBSCRIBER AS VARCHAR), 'false')) = 'true'
            )
        ),
        joined AS (
            SELECT
                se.newsletter,
                se.email,
                COALESCE(NULLIF(TRIM(zp.country), ''), NULLIF(TRIM(g.country), ''), 'UNKNOWN') as country,
                COALESCE(NULLIF(TRIM(zp.state), ''), NULLIF(TRIM(g.state), ''), 'UNKNOWN') as state,
                COALESCE(NULLIF(TRIM(zp.dma_name), ''), 'UNKNOWN') as dma_name,
                zp.dma_code,
                zp.latitude,
                zp.longitude,
                COALESCE(NULLIF(TRIM(zp.primary_city), ''), NULLIF(TRIM(g.city), ''), 'UNKNOWN') as city,
                LEFT(TRIM(g.zip), 5) as zip
            FROM subscriber_events se
            LEFT JOIN ANALYTICS.GOLDEN.GOLDEN_ACCOUNT_DEDUP_EMAIL g ON LOWER(TRIM(se.email)) = g.email
            LEFT JOIN PGAT.LOOKUP.US_ZIP_CODE_TO_DMA zp ON LPAD(LEFT(TRIM(g.zip), 5), 5, '0') = zp.zip
        )
        SELECT
            newsletter,
            UPPER(country) as country,
            UPPER(state) as state,
            dma_code,
            UPPER(dma_name) as dma_name,
            UPPER(city) as city,
            zip,
            latitude,
            longitude,
            COUNT(DISTINCT email) as subscriber_count
        FROM joined
        GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9
        """,
        # Candidate 3: Using INT_FAN_SUBSCRIBER with US_ZIP_CODE_TO_DMA
        """
        WITH subscriber_events AS (
            SELECT personid, email, 'The Early Card (Starter)' as newsletter FROM ANALYTICS.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(STARTERSUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Partner Offers' as newsletter FROM ANALYTICS.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(PARTNEROFFERS AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'VIP Volunteer' as newsletter FROM ANALYTICS.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(VIPSUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Champs Monthly' as newsletter FROM ANALYTICS.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(MONTHLYMINUTESUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Wire to Wire' as newsletter FROM ANALYTICS.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(WIRETOWIRESUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Signature Scroll' as newsletter FROM ANALYTICS.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(SIGNATURESCROLLSUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Truist Championship' as newsletter FROM ANALYTICS.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(TRUISTCHAMPIONSHIPSUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'The Players' as newsletter FROM ANALYTICS.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(THEPLAYERSSUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Cognizant Classic' as newsletter FROM ANALYTICS.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(COGNIZANTSUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Biltmore Championship' as newsletter FROM ANALYTICS.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(BILTMORECHAMPIONSHIPSUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Cadillac Championship' as newsletter FROM ANALYTICS.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(CADILLACCHAMPIONSHIPSUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Sompo Championship' as newsletter FROM ANALYTICS.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(SOMPOCHAMPIONSHIPSUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'ALL Newsletters' as newsletter FROM ANALYTICS.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE email IS NOT NULL AND (
                LOWER(COALESCE(CAST(STARTERSUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(PARTNEROFFERS AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(VIPSUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(MONTHLYMINUTESUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(WIRETOWIRESUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(SIGNATURESCROLLSUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(TRUISTCHAMPIONSHIPSUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(THEPLAYERSSUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(COGNIZANTSUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(BILTMORECHAMPIONSHIPSUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(CADILLACCHAMPIONSHIPSUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(SOMPOCHAMPIONSHIPSUBSCRIBER AS VARCHAR), 'false')) = 'true'
            )
        ),
        joined AS (
            SELECT
                se.newsletter,
                se.email,
                COALESCE(NULLIF(TRIM(zp.country), ''), NULLIF(TRIM(g.country), ''), 'UNKNOWN') as country,
                COALESCE(NULLIF(TRIM(zp.state), ''), NULLIF(TRIM(g.state), ''), 'UNKNOWN') as state,
                COALESCE(NULLIF(TRIM(zp.dma_name), ''), 'UNKNOWN') as dma_name,
                zp.dma_code,
                zp.latitude,
                zp.longitude,
                COALESCE(NULLIF(TRIM(zp.primary_city), ''), NULLIF(TRIM(g.city), ''), 'UNKNOWN') as city,
                LEFT(TRIM(g.zip), 5) as zip
            FROM subscriber_events se
            LEFT JOIN PGAT.GOLDEN.FAN g ON se.personid = g.personid
            LEFT JOIN PGAT.LOOKUP.US_ZIP_CODE_TO_DMA zp ON LPAD(LEFT(TRIM(g.zip), 5), 5, '0') = zp.zip
        )
        SELECT
            newsletter,
            UPPER(country) as country,
            UPPER(state) as state,
            dma_code,
            UPPER(dma_name) as dma_name,
            UPPER(city) as city,
            zip,
            latitude,
            longitude,
            COUNT(DISTINCT email) as subscriber_count
        FROM joined
        GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9
        """,
        # Candidate 4: INTERMEDIATE.PROD_GOLDEN.INT_FAN_SUBSCRIBER with US_ZIP_CODE_TO_DMA
        """
        WITH subscriber_events AS (
            SELECT personid, email, 'The Early Card (Starter)' as newsletter FROM INTERMEDIATE.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(STARTERSUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Partner Offers' as newsletter FROM INTERMEDIATE.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(PARTNEROFFERS AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'VIP Volunteer' as newsletter FROM INTERMEDIATE.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(VIPSUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Champs Monthly' as newsletter FROM INTERMEDIATE.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(MONTHLYMINUTESUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Wire to Wire' as newsletter FROM INTERMEDIATE.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(WIRETOWIRESUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Signature Scroll' as newsletter FROM INTERMEDIATE.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(SIGNATURESCROLLSUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Truist Championship' as newsletter FROM INTERMEDIATE.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(TRUISTCHAMPIONSHIPSUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'The Players' as newsletter FROM INTERMEDIATE.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(THEPLAYERSSUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Cognizant Classic' as newsletter FROM INTERMEDIATE.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(COGNIZANTSUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Biltmore Championship' as newsletter FROM INTERMEDIATE.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(BILTMORECHAMPIONSHIPSUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Cadillac Championship' as newsletter FROM INTERMEDIATE.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(CADILLACCHAMPIONSHIPSUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'Sompo Championship' as newsletter FROM INTERMEDIATE.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE LOWER(COALESCE(CAST(SOMPOCHAMPIONSHIPSUBSCRIBER AS VARCHAR), 'false')) = 'true' AND email IS NOT NULL
            UNION ALL
            SELECT personid, email, 'ALL Newsletters' as newsletter FROM INTERMEDIATE.PROD_GOLDEN.INT_FAN_SUBSCRIBER WHERE email IS NOT NULL AND (
                LOWER(COALESCE(CAST(STARTERSUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(PARTNEROFFERS AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(VIPSUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(MONTHLYMINUTESUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(WIRETOWIRESUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(SIGNATURESCROLLSUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(TRUISTCHAMPIONSHIPSUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(THEPLAYERSSUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(COGNIZANTSUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(BILTMORECHAMPIONSHIPSUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(CADILLACCHAMPIONSHIPSUBSCRIBER AS VARCHAR), 'false')) = 'true' OR
                LOWER(COALESCE(CAST(SOMPOCHAMPIONSHIPSUBSCRIBER AS VARCHAR), 'false')) = 'true'
            )
        ),
        joined AS (
            SELECT
                se.newsletter,
                se.email,
                COALESCE(NULLIF(TRIM(zp.country), ''), NULLIF(TRIM(g.country), ''), 'UNKNOWN') as country,
                COALESCE(NULLIF(TRIM(zp.state), ''), NULLIF(TRIM(g.state), ''), 'UNKNOWN') as state,
                COALESCE(NULLIF(TRIM(zp.dma_name), ''), 'UNKNOWN') as dma_name,
                zp.dma_code,
                zp.latitude,
                zp.longitude,
                COALESCE(NULLIF(TRIM(zp.primary_city), ''), NULLIF(TRIM(g.city), ''), 'UNKNOWN') as city,
                LEFT(TRIM(g.zip), 5) as zip
            FROM subscriber_events se
            LEFT JOIN PGAT.GOLDEN.FAN g ON se.personid = g.personid
            LEFT JOIN PGAT.LOOKUP.US_ZIP_CODE_TO_DMA zp ON LPAD(LEFT(TRIM(g.zip), 5), 5, '0') = zp.zip
        )
        SELECT
            newsletter,
            UPPER(country) as country,
            UPPER(state) as state,
            dma_code,
            UPPER(dma_name) as dma_name,
            UPPER(city) as city,
            zip,
            latitude,
            longitude,
            COUNT(DISTINCT email) as subscriber_count
        FROM joined
        GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9
        """
    ]

    last_error = None
    for q in queries:
        try:
            df = _session.sql(q).to_pandas()
            if not df.empty:
                df.columns = df.columns.str.lower()
                return df
        except Exception as e:
            last_error = e

    if last_error:
        raise last_error

    return pd.DataFrame(columns=[
        'newsletter', 'country', 'state', 'dma_code', 'dma_name',
        'city', 'zip', 'latitude', 'longitude', 'subscriber_count'
    ])


def show_subscriber_geographic_breakdown(session):
    """Render newsletter subscriber geographic breakdown tabbed view and map"""
    st.subheader("🌍 Subscriber Geographic Breakdown")
    st.markdown("Explore where newsletter subscribers are located globally, by state/province, and by US DMA.")

    try:
        geo_df = get_newsletter_subscriber_geo_breakdown(session)
    except Exception as e:
        st.error(f"Error loading newsletter geographic data: {str(e)}")
        return

    if geo_df.empty:
        st.warning("No geographic subscriber data available.")
        return

    # Normalize column names
    geo_df.columns = geo_df.columns.str.lower()

    # Available newsletters for filtering
    newsletter_options = [
        "ALL Newsletters",
        "The Early Card (Starter)",
        "Partner Offers",
        "VIP Volunteer",
        "Champs Monthly",
        "Wire to Wire",
        "Signature Scroll",
        "Truist Championship",
        "The Players",
        "Cognizant Classic",
        "Biltmore Championship",
        "Cadillac Championship",
        "Sompo Championship",
    ]

    existing_newsletters = set(geo_df['newsletter'].unique()) if 'newsletter' in geo_df.columns else set()
    selectable_newsletters = ["ALL Newsletters"] + [n for n in newsletter_options[1:] if n in existing_newsletters or not existing_newsletters]

    st.markdown("**Toggle between newsletters to view subscriber geographic distribution:**")
    selected_newsletter = st.selectbox(
        "Select Newsletter",
        options=selectable_newsletters,
        index=0,
        help="Select a specific newsletter or ALL Newsletters to view subscriber locations."
    )

    # Filter dataframe based on selection
    if selected_newsletter == "ALL Newsletters":
        filtered_df = geo_df[geo_df['newsletter'] == 'ALL Newsletters'].copy()
        if filtered_df.empty:
            filtered_df = geo_df.copy()
    else:
        filtered_df = geo_df[geo_df['newsletter'] == selected_newsletter].copy()

    if filtered_df.empty:
        st.info(f"No geographic data found for '{selected_newsletter}'.")
        return

    # Total subscribers in current selection (deduplicated across newsletters when ALL Newsletters is selected)
    total_geo_subscribers = filtered_df['subscriber_count'].sum() if 'subscriber_count' in filtered_df.columns else 0
    st.metric(f"Total Location-Mapped Subscribers (Deduped) - {selected_newsletter}", f"{int(total_geo_subscribers):,}")

    st.markdown("---")

    # Map Controls & Visualization
    if 'latitude' in filtered_df.columns and 'longitude' in filtered_df.columns:
        map_df = filtered_df.dropna(subset=['latitude', 'longitude']).copy()
        map_df['latitude'] = pd.to_numeric(map_df['latitude'], errors='coerce')
        map_df['longitude'] = pd.to_numeric(map_df['longitude'], errors='coerce')
        map_df['subscriber_count'] = pd.to_numeric(map_df['subscriber_count'], errors='coerce').fillna(0)
        map_df = map_df.dropna(subset=['latitude', 'longitude'])
        map_df = map_df[map_df['subscriber_count'] > 0]

        if not map_df.empty:
            st.subheader("📍 Geographic Distribution Map")

            m_col1, m_col2 = st.columns(2)
            with m_col1:
                map_style = st.selectbox(
                    "Map visualization style",
                    options=["Heatmap (Density)", "Point Map (Scatter)", "Hexagon Map (3D)"],
                    index=0,
                    key=f"sub_map_style_{selected_newsletter}"
                )
            with m_col2:
                countries_with_coords = sorted([c for c in map_df['country'].unique() if c and c != 'UNKNOWN'])
                selected_map_country = st.selectbox(
                    "Filter map to country",
                    options=["ALL"] + countries_with_coords,
                    index=0 if "US" not in countries_with_coords else countries_with_coords.index("US") + 1,
                    key=f"sub_map_country_{selected_newsletter}"
                )

            filtered_map_df = map_df.copy()
            if selected_map_country != "ALL":
                filtered_map_df = filtered_map_df[filtered_map_df['country'] == selected_map_country]

            if not filtered_map_df.empty:
                mid_lat = filtered_map_df['latitude'].median()
                mid_lon = filtered_map_df['longitude'].median()
                zoom_level = 3 if selected_map_country in ["ALL", "US"] else 5

                if _HAVE_PYDECK:
                    if map_style == "Heatmap (Density)":
                        layer = pdk.Layer(
                            "HeatmapLayer",
                            data=filtered_map_df,
                            get_position="[longitude, latitude]",
                            get_weight="subscriber_count",
                            radius_pixels=25,
                            intensity=1,
                            threshold=0.05,
                        )
                        view_state = pdk.ViewState(
                            latitude=mid_lat,
                            longitude=mid_lon,
                            zoom=zoom_level,
                            pitch=0,
                        )
                        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))

                    elif map_style == "Hexagon Map (3D)":
                        layer = pdk.Layer(
                            "HexagonLayer",
                            data=filtered_map_df,
                            get_position="[longitude, latitude]",
                            get_weight="subscriber_count",
                            radius=20000,
                            elevation_scale=50,
                            elevation_range=[0, 3000],
                            pickable=True,
                            extruded=True,
                        )
                        view_state = pdk.ViewState(
                            latitude=mid_lat,
                            longitude=mid_lon,
                            zoom=zoom_level,
                            pitch=45,
                        )
                        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))

                    else:  # Point Map (Scatter)
                        max_val = filtered_map_df['subscriber_count'].max()
                        filtered_map_df['radius'] = (filtered_map_df['subscriber_count'] / (max_val if max_val > 0 else 1) * 30000) + 5000

                        layer = pdk.Layer(
                            "ScatterplotLayer",
                            data=filtered_map_df,
                            get_position="[longitude, latitude]",
                            get_color="[25, 118, 210, 160]",
                            get_radius="radius",
                            pickable=True,
                        )
                        view_state = pdk.ViewState(
                            latitude=mid_lat,
                            longitude=mid_lon,
                            zoom=zoom_level,
                            pitch=0,
                        )
                        st.pydeck_chart(
                            pdk.Deck(
                                layers=[layer],
                                initial_view_state=view_state,
                                tooltip={"text": "{city}, {state}\nSubscribers: {subscriber_count}"}
                            )
                        )
                else:
                    st.map(filtered_map_df[['latitude', 'longitude']])

            st.write("---")

    # Tabs for Breakdowns: Country, State, DMA
    st.subheader("📊 Location Breakdown Tables & Charts")
    tab_country, tab_state, tab_dma = st.tabs(["Country Breakdown", "State/Province Breakdown", "DMA Breakdown"])

    # Tab 1: Country
    with tab_country:
        st.write("### Country Distribution")
        country_df = filtered_df.groupby("country", as_index=False)["subscriber_count"].sum()
        total_country_subs = country_df["subscriber_count"].sum()
        country_df["percentage"] = (country_df["subscriber_count"] / (total_country_subs if total_country_subs > 0 else 1) * 100).round(2)
        country_df = country_df.sort_values("subscriber_count", ascending=False)

        chart_country_df = country_df.head(10).copy()
        _render_subscriber_bar_chart(
            df=chart_country_df,
            category_col="country",
            value_col="subscriber_count",
            title=f"Top 10 Countries by Subscribers ({selected_newsletter})",
            height=320
        )

        display_country = country_df.copy()
        display_country.columns = ["Country", "Subscribers", "% of Total"]
        display_country["Subscribers"] = display_country["Subscribers"].apply(lambda x: f"{int(x):,}")
        display_country["% of Total"] = display_country["% of Total"].apply(lambda x: f"{x:.2f}%")

        total_country_row = pd.DataFrame([{
            "Country": "Total",
            "Subscribers": f"{int(total_country_subs):,}",
            "% of Total": "100.00%"
        }])
        display_country_with_total = pd.concat([display_country, total_country_row], ignore_index=True)
        st.dataframe(display_country_with_total, use_container_width=True, height=350)

    # Tab 2: State
    with tab_state:
        st.write("### State/Province Distribution")
        countries_available = sorted([c for c in filtered_df["country"].unique() if c])
        default_state_country = "US" if "US" in countries_available else (countries_available[0] if countries_available else "US")

        selected_state_country = st.selectbox(
            "Select Country for State Breakdown",
            options=countries_available if countries_available else ["US"],
            index=countries_available.index(default_state_country) if default_state_country in countries_available else 0,
            key=f"sub_state_country_{selected_newsletter}"
        )

        state_filtered = filtered_df[filtered_df["country"] == selected_state_country]
        state_df = state_filtered.groupby("state", as_index=False)["subscriber_count"].sum()
        total_state_subs = state_df["subscriber_count"].sum()
        state_df["percentage"] = (state_df["subscriber_count"] / (total_state_subs if total_state_subs > 0 else 1) * 100).round(2)
        state_df = state_df.sort_values("subscriber_count", ascending=False)

        chart_state_df = state_df.head(15).copy()
        _render_subscriber_bar_chart(
            df=chart_state_df,
            category_col="state",
            value_col="subscriber_count",
            title=f"Top 15 States/Provinces in {selected_state_country} ({selected_newsletter})",
            height=360
        )

        display_state = state_df.copy()
        display_state.columns = ["State/Province", "Subscribers", "% of Country Total"]
        display_state["Subscribers"] = display_state["Subscribers"].apply(lambda x: f"{int(x):,}")
        display_state["% of Country Total"] = display_state["% of Country Total"].apply(lambda x: f"{x:.2f}%")

        total_state_row = pd.DataFrame([{
            "State/Province": "Total",
            "Subscribers": f"{int(total_state_subs):,}",
            "% of Country Total": "100.00%"
        }])
        display_state_with_total = pd.concat([display_state, total_state_row], ignore_index=True)
        st.dataframe(display_state_with_total, use_container_width=True, height=350)

    # Tab 3: DMA
    with tab_dma:
        st.write("### Designated Market Area (DMA) Distribution")
        st.caption("DMAs are geographic regions in the United States that represent television/media markets.")

        dma_filtered = filtered_df[
            filtered_df["dma_name"].notna() & 
            (filtered_df["dma_name"].astype(str).str.upper() != "UNKNOWN") & 
            (filtered_df["dma_name"].astype(str).str.strip() != "")
        ]

        if dma_filtered.empty:
            st.info("No DMA data available for the selected newsletter.")
        else:
            dma_df = dma_filtered.groupby(["dma_code", "dma_name"], as_index=False, dropna=False)["subscriber_count"].sum()
            total_dma_subs = dma_df["subscriber_count"].sum()
            dma_df["percentage"] = (dma_df["subscriber_count"] / (total_dma_subs if total_dma_subs > 0 else 1) * 100).round(2)
            dma_df = dma_df.sort_values("subscriber_count", ascending=False)

            chart_dma_df = dma_df.head(15).copy()
            _render_subscriber_bar_chart(
                df=chart_dma_df,
                category_col="dma_name",
                value_col="subscriber_count",
                title=f"Top 15 US DMAs ({selected_newsletter})",
                height=360
            )

            display_dma = dma_df.copy()
            display_dma["dma_code"] = pd.to_numeric(display_dma["dma_code"], errors="coerce").fillna(0).astype(int)
            display_dma.columns = ["DMA Code", "DMA Name", "Subscribers", "% of Total DMA"]
            display_dma["Subscribers"] = display_dma["Subscribers"].apply(lambda x: f"{int(x):,}")
            display_dma["% of Total DMA"] = display_dma["% of Total DMA"].apply(lambda x: f"{x:.2f}%")

            total_dma_row = pd.DataFrame([{
                "DMA Code": "",
                "DMA Name": "Total",
                "Subscribers": f"{int(total_dma_subs):,}",
                "% of Total DMA": "100.00%"
            }])
            display_dma_with_total = pd.concat([display_dma, total_dma_row], ignore_index=True)
            st.dataframe(display_dma_with_total, use_container_width=True, height=350)



@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_audience_acuity_distribution_data(_session, relation: str):
    """Get Audience Acuity source distribution data from dbt model"""
    return _session.sql(f"SELECT * FROM {relation}").to_pandas()


def show_audience_acuity_overlay():
    """Display Audience Acuity demographic distribution overlay onto Golden Record"""
    st.header("🎯 Audience Acuity Golden Record Overlay")
    st.markdown("### Demographic Distributions across Golden Record Segments")

    session = st.session_state.get('session')
    if not session:
        session = init_session()
        if not session:
            st.error("Unable to connect to Snowflake. Please check your connection.")
            return
        st.session_state['session'] = session

    relation = ACUITY_RELATION

    # Fetch data
    try:
        df = get_audience_acuity_distribution_data(session, relation)
    except Exception as e:
        st.error(f"Could not load `{relation}`: {str(e)}")
        st.info("Tip: Check the database, schema, and table name in the sidebar. Make sure your dbt models have been run.")
        return

    if df.empty:
        st.warning("No Audience Acuity distribution data available.")
        return

    # Normalize column names to lowercase
    df.columns = df.columns.str.lower()

    # Fill NaN values in source_type to represent the overall Golden Record
    df['source_type'] = df['source_type'].fillna('All Golden Record Users')

    # Get available segments
    segments = sorted(list(df['source_type'].unique()))
    
    # Get available attributes
    attributes = sorted(list(df['attribute'].unique()))
    
    # Attribute mapping for user-friendly labels
    ATTRIBUTE_LABELS = {
        'aa_age_range': 'Age Range',
        'AA_Age_Range': 'Age Range',
        'aa_gender': 'Gender',
        'AA_Gender': 'Gender',
        'aa_marital_status': 'Marital Status',
        'AA_Marital_Status': 'Marital Status',
        'aa_children_hh': 'Children in Household',
        'AA_Children_HH': 'Children in Household',
        'aa_home_owner': 'Home Ownership Status',
        'AA_Home_Owner': 'Home Ownership Status',
        'aa_income_hh': 'Household Income',
        'AA_Income_HH': 'Household Income',
        'aa_net_worth_hh': 'Household Net Worth',
        'AA_Net_Worth_HH': 'Household Net Worth',
        'aa_credit_range': 'Credit Range',
        'AA_Credit_Range': 'Credit Range',
        'aa_occupation_category': 'Occupation Category',
        'AA_Occupation_Category': 'Occupation Category'
    }
    
    # Ensure lowercase keys are also mapped
    friendly_attr_labels = {}
    for k, v in ATTRIBUTE_LABELS.items():
        friendly_attr_labels[k.lower()] = v
        friendly_attr_labels[k] = v

    def get_attr_label(attr):
        return friendly_attr_labels.get(attr, attr.replace('_', ' ').title())

    # Pre-defined logical sort orders for attributes
    SORT_ORDERS = {
        'aa_age_range': ['18-24', '25-34', '35-44', '45-54', '55-64', '65+'],
        'aa_gender': ['M', 'F', 'U', 'Unknown'],
        'aa_marital_status': ['Married', 'Single', 'Divorced', 'Widowed', 'Separated', 'Unknown'],
        'aa_home_owner': ['Home Owner', 'Renter', 'Unknown'],
        'aa_children_hh': ['Yes', 'No', 'Unknown', 'Y', 'N'],
    }
    
    # Lowercase keys for sorting
    sort_orders_lower = {k.lower(): v for k, v in SORT_ORDERS.items()}

    def get_sorted_values_for_attr(attr, vals):
        attr_lower = attr.lower()
        if attr_lower in sort_orders_lower:
            order = sort_orders_lower[attr_lower]
            sorted_vals = [v for v in order if v in vals]
            other_vals = [v for v in vals if v not in order]
            return sorted_vals + sorted(other_vals)
        else:
            return sorted(list(vals))

    # Tab views
    tab_compare, tab_profile, tab_data = st.tabs([
        "📊 Segment Comparison", 
        "👤 Single Segment Profile", 
        "📋 Raw Distribution Data"
    ])

    with tab_compare:
        st.subheader("Compare Segments by Audience Attribute")
        st.markdown("Select an attribute and multiple segments to compare how their distributions differ.")

        col_left, col_right = st.columns([1, 3])

        with col_left:
            # Select attribute
            selected_attr = st.selectbox(
                "Select Audience Attribute",
                options=attributes,
                format_func=get_attr_label,
                key="compare_attr"
            )

            # Select segments to compare
            default_segments = ['All Golden Record Users']
            preferred_defaults = ['Event Attendees', 'Fanatics Buyers', 'TOUR Pass Member']
            for s in preferred_defaults:
                if s in segments:
                    default_segments.append(s)
                    break
                    
            selected_segments = st.multiselect(
                "Select Segments",
                options=segments,
                default=default_segments,
                key="compare_segments"
            )

        with col_right:
            if not selected_segments:
                st.info("Please select at least one segment to display the comparison chart.")
            else:
                # Filter data for selected attribute and segments
                chart_df = df[
                    (df['attribute'] == selected_attr) &
                    (df['source_type'].isin(selected_segments))
                ].copy()

                if chart_df.empty:
                    st.warning("No data found for the selected options.")
                else:
                    attr_label = get_attr_label(selected_attr)
                    unique_vals = chart_df['field_value'].unique()
                    sorted_vals = get_sorted_values_for_attr(selected_attr, unique_vals)

                    # Build clustered bar chart
                    if _HAVE_ALTAIR and alt is not None:
                        chart_df['field_distribution'] = pd.to_numeric(chart_df['field_distribution'], errors='coerce')
                        chart_df['field_records'] = pd.to_numeric(chart_df['field_records'], errors='coerce')
                        
                        chart = alt.Chart(chart_df).mark_bar().encode(
                            y=alt.Y('source_type:N', title=None, axis=alt.Axis(labels=True)),
                            x=alt.X('field_distribution:Q', title='Percentage of Segment', axis=alt.Axis(format='.0%')),
                            color=alt.Color('source_type:N', legend=alt.Legend(title="Segments"), scale=alt.Scale(scheme='tableau10')),
                            row=alt.Row('field_value:N', title=attr_label, sort=sorted_vals, header=alt.Header(labelAngle=0, labelAlign='left', labelFontSize=12)),
                            tooltip=[
                                alt.Tooltip('source_type:N', title='Segment'),
                                alt.Tooltip('field_value:N', title='Value'),
                                alt.Tooltip('field_distribution:Q', title='Percentage', format='.1%'),
                                alt.Tooltip('field_records:Q', title='Profiles Count', format=',.0f')
                            ]
                        ).properties(
                            height=60,
                            width=600
                        ).configure_view(
                            strokeOpacity=0
                        )
                        st.altair_chart(chart, use_container_width=True)
                    else:
                        pivot_df = chart_df.pivot(index='field_value', columns='source_type', values='field_distribution')
                        pivot_df = pivot_df.reindex(sorted_vals)
                        st.bar_chart(pivot_df)

                    st.markdown("#### Distribution Detail Table")
                    display_pivot = chart_df.pivot(index='field_value', columns='source_type', values='field_distribution')
                    display_pivot = display_pivot.reindex(sorted_vals)
                    
                    # Safe percentage formatting
                    display_pivot_fmt = display_pivot.copy()
                    for col in display_pivot_fmt.columns:
                        display_pivot_fmt[col] = display_pivot_fmt[col].map(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "0.0%")
                    
                    st.dataframe(display_pivot_fmt, use_container_width=True)

    with tab_profile:
        st.subheader("👤 Single Segment Persona Profile")
        st.markdown("Select a specific segment of your Golden Record to see its full Audience Acuity demographic profile at a glance.")

        selected_segment = st.selectbox(
            "Select Segment to Profile",
            options=segments,
            index=segments.index('All Golden Record Users') if 'All Golden Record Users' in segments else 0,
            key="profile_segment"
        )

        segment_df = df[df['source_type'] == selected_segment].copy()

        if segment_df.empty:
            st.warning("No Audience Acuity data available for this segment.")
        else:
            segment_matched_total = int(segment_df['attribute_total'].max()) if not segment_df['attribute_total'].empty else 0
            st.markdown(f"**Total profiles in segment with Audience Acuity enrichment:** {segment_matched_total:,}")
            st.markdown("---")

            profile_attrs = [
                ('aa_age_range', 'Age Range'),
                ('aa_gender', 'Gender'),
                ('aa_marital_status', 'Marital Status'),
                ('aa_income_hh', 'Household Income'),
                ('aa_net_worth_hh', 'Household Net Worth'),
                ('aa_home_owner', 'Home Ownership')
            ]

            available_profile_attrs = [attr for attr in profile_attrs if attr[0] in segment_df['attribute'].unique() or attr[0].upper() in segment_df['attribute'].unique()]

            if not available_profile_attrs:
                st.info("No matching demographic profile attributes available for this segment.")
            else:
                cols = st.columns(3)
                
                for idx, (attr_id, attr_label) in enumerate(available_profile_attrs):
                    col_selector = cols[idx % 3]
                    
                    with col_selector:
                        attr_data = segment_df[segment_df['attribute'].str.lower() == attr_id.lower()].copy()
                        unique_vals = attr_data['field_value'].unique()
                        sort_order = get_sorted_values_for_attr(attr_id, unique_vals)
                        
                        attr_data['field_distribution'] = pd.to_numeric(attr_data['field_distribution'], errors='coerce')
                        attr_data['field_records'] = pd.to_numeric(attr_data['field_records'], errors='coerce')

                        if _HAVE_ALTAIR and alt is not None:
                            chart = alt.Chart(attr_data).mark_bar(
                                color='#1f77b4', cornerRadiusTopLeft=4, cornerRadiusTopRight=4
                            ).encode(
                                x=alt.X('field_value:N', sort=sort_order, title=None, axis=alt.Axis(labelAngle=-45)),
                                y=alt.Y('field_distribution:Q', title='Percentage', axis=alt.Axis(format='.0%')),
                                tooltip=[
                                    alt.Tooltip('field_value:N', title='Value'),
                                    alt.Tooltip('field_distribution:Q', title='Percentage', format='.1%'),
                                    alt.Tooltip('field_records:Q', title='Profiles Count', format=',.0f')
                                ]
                            ).properties(
                                title=attr_label,
                                height=200,
                            ).configure_view(
                                strokeOpacity=0
                            )
                            st.altair_chart(chart, use_container_width=True)
                        else:
                            chart_series = attr_data.set_index('field_value')['field_distribution'].reindex(sort_order)
                            st.subheader(attr_label)
                            st.bar_chart(chart_series)

    with tab_data:
        st.subheader("📋 Raw Data & Export")
        st.markdown("Inspect or export the raw unpivoted distribution metrics for custom reporting.")

        f_cols = st.columns(2)
        with f_cols[0]:
            sel_attrs = st.multiselect("Filter by Attributes", options=attributes, format_func=get_attr_label, key="raw_attrs")
        with f_cols[1]:
            sel_segs = st.multiselect("Filter by Segments", options=segments, key="raw_segs")

        raw_display_df = df.copy()
        if sel_attrs:
            raw_display_df = raw_display_df[raw_display_df['attribute'].isin(sel_attrs)]
        if sel_segs:
            raw_display_df = raw_display_df[raw_display_df['source_type'].isin(sel_segs)]

        raw_display_df['attribute_label'] = raw_display_df['attribute'].map(get_attr_label)
        
        cols_to_show = [
            'source_type', 'attribute_label', 'field_value', 
            'field_records', 'attribute_total', 'field_distribution'
        ]
        
        cols_to_show = [c for c in cols_to_show if c in raw_display_df.columns]
        
        export_df = raw_display_df[cols_to_show].copy()
        for num_col in ('field_records', 'attribute_total', 'field_distribution'):
            if num_col in export_df.columns:
                export_df[num_col] = pd.to_numeric(export_df[num_col], errors='coerce')

        st.dataframe(
            export_df.style.format({
                'field_records': '{:,.0f}',
                'attribute_total': '{:,.0f}',
                'field_distribution': '{:.2%}'
            }),
            height=500,
            use_container_width=True
        )

        csv_data = export_df.to_csv(index=False)
        export_name = f"audience_acuity_distribution_{pd.Timestamp.now().strftime('%Y%m%d')}.csv"
        st.download_button(
            label="📥 Download Distribution Data as CSV",
            data=csv_data,
            file_name=export_name,
            mime="text/csv",
            use_container_width=True
        )

        # Fallback: st.download_button is served via a presigned S3 URL that currently
        # fails with SignatureDoesNotMatch in Streamlit in Snowflake. A data-URI link
        # is generated in the page and avoids that URL.
        import base64
        b64_csv = base64.b64encode(csv_data.encode("utf-8")).decode("ascii")
        st.markdown(
            f'<a href="data:text/csv;base64,{b64_csv}" download="{export_name}">'
            f'📥 Alternate download (if the button above errors)</a>',
            unsafe_allow_html=True
        )

    st.caption(f"📅 Data last refreshed: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')} | Source: `{relation}`")


def main():
    """Main application entry point"""
    st.title("📊 Marketing Data Insights Dashboard")
    st.markdown("### 1st Party Data Health & Campaign Performance")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select a page",
        [
            "Data Health",
            "Subscriber Information",
            "Audience Acuity Overlay",
            "Custom Identity Campaigns",
            "Wit Data",
            "Safari WiFi Data",
            "Fanatics Data",
        ],
        index=0,
    )
    
    # Sidebar info
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.info(
        "This dashboard provides insights into campaign performance "
        "and 1st party data health using DBT models."
    )
    
    # Route to appropriate page
    if page == "Data Health":
        show_data_health()
    elif page == "Audience Acuity Overlay":
        show_audience_acuity_overlay()
    elif page == "Custom Identity Campaigns":
        show_custom_identity_campaigns()
    elif page == "Wit Data":
        show_wit_data()
    elif page == "Safari WiFi Data":
        show_safari_wifi_data()
    elif page == "Subscriber Information":
        show_subscriber_information()
    elif page == "Fanatics Data":
        show_fanatics_data()

if __name__ == "__main__":
    main()