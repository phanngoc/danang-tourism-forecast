#!/usr/bin/env python3
"""
Interactive Streamlit Dashboard for Vietnam Tourism Forecast.

Usage:
    streamlit run dashboard.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from src.city_config import CityConfig, load_all_cities, get_city, list_cities
from src.data_collector import (
    collect_all,
    get_visitor_data,
    get_event_series,
    fetch_weather,
)

# ═══════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Vietnam Tourism Forecast",
    page_icon="🏖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Color palette
COLORS = {
    "primary": "#1976D2",
    "secondary": "#E64A19",
    "accent": "#FF7043",
    "success": "#4CAF50",
    "warning": "#FF9800",
    "domestic": "#1976D2",
    "international": "#FF9800",
    "forecast": "#E64A19",
    "band": "#FF7043",
}


# ═══════════════════════════════════════════════════════════
# DATA LOADING (cached)
# ═══════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def load_city_data(city_id: str, fetch_trends: bool = False) -> dict:
    """Load all data for a city. Cached for 1 hour."""
    load_all_cities()
    city = get_city(city_id)
    data = collect_all(
        city=city,
        start_date="2023-01-01",
        fetch_trends=fetch_trends,
    )
    return data


@st.cache_resource
def load_forecaster():
    """Load TimesFM model. Cached across sessions."""
    from src.forecaster import TourismForecaster
    forecaster = TourismForecaster(max_context=512, max_horizon=128)
    forecaster.load_model()
    return forecaster


def get_city_config(city_id: str) -> CityConfig:
    load_all_cities()
    return get_city(city_id)


# ═══════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════

def render_sidebar():
    load_all_cities()
    cities = list_cities()

    st.sidebar.title("🏖️ Vietnam Tourism")
    st.sidebar.markdown("**Forecast Dashboard**")
    st.sidebar.divider()

    city_id = st.sidebar.selectbox(
        "Select City",
        cities,
        format_func=lambda x: get_city_config(x).city_name,
        index=0,
    )

    city = get_city_config(city_id)
    st.sidebar.caption(f"📍 {city.city_name_vi} ({city.latitude:.2f}, {city.longitude:.2f})")
    st.sidebar.caption(f"📊 {len(city.monthly_visitors)} months data | {len(city.events)} events")

    st.sidebar.divider()

    fetch_trends = st.sidebar.checkbox("Fetch Google Trends (live)", value=False,
                                        help="Requires internet. Slower but gets latest data.")

    st.sidebar.divider()
    st.sidebar.markdown("### Navigation")

    return city_id, fetch_trends


# ═══════════════════════════════════════════════════════════
# TAB: OVERVIEW
# ═══════════════════════════════════════════════════════════

def render_overview(city: CityConfig, data: dict):
    st.header(f"📊 Overview — {city.city_name}")

    visitors = data["visitors"]

    # KPI row 1: Visitor metrics
    col1, col2, col3, col4 = st.columns(4)

    latest_month = visitors.index[-1].strftime("%b %Y")
    latest_total = visitors["total_visitors_k"].iloc[-1]
    latest_intl = visitors["intl_visitors_k"].iloc[-1]
    latest_dom = visitors["domestic_visitors_k"].iloc[-1]

    # YoY change
    if len(visitors) > 12:
        yoy_total = visitors["total_visitors_k"].iloc[-1] - visitors["total_visitors_k"].iloc[-13]
        yoy_pct = yoy_total / visitors["total_visitors_k"].iloc[-13] * 100
    else:
        yoy_pct = 0

    with col1:
        st.metric(
            f"Total Visitors ({latest_month})",
            f"{latest_total:,.0f}K",
            f"{yoy_pct:+.1f}% YoY",
        )
    with col2:
        intl_pct = latest_intl / latest_total * 100
        st.metric("International", f"{latest_intl:,.0f}K", f"{intl_pct:.0f}% of total")
    with col3:
        st.metric("Domestic", f"{latest_dom:,.0f}K", f"{100 - intl_pct:.0f}% of total")
    with col4:
        total_all = visitors["total_visitors_k"].sum()
        st.metric("Total (all time)", f"{total_all / 1000:.1f}M", f"{len(visitors)} months")

    # KPI row 2: Business metrics (if available)
    has_business = "revenue_billion_vnd" in visitors.columns and visitors["revenue_billion_vnd"].notna().any()
    if has_business:
        st.markdown("##### 💼 Business Metrics")
        bc1, bc2, bc3, bc4 = st.columns(4)

        latest_rev = visitors["revenue_billion_vnd"].dropna().iloc[-1] if visitors["revenue_billion_vnd"].notna().any() else None
        latest_occ = visitors["occupancy_pct"].dropna().iloc[-1] if visitors["occupancy_pct"].notna().any() else None
        latest_flights = visitors["flights"].dropna().iloc[-1] if visitors["flights"].notna().any() else None
        latest_stay = visitors["avg_stay_days"].dropna().iloc[-1] if visitors["avg_stay_days"].notna().any() else None

        with bc1:
            if latest_rev:
                # YoY revenue
                rev_series = visitors["revenue_billion_vnd"].dropna()
                rev_yoy = ""
                if len(rev_series) > 12:
                    prev = rev_series.iloc[-13]
                    if prev > 0:
                        rev_yoy = f"{(latest_rev - prev) / prev * 100:+.1f}% YoY"
                st.metric("Revenue", f"{latest_rev:,.0f} bn VND", rev_yoy)
        with bc2:
            if latest_occ:
                st.metric("Hotel Occupancy", f"{latest_occ:.0f}%")
        with bc3:
            if latest_flights:
                st.metric("Flights", f"{latest_flights:,.0f}")
        with bc4:
            if latest_stay:
                st.metric("Avg Stay", f"{latest_stay:.1f} days")

    st.divider()

    # Main chart: Visitors over time
    col_chart, col_stats = st.columns([3, 1])

    with col_chart:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=visitors.index, y=visitors["domestic_visitors_k"],
            name="Domestic", marker_color=COLORS["domestic"], opacity=0.8,
        ))
        fig.add_trace(go.Bar(
            x=visitors.index, y=visitors["intl_visitors_k"],
            name="International", marker_color=COLORS["international"], opacity=0.8,
        ))
        fig.update_layout(
            barmode="stack",
            title=f"Monthly Visitors — {city.city_name}",
            xaxis_title="Month", yaxis_title="Visitors (K)",
            height=420, legend=dict(orientation="h", y=-0.15),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_stats:
        st.markdown("#### Quick Stats")
        st.markdown(f"**Peak month:** {visitors['total_visitors_k'].idxmax().strftime('%b %Y')}")
        st.markdown(f"**Peak value:** {visitors['total_visitors_k'].max():,.0f}K")
        st.markdown(f"**Lowest:** {visitors['total_visitors_k'].min():,.0f}K")
        st.markdown(f"**Average:** {visitors['total_visitors_k'].mean():,.0f}K")
        st.markdown(f"**Median:** {visitors['total_visitors_k'].median():,.0f}K")

        # Seasonality hint
        monthly_avg = visitors.groupby(visitors.index.month)["total_visitors_k"].mean()
        peak_month_num = monthly_avg.idxmax()
        low_month_num = monthly_avg.idxmin()
        month_names = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                       7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
        st.markdown(f"**Best season:** {month_names[peak_month_num]}")
        st.markdown(f"**Low season:** {month_names[low_month_num]}")

    # Weather summary (if available)
    if "weather" in data:
        st.divider()
        weather = data["weather"]
        st.subheader("🌡️ Weather Summary (Recent 90 days)")
        recent = weather.tail(90)

        wc1, wc2, wc3, wc4 = st.columns(4)
        with wc1:
            st.metric("Avg Temp Max", f"{recent['temp_max'].mean():.1f}°C")
        with wc2:
            st.metric("Avg Temp Min", f"{recent['temp_min'].mean():.1f}°C")
        with wc3:
            st.metric("Total Rain", f"{recent['rain'].sum():.0f} mm")
        with wc4:
            st.metric("Avg Sunshine", f"{recent['sunshine_hours'].mean():.1f} hrs/day")


# ═══════════════════════════════════════════════════════════
# TAB: VISITOR ANALYSIS
# ═══════════════════════════════════════════════════════════

def render_visitors(city: CityConfig, data: dict):
    st.header(f"👥 Visitor Analysis — {city.city_name}")

    visitors = data["visitors"]

    # Year filter
    years = sorted(visitors.index.year.unique())
    selected_years = st.multiselect("Filter by Year", years, default=years)
    filtered = visitors[visitors.index.year.isin(selected_years)]

    tab1, tab2, tab3 = st.tabs(["📈 Time Series", "📊 Composition", "🔄 YoY Comparison"])

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=filtered.index, y=filtered["total_visitors_k"],
            mode="lines+markers", name="Total",
            line=dict(color=COLORS["primary"], width=2.5),
            marker=dict(size=6),
        ))
        fig.add_trace(go.Scatter(
            x=filtered.index, y=filtered["intl_visitors_k"],
            mode="lines+markers", name="International",
            line=dict(color=COLORS["international"], width=1.5, dash="dash"),
        ))
        fig.add_trace(go.Scatter(
            x=filtered.index, y=filtered["domestic_visitors_k"],
            mode="lines+markers", name="Domestic",
            line=dict(color=COLORS["domestic"], width=1.5, dash="dot"),
        ))

        # Add event markers
        if "events" in data:
            events = data["events"]
            evt_days = events[events["has_event"] == 1]
            for date in evt_days.index:
                if filtered.index[0] <= date <= filtered.index[-1]:
                    fig.add_vline(x=date, line_dash="dash", line_color=COLORS["success"],
                                  opacity=0.3)

        fig.update_layout(
            title="Monthly Visitor Trends",
            xaxis_title="Month", yaxis_title="Visitors (K)",
            height=450, hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        col1, col2 = st.columns(2)

        with col1:
            # Pie chart: intl vs domestic (latest year)
            latest_year = filtered.index.year.max()
            year_data = filtered[filtered.index.year == latest_year]
            intl_total = year_data["intl_visitors_k"].sum()
            dom_total = year_data["domestic_visitors_k"].sum()
            fig_pie = px.pie(
                values=[dom_total, intl_total],
                names=["Domestic", "International"],
                color_discrete_sequence=[COLORS["domestic"], COLORS["international"]],
                title=f"Visitor Composition ({latest_year})",
            )
            fig_pie.update_layout(height=350)
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            # Monthly seasonality
            monthly_avg = filtered.groupby(filtered.index.month).agg({
                "total_visitors_k": "mean",
                "intl_visitors_k": "mean",
                "domestic_visitors_k": "mean",
            }).round(0)
            month_labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            monthly_avg.index = [month_labels[m-1] for m in monthly_avg.index]

            fig_season = go.Figure()
            fig_season.add_trace(go.Bar(
                x=monthly_avg.index, y=monthly_avg["domestic_visitors_k"],
                name="Domestic", marker_color=COLORS["domestic"], opacity=0.8,
            ))
            fig_season.add_trace(go.Bar(
                x=monthly_avg.index, y=monthly_avg["intl_visitors_k"],
                name="International", marker_color=COLORS["international"], opacity=0.8,
            ))
            fig_season.update_layout(
                barmode="stack", title="Seasonal Pattern (Avg by Month)",
                yaxis_title="Visitors (K)", height=350,
            )
            st.plotly_chart(fig_season, use_container_width=True)

    with tab3:
        # YoY comparison
        if len(years) >= 2:
            pivot = filtered.copy()
            pivot["month"] = pivot.index.month
            pivot["year"] = pivot.index.year

            fig_yoy = go.Figure()
            for year in sorted(pivot["year"].unique()):
                yr_data = pivot[pivot["year"] == year]
                fig_yoy.add_trace(go.Scatter(
                    x=[f"{m:02d}" for m in yr_data["month"]],
                    y=yr_data["total_visitors_k"].values,
                    mode="lines+markers", name=str(year),
                    line=dict(width=2), marker=dict(size=6),
                ))
            fig_yoy.update_layout(
                title="Year-over-Year Comparison",
                xaxis_title="Month", yaxis_title="Visitors (K)",
                height=450,
            )
            st.plotly_chart(fig_yoy, use_container_width=True)

            # Growth table
            st.subheader("📈 YoY Growth Rate")
            growth_data = []
            for year in sorted(pivot["year"].unique()):
                if year == pivot["year"].min():
                    continue
                curr = pivot[pivot["year"] == year]["total_visitors_k"].sum()
                prev = pivot[pivot["year"] == year - 1]["total_visitors_k"].sum()
                if prev > 0:
                    growth_data.append({
                        "Year": year,
                        "Total (K)": f"{curr:,.0f}",
                        "Prev Year (K)": f"{prev:,.0f}",
                        "Growth": f"{(curr - prev) / prev * 100:+.1f}%",
                    })
            if growth_data:
                st.dataframe(pd.DataFrame(growth_data), use_container_width=True, hide_index=True)
        else:
            st.info("Need at least 2 years of data for YoY comparison.")

    # Raw data table
    with st.expander("📋 View Raw Data"):
        st.dataframe(filtered.reset_index(), use_container_width=True)
        csv = filtered.to_csv()
        st.download_button("Download CSV", csv, f"{city.city_id}_visitors.csv", "text/csv")


# ═══════════════════════════════════════════════════════════
# TAB: GOOGLE TRENDS
# ═══════════════════════════════════════════════════════════

def render_trends(city: CityConfig, data: dict):
    st.header(f"🔍 Google Trends — {city.city_name}")

    if "trends_weekly" not in data:
        st.warning("Google Trends data not loaded. Enable 'Fetch Google Trends' in sidebar.")
        st.markdown("**Available queries for this city:**")
        for key, term in city.all_queries.items():
            st.markdown(f"- `{key}`: *{term}*")
        return

    trends = data["trends_weekly"]

    tab1, tab2, tab3 = st.tabs(["📈 Trends Lines", "🔥 Heatmap", "📊 Correlation"])

    with tab1:
        # Query selector
        available_queries = trends.columns.tolist()
        selected = st.multiselect(
            "Select queries to display",
            available_queries,
            default=available_queries[:5],
        )

        if selected:
            fig = go.Figure()
            for col in selected:
                fig.add_trace(go.Scatter(
                    x=trends.index, y=trends[col],
                    mode="lines", name=col,
                    line=dict(width=1.5),
                ))
            fig.update_layout(
                title=f"Google Trends — {city.city_name}",
                xaxis_title="Date", yaxis_title="Search Interest (0-100)",
                height=500, hovermode="x unified",
                legend=dict(orientation="h", y=-0.2),
            )
            st.plotly_chart(fig, use_container_width=True)

        # Latest values table
        st.subheader("Latest Values")
        latest = trends.tail(1).T.reset_index()
        latest.columns = ["Query", "Latest Value"]
        latest = latest.sort_values("Latest Value", ascending=False)
        st.dataframe(latest, use_container_width=True, hide_index=True)

    with tab2:
        # Heatmap by month
        st.subheader("Monthly Search Interest Heatmap")
        monthly_trends = trends.resample("ME").mean()
        monthly_trends.index = monthly_trends.index.strftime("%Y-%m")

        fig_heat = px.imshow(
            monthly_trends.T,
            labels=dict(x="Month", y="Query", color="Interest"),
            color_continuous_scale="YlOrRd",
            aspect="auto",
        )
        fig_heat.update_layout(height=max(300, len(available_queries) * 35))
        st.plotly_chart(fig_heat, use_container_width=True)

    with tab3:
        # Correlation matrix
        st.subheader("Query Correlation Matrix")
        corr = trends.corr()
        fig_corr = px.imshow(
            corr,
            color_continuous_scale="RdBu_r",
            zmin=-1, zmax=1,
            labels=dict(color="Correlation"),
        )
        fig_corr.update_layout(height=500, width=600)
        st.plotly_chart(fig_corr, use_container_width=True)

        # Top correlations
        st.subheader("Top Correlated Pairs")
        pairs = []
        for i in range(len(corr.columns)):
            for j in range(i + 1, len(corr.columns)):
                pairs.append({
                    "Query A": corr.columns[i],
                    "Query B": corr.columns[j],
                    "Correlation": corr.iloc[i, j],
                })
        pairs_df = pd.DataFrame(pairs).sort_values("Correlation", ascending=False)
        st.dataframe(pairs_df.head(10), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════
# TAB: WEATHER
# ═══════════════════════════════════════════════════════════

def render_weather(city: CityConfig, data: dict):
    st.header(f"🌡️ Weather Analysis — {city.city_name}")

    if "weather" not in data:
        st.warning("Weather data not available.")
        return

    weather = data["weather"]

    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("From", weather.index.min().date())
    with col2:
        end = st.date_input("To", weather.index.max().date())

    filtered = weather.loc[str(start):str(end)]

    tab1, tab2, tab3 = st.tabs(["🌡️ Temperature", "🌧️ Rainfall", "📊 Tourism vs Weather"])

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=filtered.index, y=filtered["temp_max"],
            mode="lines", name="Max Temp",
            line=dict(color="red", width=1), fill=None,
        ))
        fig.add_trace(go.Scatter(
            x=filtered.index, y=filtered["temp_min"],
            mode="lines", name="Min Temp",
            line=dict(color="blue", width=1),
            fill="tonexty", fillcolor="rgba(173, 216, 230, 0.3)",
        ))
        fig.update_layout(
            title=f"Temperature Range — {city.city_name}",
            yaxis_title="Temperature (°C)", height=400,
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Monthly temperature stats
        monthly_temp = filtered.resample("ME").agg({
            "temp_max": "mean", "temp_min": "mean",
        }).round(1)
        monthly_temp.index = monthly_temp.index.strftime("%Y-%m")
        st.dataframe(monthly_temp, use_container_width=True)

    with tab2:
        fig_rain = make_subplots(specs=[[{"secondary_y": True}]])
        fig_rain.add_trace(go.Bar(
            x=filtered.index, y=filtered["rain"],
            name="Rain (mm)", marker_color="steelblue", opacity=0.6,
        ), secondary_y=False)
        fig_rain.add_trace(go.Scatter(
            x=filtered.index, y=filtered["sunshine_hours"],
            name="Sunshine (hrs)", line=dict(color="orange", width=1.5),
        ), secondary_y=True)
        fig_rain.update_layout(
            title=f"Rainfall & Sunshine — {city.city_name}",
            height=400, hovermode="x unified",
        )
        fig_rain.update_yaxes(title_text="Rain (mm)", secondary_y=False)
        fig_rain.update_yaxes(title_text="Sunshine (hrs)", secondary_y=True)
        st.plotly_chart(fig_rain, use_container_width=True)

        # Monthly rain summary
        monthly_rain = filtered.resample("ME").agg({
            "rain": "sum", "sunshine_hours": "mean",
        }).round(1)
        monthly_rain.columns = ["Total Rain (mm)", "Avg Sunshine (hrs/day)"]
        monthly_rain.index = monthly_rain.index.strftime("%Y-%m")
        st.dataframe(monthly_rain, use_container_width=True)

    with tab3:
        st.subheader("Tourism vs Weather Correlation")

        visitors = data["visitors"]
        # Align weather to monthly for comparison
        monthly_weather = filtered.resample("ME").agg({
            "temp_max": "mean",
            "temp_min": "mean",
            "rain": "sum",
            "sunshine_hours": "mean",
        })

        # Merge with visitors
        merged = visitors.join(monthly_weather, how="inner")
        if len(merged) > 3:
            col1, col2 = st.columns(2)

            with col1:
                fig_scatter1 = px.scatter(
                    merged, x="temp_max", y="total_visitors_k",
                    trendline="ols",
                    labels={"temp_max": "Avg Max Temp (°C)", "total_visitors_k": "Visitors (K)"},
                    title="Visitors vs Temperature",
                )
                fig_scatter1.update_layout(height=350)
                st.plotly_chart(fig_scatter1, use_container_width=True)

            with col2:
                fig_scatter2 = px.scatter(
                    merged, x="rain", y="total_visitors_k",
                    trendline="ols",
                    labels={"rain": "Monthly Rain (mm)", "total_visitors_k": "Visitors (K)"},
                    title="Visitors vs Rainfall",
                )
                fig_scatter2.update_layout(height=350)
                st.plotly_chart(fig_scatter2, use_container_width=True)

            # Correlation table
            corr_cols = ["total_visitors_k", "intl_visitors_k", "temp_max", "rain", "sunshine_hours"]
            available = [c for c in corr_cols if c in merged.columns]
            if len(available) > 2:
                corr = merged[available].corr().round(3)
                st.dataframe(corr, use_container_width=True)
        else:
            st.info("Not enough overlapping data between visitors and weather.")


# ═══════════════════════════════════════════════════════════
# TAB: EVENTS
# ═══════════════════════════════════════════════════════════

def render_events(city: CityConfig, data: dict):
    st.header(f"📅 Events Calendar — {city.city_name}")

    # Events table
    events_list = []
    for evt in city.events:
        events_list.append({
            "Date": evt["date"],
            "Event": evt["name"],
            "Impact": "⭐" * evt["impact"],
            "Duration (days)": evt["duration_days"],
            "Impact Score": evt["impact"],
        })

    events_df = pd.DataFrame(events_list)
    events_df["Date"] = pd.to_datetime(events_df["Date"])
    events_df = events_df.sort_values("Date")

    # Year filter
    years = sorted(events_df["Date"].dt.year.unique())
    selected_year = st.selectbox("Filter Year", ["All"] + [str(y) for y in years])

    if selected_year != "All":
        events_df = events_df[events_df["Date"].dt.year == int(selected_year)]

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Event Timeline")

        # Gantt-style chart
        gantt_data = []
        for _, row in events_df.iterrows():
            start = row["Date"]
            end = start + pd.Timedelta(days=row["Duration (days)"])
            gantt_data.append({
                "Event": row["Event"],
                "Start": start,
                "End": end,
                "Impact": row["Impact Score"],
            })

        gantt_df = pd.DataFrame(gantt_data)
        if not gantt_df.empty:
            fig_gantt = px.timeline(
                gantt_df, x_start="Start", x_end="End", y="Event",
                color="Impact",
                color_continuous_scale=["#90CAF9", "#FF9800", "#E64A19"],
                title="Event Calendar",
            )
            fig_gantt.update_layout(height=max(300, len(gantt_df) * 40))
            st.plotly_chart(fig_gantt, use_container_width=True)

    with col2:
        st.subheader("Impact Distribution")
        impact_counts = events_df["Impact Score"].value_counts().sort_index()
        fig_impact = px.bar(
            x=impact_counts.index, y=impact_counts.values,
            labels={"x": "Impact Score", "y": "Count"},
            color=impact_counts.index,
            color_continuous_scale=["#90CAF9", "#FF9800", "#E64A19"],
        )
        fig_impact.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig_impact, use_container_width=True)

        st.subheader("Stats")
        st.metric("Total Events", len(events_df))
        st.metric("High Impact (3)", len(events_df[events_df["Impact Score"] == 3]))
        total_event_days = events_df["Duration (days)"].sum()
        st.metric("Total Event Days", total_event_days)

    # Events vs Visitors overlay
    if "events" in data:
        st.divider()
        st.subheader("Events vs Visitor Numbers")

        visitors = data["visitors"]
        event_series = data["events"]

        # Monthly event impact
        monthly_events = event_series.resample("ME").agg({
            "event_impact": "mean",
            "has_event": "sum",
        })

        merged = visitors.join(monthly_events, how="inner")
        if len(merged) > 0:
            fig_overlay = make_subplots(specs=[[{"secondary_y": True}]])
            fig_overlay.add_trace(go.Bar(
                x=merged.index, y=merged["total_visitors_k"],
                name="Visitors (K)", marker_color=COLORS["primary"], opacity=0.7,
            ), secondary_y=False)
            fig_overlay.add_trace(go.Scatter(
                x=merged.index, y=merged["has_event"],
                name="Event Days", line=dict(color=COLORS["secondary"], width=2),
                mode="lines+markers",
            ), secondary_y=True)
            fig_overlay.update_layout(
                title="Monthly Visitors vs Event Days",
                height=400, hovermode="x unified",
            )
            fig_overlay.update_yaxes(title_text="Visitors (K)", secondary_y=False)
            fig_overlay.update_yaxes(title_text="Event Days in Month", secondary_y=True)
            st.plotly_chart(fig_overlay, use_container_width=True)

    # Raw table
    with st.expander("📋 View Events Table"):
        display_df = events_df.copy()
        display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
        st.dataframe(display_df[["Date", "Event", "Impact", "Duration (days)"]],
                     use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════
# TAB: FORECAST
# ═══════════════════════════════════════════════════════════

def render_forecast(city: CityConfig, data: dict):
    st.header(f"🔮 Forecast — {city.city_name}")

    st.markdown("Run TimesFM 2.5 forecast on visitor data and (optionally) Google Trends.")

    col1, col2 = st.columns(2)
    with col1:
        visitor_horizon = st.slider("Visitor Forecast Horizon (months)", 1, 24, 6)
    with col2:
        trends_horizon = st.slider("Trends Forecast Horizon (weeks)", 4, 52, 12)

    # Multi-target selector
    visitors = data["visitors"]
    available_targets = ["Total Visitors"]
    if "intl_visitors_k" in visitors.columns:
        available_targets.append("International Visitors")
    if "domestic_visitors_k" in visitors.columns:
        available_targets.append("Domestic Visitors")
    if "revenue_billion_vnd" in visitors.columns and visitors["revenue_billion_vnd"].notna().any():
        available_targets.append("Revenue (bn VND)")
    if "occupancy_pct" in visitors.columns and visitors["occupancy_pct"].notna().any():
        available_targets.append("Hotel Occupancy %")

    extra_targets = st.multiselect(
        "Additional targets to forecast",
        [t for t in available_targets if t != "Total Visitors"],
        default=[],
    )

    if st.button("🚀 Run Forecast", type="primary", use_container_width=True):
        with st.spinner("Loading TimesFM 2.5 model..."):
            forecaster = load_forecaster()

        # ── Visitor Forecast ──
        st.subheader("👥 Visitor Forecast")
        visitor_series = visitors["total_visitors_k"].values

        with st.spinner("Forecasting visitors..."):
            visitor_result = forecaster.forecast(
                visitor_series, horizon=visitor_horizon,
                name=f"Visitors — {city.city_name}",
            )

        # Metrics
        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1:
            st.metric("Last Actual", f"{visitor_result.last_value:,.0f}K")
        with mc2:
            st.metric(f"Forecast +{visitor_horizon}m",
                      f"{visitor_result.point_forecast[-1]:,.0f}K",
                      f"{visitor_result.trend_pct:+.1f}%")
        with mc3:
            st.metric("Lower 10%", f"{visitor_result.lower_10[-1]:,.0f}K")
        with mc4:
            st.metric("Upper 90%", f"{visitor_result.upper_90[-1]:,.0f}K")

        # Chart
        last_date = visitors.index[-1]
        forecast_dates = pd.date_range(
            last_date + pd.DateOffset(months=1),
            periods=visitor_horizon, freq="MS",
        )

        fig_fc = go.Figure()

        # Historical
        fig_fc.add_trace(go.Bar(
            x=visitors.index, y=visitors["total_visitors_k"],
            name="Actual", marker_color=COLORS["primary"], opacity=0.7,
        ))

        # Forecast bars
        fig_fc.add_trace(go.Bar(
            x=forecast_dates, y=visitor_result.point_forecast,
            name="Forecast", marker_color=COLORS["forecast"], opacity=0.7,
        ))

        # Confidence band
        q = visitor_result.quantile_forecast
        if q.shape[1] >= 10:
            fig_fc.add_trace(go.Scatter(
                x=list(forecast_dates) + list(forecast_dates[::-1]),
                y=list(q[:, -1]) + list(q[:, 1][::-1]),
                fill="toself", fillcolor="rgba(255,112,67,0.15)",
                line=dict(color="rgba(255,112,67,0)"),
                name="10%-90% CI",
            ))

        fig_fc.update_layout(
            title=f"Visitor Forecast — {city.city_name} (+{visitor_horizon} months)",
            xaxis_title="Month", yaxis_title="Visitors (K)",
            height=450, hovermode="x unified",
            barmode="group",
        )
        st.plotly_chart(fig_fc, use_container_width=True)

        # Forecast table
        fc_table = pd.DataFrame({
            "Month": forecast_dates.strftime("%Y-%m"),
            "Point Forecast (K)": visitor_result.point_forecast.round(0),
            "Lower 10% (K)": visitor_result.lower_10.round(0),
            "Upper 90% (K)": visitor_result.upper_90.round(0),
        })
        st.dataframe(fc_table, use_container_width=True, hide_index=True)

        csv_fc = fc_table.to_csv(index=False)
        st.download_button(
            "Download Forecast CSV", csv_fc,
            f"{city.city_id}_visitor_forecast.csv", "text/csv",
        )

        # ── Extra Target Forecasts (revenue, occupancy, intl, domestic) ──
        target_to_col = {
            "International Visitors": ("intl_visitors_k", "K visitors"),
            "Domestic Visitors": ("domestic_visitors_k", "K visitors"),
            "Revenue (bn VND)": ("revenue_billion_vnd", "bn VND"),
            "Hotel Occupancy %": ("occupancy_pct", "%"),
        }
        for target_name in extra_targets:
            col_name, unit = target_to_col[target_name]
            series = visitors[col_name].dropna().values
            if len(series) < 24:
                st.warning(f"⚠️ {target_name}: not enough data ({len(series)} points)")
                continue

            st.divider()
            st.subheader(f"📈 {target_name} Forecast")

            with st.spinner(f"Forecasting {target_name}..."):
                target_result = forecaster.forecast(
                    series, horizon=visitor_horizon, name=target_name,
                )

            tc1, tc2, tc3 = st.columns(3)
            with tc1:
                st.metric("Last Actual", f"{target_result.last_value:,.1f} {unit}")
            with tc2:
                st.metric(f"Forecast +{visitor_horizon}m",
                          f"{target_result.point_forecast[-1]:,.1f} {unit}",
                          f"{target_result.trend_pct:+.1f}%")
            with tc3:
                st.metric("Range (10-90%)",
                          f"{target_result.lower_10[-1]:,.0f}–{target_result.upper_90[-1]:,.0f}")

            target_dates = pd.date_range(
                visitors.index[-1] + pd.DateOffset(months=1),
                periods=visitor_horizon, freq="MS",
            )
            valid_idx = visitors[col_name].dropna().index
            fig_t = go.Figure()
            fig_t.add_trace(go.Scatter(
                x=valid_idx, y=visitors.loc[valid_idx, col_name],
                mode="lines+markers", name="Historical",
                line=dict(color=COLORS["primary"], width=2),
            ))
            fig_t.add_trace(go.Scatter(
                x=target_dates, y=target_result.point_forecast,
                mode="lines+markers", name="Forecast",
                line=dict(color=COLORS["forecast"], dash="dash", width=2),
            ))
            q = target_result.quantile_forecast
            if q.shape[1] >= 10:
                fig_t.add_trace(go.Scatter(
                    x=list(target_dates) + list(target_dates[::-1]),
                    y=list(q[:, -1]) + list(q[:, 1][::-1]),
                    fill="toself", fillcolor="rgba(255,112,67,0.15)",
                    line=dict(color="rgba(255,112,67,0)"),
                    name="10%-90% CI",
                ))
            fig_t.update_layout(
                title=f"{target_name} ({target_result.trend_pct:+.1f}%)",
                yaxis_title=unit, height=380,
                hovermode="x unified",
            )
            st.plotly_chart(fig_t, use_container_width=True)

        # ── Trends Forecast ──
        if "trends_weekly" in data:
            st.divider()
            st.subheader("🔍 Google Trends Forecast")

            trends = data["trends_weekly"]
            series_dict = {}
            for col in trends.columns:
                s = trends[col].dropna().values
                if len(s) > 20:
                    series_dict[col] = s

            if series_dict:
                with st.spinner("Forecasting trends..."):
                    trends_results = forecaster.forecast_multiple(
                        series_dict, horizon=trends_horizon
                    )

                # Summary metrics
                trend_summary = []
                for name, r in trends_results.items():
                    trend_summary.append({
                        "Query": name,
                        "Last Value": f"{r.last_value:.0f}",
                        "Forecast End": f"{r.point_forecast[-1]:.0f}",
                        "Trend": f"{r.trend_pct:+.1f}%",
                    })
                st.dataframe(pd.DataFrame(trend_summary), use_container_width=True, hide_index=True)

                # Individual trend charts
                selected_trends = st.multiselect(
                    "Select trends to visualize",
                    list(trends_results.keys()),
                    default=list(trends_results.keys())[:3],
                )

                for trend_name in selected_trends:
                    r = trends_results[trend_name]
                    hist_series = trends[trend_name].dropna()

                    last_trend_date = hist_series.index[-1]
                    fc_dates = pd.date_range(
                        last_trend_date + pd.Timedelta(weeks=1),
                        periods=r.horizon, freq="W",
                    )

                    fig_t = go.Figure()
                    fig_t.add_trace(go.Scatter(
                        x=hist_series.index, y=hist_series.values,
                        mode="lines", name="Historical",
                        line=dict(color=COLORS["primary"]),
                    ))
                    fig_t.add_trace(go.Scatter(
                        x=fc_dates, y=r.point_forecast,
                        mode="lines", name="Forecast",
                        line=dict(color=COLORS["forecast"], dash="dash", width=2),
                    ))

                    q = r.quantile_forecast
                    if q.shape[1] >= 10:
                        fig_t.add_trace(go.Scatter(
                            x=list(fc_dates) + list(fc_dates[::-1]),
                            y=list(q[:, -1]) + list(q[:, 1][::-1]),
                            fill="toself", fillcolor="rgba(255,112,67,0.15)",
                            line=dict(color="rgba(255,112,67,0)"),
                            name="10%-90% CI",
                        ))

                    arrow = "+" if r.trend_pct > 0 else ""
                    fig_t.update_layout(
                        title=f"{trend_name} ({arrow}{r.trend_pct:.1f}%)",
                        height=350, hovermode="x unified",
                    )
                    st.plotly_chart(fig_t, use_container_width=True)

    else:
        st.info("Click **Run Forecast** to generate predictions with TimesFM 2.5.")

        # Show available data summary
        visitors = data["visitors"]
        st.markdown(f"**Available data:** {len(visitors)} months of visitor data "
                    f"({visitors.index.min().strftime('%b %Y')} — "
                    f"{visitors.index.max().strftime('%b %Y')})")

        if "trends_weekly" in data:
            trends = data["trends_weekly"]
            st.markdown(f"**Google Trends:** {len(trends)} weeks, {len(trends.columns)} queries")


# ═══════════════════════════════════════════════════════════
# TAB: BUSINESS METRICS
# ═══════════════════════════════════════════════════════════

def render_business(city: CityConfig, data: dict):
    st.header(f"💼 Business Metrics — {city.city_name}")

    visitors = data["visitors"]

    has_revenue = "revenue_billion_vnd" in visitors.columns and visitors["revenue_billion_vnd"].notna().any()
    if not has_revenue:
        st.info("No business metrics configured for this city yet.")
        return

    biz = visitors.dropna(subset=["revenue_billion_vnd"]).copy()

    # Summary KPIs
    total_rev = biz["revenue_billion_vnd"].sum()
    avg_occ = biz["occupancy_pct"].mean()
    total_flights = biz["flights"].sum() if biz["flights"].notna().any() else 0
    avg_stay = biz["avg_stay_days"].mean()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Revenue", f"{total_rev / 1000:.1f} trillion VND",
                  f"{len(biz)} months tracked")
    with c2:
        st.metric("Avg Occupancy", f"{avg_occ:.0f}%")
    with c3:
        st.metric("Total Flights", f"{total_flights:,.0f}")
    with c4:
        st.metric("Avg Stay", f"{avg_stay:.1f} days")

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs([
        "💰 Revenue", "🏨 Occupancy", "✈️ Flights", "🔗 Correlations",
    ])

    with tab1:
        # Revenue trend
        fig_rev = go.Figure()
        fig_rev.add_trace(go.Bar(
            x=biz.index, y=biz["revenue_billion_vnd"],
            name="Revenue (bn VND)", marker_color="#388E3C", opacity=0.8,
        ))
        fig_rev.update_layout(
            title="Monthly Tourism Revenue (Lưu trú + F&B + Lữ hành)",
            xaxis_title="Month", yaxis_title="Billion VND",
            height=400, hovermode="x unified",
        )
        st.plotly_chart(fig_rev, use_container_width=True)

        # Revenue per visitor
        biz["rev_per_visitor"] = biz["revenue_billion_vnd"] / biz["total_visitors_k"]
        fig_rpv = go.Figure()
        fig_rpv.add_trace(go.Scatter(
            x=biz.index, y=biz["rev_per_visitor"],
            mode="lines+markers", name="Million VND / Visitor",
            line=dict(color="#7B1FA2", width=2),
        ))
        fig_rpv.update_layout(
            title="Revenue per Visitor (Million VND)",
            xaxis_title="Month", yaxis_title="Million VND/visitor",
            height=350,
        )
        st.plotly_chart(fig_rpv, use_container_width=True)

        # Annual rollup
        st.subheader("Annual Revenue Summary")
        biz_year = biz.copy()
        biz_year["year"] = biz_year.index.year
        annual = biz_year.groupby("year").agg({
            "revenue_billion_vnd": "sum",
            "total_visitors_k": "sum",
        }).round(0)
        annual["rev_per_visitor_M"] = (annual["revenue_billion_vnd"] / annual["total_visitors_k"]).round(2)
        annual.columns = ["Revenue (bn VND)", "Visitors (K)", "Rev/Visitor (M VND)"]
        st.dataframe(annual, use_container_width=True)

    with tab2:
        if biz["occupancy_pct"].notna().any():
            fig_occ = make_subplots(specs=[[{"secondary_y": True}]])
            fig_occ.add_trace(go.Bar(
                x=biz.index, y=biz["total_visitors_k"],
                name="Visitors (K)", marker_color=COLORS["primary"], opacity=0.5,
            ), secondary_y=False)
            fig_occ.add_trace(go.Scatter(
                x=biz.index, y=biz["occupancy_pct"],
                mode="lines+markers", name="Occupancy %",
                line=dict(color="#E64A19", width=2.5),
                marker=dict(size=7),
            ), secondary_y=True)
            fig_occ.update_layout(
                title="Hotel Occupancy vs Visitors",
                height=420, hovermode="x unified",
            )
            fig_occ.update_yaxes(title_text="Visitors (K)", secondary_y=False)
            fig_occ.update_yaxes(title_text="Occupancy %", range=[0, 100], secondary_y=True)
            st.plotly_chart(fig_occ, use_container_width=True)

            # Seasonality
            biz_m = biz.copy()
            biz_m["month"] = biz_m.index.month
            monthly_occ = biz_m.groupby("month")["occupancy_pct"].mean().round(0)
            month_labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            fig_occ_season = px.bar(
                x=[month_labels[m-1] for m in monthly_occ.index],
                y=monthly_occ.values,
                labels={"x": "Month", "y": "Avg Occupancy %"},
                title="Occupancy Seasonality",
                color=monthly_occ.values,
                color_continuous_scale="RdYlGn",
            )
            fig_occ_season.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig_occ_season, use_container_width=True)

    with tab3:
        if biz["flights"].notna().any():
            fig_fl = go.Figure()
            fig_fl.add_trace(go.Bar(
                x=biz.index, y=biz["flights"],
                name="Flights", marker_color="#0097A7", opacity=0.8,
            ))
            fig_fl.update_layout(
                title="Monthly Flights (Da Nang/Hue Airport)",
                xaxis_title="Month", yaxis_title="Number of Flights",
                height=400,
            )
            st.plotly_chart(fig_fl, use_container_width=True)

            # Flights vs Visitors
            fig_fl_v = px.scatter(
                biz, x="flights", y="total_visitors_k",
                trendline="ols",
                hover_data={"intl_visitors_k": True},
                labels={"flights": "Flights", "total_visitors_k": "Visitors (K)"},
                title="Flights vs Visitors (linear regression)",
            )
            fig_fl_v.update_layout(height=400)
            st.plotly_chart(fig_fl_v, use_container_width=True)

    with tab4:
        # Correlation matrix of all metrics
        cols = ["total_visitors_k", "intl_visitors_k", "domestic_visitors_k",
                "revenue_billion_vnd", "occupancy_pct", "flights", "avg_stay_days"]
        available = [c for c in cols if c in biz.columns and biz[c].notna().any()]
        corr = biz[available].corr().round(3)

        fig_c = px.imshow(
            corr, color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
            text_auto=True, aspect="auto",
        )
        fig_c.update_layout(title="Metric Correlation Matrix", height=500)
        st.plotly_chart(fig_c, use_container_width=True)

        st.markdown("**Strongest correlations with total visitors:**")
        if "total_visitors_k" in corr.columns:
            visitor_corr = corr["total_visitors_k"].drop("total_visitors_k").sort_values(
                key=abs, ascending=False
            )
            for metric, val in visitor_corr.items():
                emoji = "📈" if val > 0 else "📉"
                st.markdown(f"- {emoji} **{metric}**: {val:+.3f}")

    # Raw data
    with st.expander("📋 View Business Metrics Data"):
        display_cols = ["total_visitors_k", "revenue_billion_vnd", "occupancy_pct",
                        "flights", "avg_stay_days"]
        available = [c for c in display_cols if c in biz.columns]
        st.dataframe(biz[available].round(2), use_container_width=True)
        csv = biz[available].to_csv()
        st.download_button("Download CSV", csv, f"{city.city_id}_business_metrics.csv", "text/csv")


# ═══════════════════════════════════════════════════════════
# TAB: DATA EXPLORER
# ═══════════════════════════════════════════════════════════

def render_data_explorer(city: CityConfig, data: dict):
    st.header(f"🗂️ Data Explorer — {city.city_name}")

    dataset = st.selectbox("Select Dataset", [
        k for k in ["visitors", "weather", "trends_weekly", "trends_daily", "events"]
        if k in data
    ])

    if dataset:
        df = data[dataset]
        st.markdown(f"**Shape:** {df.shape[0]} rows x {df.shape[1]} columns")
        st.markdown(f"**Date range:** {df.index.min()} — {df.index.max()}")
        st.markdown(f"**Columns:** {', '.join(df.columns)}")

        tab1, tab2, tab3 = st.tabs(["📊 Data", "📈 Statistics", "📉 Charts"])

        with tab1:
            st.dataframe(df.reset_index(), use_container_width=True, height=400)
            csv = df.to_csv()
            st.download_button(
                f"Download {dataset}.csv", csv,
                f"{city.city_id}_{dataset}.csv", "text/csv",
            )

        with tab2:
            st.dataframe(df.describe().round(2), use_container_width=True)

            # Missing values
            missing = df.isnull().sum()
            if missing.sum() > 0:
                st.warning(f"Missing values: {missing[missing > 0].to_dict()}")
            else:
                st.success("No missing values")

        with tab3:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                chart_col = st.selectbox("Column to plot", numeric_cols)
                chart_type = st.radio("Chart type", ["Line", "Bar", "Area", "Histogram"],
                                      horizontal=True)

                if chart_type == "Line":
                    fig = px.line(df, y=chart_col, title=chart_col)
                elif chart_type == "Bar":
                    fig = px.bar(df, y=chart_col, title=chart_col)
                elif chart_type == "Area":
                    fig = px.area(df, y=chart_col, title=chart_col)
                else:
                    fig = px.histogram(df, x=chart_col, title=f"Distribution: {chart_col}",
                                       nbins=30)

                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════
# TAB: COMPARE CITIES
# ═══════════════════════════════════════════════════════════

def render_compare():
    st.header("🏙️ City Comparison")

    load_all_cities()
    cities = list_cities()

    if len(cities) < 2:
        st.info("Need at least 2 cities to compare. Add more city configs.")
        return

    selected = st.multiselect("Select cities to compare", cities,
                               default=cities[:2],
                               format_func=lambda x: get_city_config(x).city_name)

    if len(selected) < 2:
        st.warning("Select at least 2 cities.")
        return

    # Load visitor data for each city
    city_visitors = {}
    for city_id in selected:
        city = get_city_config(city_id)
        visitors = get_visitor_data(city)
        city_visitors[city.city_name] = visitors

    tab1, tab2 = st.tabs(["📈 Visitor Comparison", "📊 Statistics"])

    with tab1:
        fig = go.Figure()
        for name, visitors in city_visitors.items():
            fig.add_trace(go.Scatter(
                x=visitors.index, y=visitors["total_visitors_k"],
                mode="lines+markers", name=name,
                line=dict(width=2), marker=dict(size=5),
            ))
        fig.update_layout(
            title="Total Visitors Comparison",
            xaxis_title="Month", yaxis_title="Visitors (K)",
            height=450, hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

        # International ratio comparison
        fig_ratio = go.Figure()
        for name, visitors in city_visitors.items():
            ratio = visitors["intl_visitors_k"] / visitors["total_visitors_k"] * 100
            fig_ratio.add_trace(go.Scatter(
                x=visitors.index, y=ratio,
                mode="lines+markers", name=name,
                line=dict(width=2),
            ))
        fig_ratio.update_layout(
            title="International Visitor Ratio (%)",
            xaxis_title="Month", yaxis_title="% International",
            height=350, hovermode="x unified",
        )
        st.plotly_chart(fig_ratio, use_container_width=True)

    with tab2:
        compare_data = []
        for city_id in selected:
            city = get_city_config(city_id)
            v = city_visitors[city.city_name]
            compare_data.append({
                "City": city.city_name,
                "Data Points": len(v),
                "Avg Monthly (K)": f"{v['total_visitors_k'].mean():.0f}",
                "Peak (K)": f"{v['total_visitors_k'].max():.0f}",
                "Peak Month": v["total_visitors_k"].idxmax().strftime("%b %Y"),
                "Intl Ratio": f"{v['intl_visitors_k'].sum() / v['total_visitors_k'].sum() * 100:.1f}%",
                "Events": len(city.events),
                "Trends Queries": len(city.all_queries),
            })
        st.dataframe(pd.DataFrame(compare_data), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════

def main():
    city_id, fetch_trends = render_sidebar()
    city = get_city_config(city_id)

    # Load data
    data = load_city_data(city_id, fetch_trends)

    # Navigation tabs
    tabs = st.tabs([
        "📊 Overview",
        "👥 Visitors",
        "💼 Business",
        "🔍 Trends",
        "🌡️ Weather",
        "📅 Events",
        "🔮 Forecast",
        "🗂️ Data Explorer",
        "🏙️ Compare Cities",
    ])

    with tabs[0]:
        render_overview(city, data)
    with tabs[1]:
        render_visitors(city, data)
    with tabs[2]:
        render_business(city, data)
    with tabs[3]:
        render_trends(city, data)
    with tabs[4]:
        render_weather(city, data)
    with tabs[5]:
        render_events(city, data)
    with tabs[6]:
        render_forecast(city, data)
    with tabs[7]:
        render_data_explorer(city, data)
    with tabs[8]:
        render_compare()


if __name__ == "__main__":
    main()
