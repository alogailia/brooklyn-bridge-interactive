"""
The Brooklyn Bridge Tourist Loop - Interactive Redesign
Interactive visualization showing directional flow patterns throughout the day
"""

import pandas as pd
import numpy as np
import altair as alt
import panel as pn

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

pn.extension("vega")
alt.data_transformers.disable_max_rows()

# Color palette
BROOKLYN_COLOR = "#E67E22"  # Orange
MANHATTAN_COLOR = "#8E44AD"  # Purple

# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING & PREPARATION
# ══════════════════════════════════════════════════════════════════════════════


def load_and_prepare_data(filepath):
    """Load and preprocess Brooklyn Bridge pedestrian count data."""

    df = pd.read_csv(filepath)
    df["hour_beginning"] = pd.to_datetime(df["hour_beginning"], format="mixed")

    # Clean numeric columns
    for col in ["Pedestrians", "Towards Manhattan", "Towards Brooklyn"]:
        df[col] = df[col].astype(str).str.replace(",", "").astype(float)

    # Extract time features
    df["hour"] = df["hour_beginning"].dt.hour
    df["day_of_week"] = df["hour_beginning"].dt.dayofweek
    df["month"] = df["hour_beginning"].dt.month
    df["year"] = df["hour_beginning"].dt.year

    # Categorical features
    df["is_weekend"] = df["day_of_week"].isin([5, 6])
    df["day_type"] = df["is_weekend"].map({True: "Weekend", False: "Weekday"})
    df["season"] = df["month"].map(
        {
            12: "Winter",
            1: "Winter",
            2: "Winter",
            3: "Spring",
            4: "Spring",
            5: "Spring",
            6: "Summer",
            7: "Summer",
            8: "Summer",
            9: "Fall",
            10: "Fall",
            11: "Fall",
        }
    )

    # Weather simplification
    weather_map = {
        "clear-day": "Clear",
        "partly-cloudy-day": "Partly Cloudy",
        "cloudy": "Cloudy",
        "rain": "Rain",
        "snow": "Snow",
    }
    df["weather_clean"] = df["weather_summary"].map(weather_map).fillna("Other")

    # Directional metrics
    df["net_to_brooklyn"] = df["Towards Brooklyn"] - df["Towards Manhattan"]

    return df


# Load data
df = load_and_prepare_data(
    "Brooklyn_Bridge_Automated_Pedestrian_Counts_Demonstration_Project_20260203.csv"
)

# ══════════════════════════════════════════════════════════════════════════════
# INTERACTIVE CONTROLS
# ══════════════════════════════════════════════════════════════════════════════

day_type_select = pn.widgets.RadioButtonGroup(
    name="Day Type",
    options=["All", "Weekday", "Weekend"],
    value="All",
    button_type="primary",
)

season_select = pn.widgets.Select(
    name="Season", options=["All", "Winter", "Spring", "Summer", "Fall"], value="All"
)

weather_select = pn.widgets.Select(
    name="Weather",
    options=["All", "Clear", "Partly Cloudy", "Cloudy", "Rain", "Snow"],
    value="All",
)

year_select = pn.widgets.IntSlider(
    name="Year", start=2017, end=2019, value=2019, step=1
)

show_variation = pn.widgets.Checkbox(
    name="Show data variation (IQR bands)", value=False
)

# ══════════════════════════════════════════════════════════════════════════════
# VISUALIZATION FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════


def apply_filters(data, day_type, season, weather, year):
    """Apply user-selected filters to the dataset."""

    filtered = data.copy()

    if day_type != "All":
        filtered = filtered[filtered["day_type"] == day_type]
    if season != "All":
        filtered = filtered[filtered["season"] == season]
    if weather != "All":
        filtered = filtered[filtered["weather_clean"] == weather]

    filtered = filtered[filtered["year"] == year]

    return filtered


@pn.depends(day_type_select, season_select, weather_select, year_select, show_variation)
def create_directional_flow_chart(day_type, season, weather, year, show_var):
    """Create the main directional flow visualization."""

    filtered = apply_filters(df, day_type, season, weather, year)

    if len(filtered) == 0:
        return (
            alt.Chart()
            .mark_text(text="No data for this combination", size=16, color="gray")
            .properties(width=800, height=400)
        )

    # Aggregate by hour
    hourly = (
        filtered.groupby("hour")
        .agg(
            to_brooklyn_mean=("Towards Brooklyn", "mean"),
            to_manhattan_mean=("Towards Manhattan", "mean"),
            net_mean=("net_to_brooklyn", "mean"),
            to_brooklyn_q25=("Towards Brooklyn", lambda x: x.quantile(0.25)),
            to_brooklyn_q75=("Towards Brooklyn", lambda x: x.quantile(0.75)),
            to_manhattan_q25=("Towards Manhattan", lambda x: x.quantile(0.25)),
            to_manhattan_q75=("Towards Manhattan", lambda x: x.quantile(0.75)),
        )
        .reset_index()
    )

    # Reshape for plotting
    data_long = pd.DataFrame(
        {
            "hour": list(hourly["hour"]) * 2,
            "direction": ["→ Brooklyn"] * len(hourly) + ["→ Manhattan"] * len(hourly),
            "mean": list(hourly["to_brooklyn_mean"])
            + list(hourly["to_manhattan_mean"]),
            "q25": list(hourly["to_brooklyn_q25"]) + list(hourly["to_manhattan_q25"]),
            "q75": list(hourly["to_brooklyn_q75"]) + list(hourly["to_manhattan_q75"]),
        }
    )

    # Base chart
    base = alt.Chart(data_long).encode(
        x=alt.X(
            "hour:Q",
            title="Hour of Day",
            scale=alt.Scale(domain=[0, 23]),
            axis=alt.Axis(
                values=list(range(0, 24, 3)),
                labelExpr="datum.value == 0 ? '12am' : datum.value == 12 ? '12pm' : datum.value < 12 ? datum.value + 'am' : (datum.value - 12) + 'pm'",
            ),
        ),
        color=alt.Color(
            "direction:N",
            title="Direction",
            scale=alt.Scale(
                domain=["→ Brooklyn", "→ Manhattan"],
                range=[BROOKLYN_COLOR, MANHATTAN_COLOR],
            ),
            legend=alt.Legend(orient="top"),
        ),
    )

    # Build chart based on variation toggle
    if show_var:
        band = base.mark_area(opacity=0.2).encode(
            y=alt.Y("q25:Q", title="Pedestrians per Hour"), y2="q75:Q"
        )
        line = base.mark_line(size=3).encode(
            y="mean:Q",
            tooltip=[
                alt.Tooltip("hour:Q", title="Hour"),
                alt.Tooltip("direction:N", title="Direction"),
                alt.Tooltip("mean:Q", title="Mean", format=".0f"),
                alt.Tooltip("q25:Q", title="25th percentile", format=".0f"),
                alt.Tooltip("q75:Q", title="75th percentile", format=".0f"),
            ],
        )
        main_chart = (band + line).properties(
            width=800,
            height=400,
            title={
                "text": "Directional Flow Throughout the Day",
                "subtitle": f"{day_type} · {season} · {weather} · {year} · n={len(filtered)} hours",
                "fontSize": 16,
                "subtitleFontSize": 11,
            },
        )
    else:
        main_chart = (
            base.mark_line(size=3, point=True)
            .encode(
                y=alt.Y("mean:Q", title="Pedestrians per Hour"),
                tooltip=[
                    alt.Tooltip("hour:Q", title="Hour"),
                    alt.Tooltip("direction:N", title="Direction"),
                    alt.Tooltip("mean:Q", title="Mean pedestrians/hr", format=".0f"),
                ],
            )
            .properties(
                width=800,
                height=400,
                title={
                    "text": "Directional Flow Throughout the Day",
                    "subtitle": f"{day_type} · {season} · {weather} · {year} · n={len(filtered)} hours",
                    "fontSize": 16,
                    "subtitleFontSize": 11,
                },
            )
        )

    # Net flow chart
    net_chart = (
        alt.Chart(hourly)
        .mark_bar()
        .encode(
            x=alt.X("hour:Q", scale=alt.Scale(domain=[0, 23])),
            y=alt.Y("net_mean:Q", title="Net Flow (+ = toward Brooklyn)"),
            color=alt.condition(
                alt.datum.net_mean > 0,
                alt.value(BROOKLYN_COLOR),
                alt.value(MANHATTAN_COLOR),
            ),
            tooltip=[
                alt.Tooltip("hour:Q", title="Hour"),
                alt.Tooltip("net_mean:Q", title="Net toward Brooklyn", format="+.0f"),
            ],
        )
        .properties(
            width=800, height=200, title="Net Directional Flow (Brooklyn - Manhattan)"
        )
    )

    zero_line = (
        alt.Chart(pd.DataFrame({"y": [0]}))
        .mark_rule(strokeDash=[5, 5], size=2)
        .encode(y="y:Q")
    )

    return (main_chart & (net_chart + zero_line)).configure_view(strokeWidth=0)


@pn.depends(day_type_select, season_select, weather_select, year_select)
def create_summary_stats(day_type, season, weather, year):
    """Generate summary statistics panel."""

    filtered = apply_filters(df, day_type, season, weather, year)

    if len(filtered) == 0:
        return pn.pane.Markdown("### No data for this combination")

    # Calculate metrics
    total_to_bk = filtered["Towards Brooklyn"].sum()
    total_to_mn = filtered["Towards Manhattan"].sum()
    total = total_to_bk + total_to_mn

    hourly_net = filtered.groupby("hour")["net_to_brooklyn"].mean()
    reversal_hour = (
        hourly_net[hourly_net > 0].index.min() if any(hourly_net > 0) else None
    )

    hourly_bk = filtered.groupby("hour")["Towards Brooklyn"].mean()
    hourly_mn = filtered.groupby("hour")["Towards Manhattan"].mean()

    # Format output
    md = f"""
### Summary Statistics

**Overall Split:**
- Toward Brooklyn: {(total_to_bk / total) * 100:.1f}% ({total_to_bk:,.0f} total)
- Toward Manhattan: {(total_to_mn / total) * 100:.1f}% ({total_to_mn:,.0f} total)

**The Tourist Loop:**
- Flow reverses at: **{reversal_hour}:00** ({reversal_hour % 12 if reversal_hour else 0}{"pm" if reversal_hour and reversal_hour >= 12 else "am"})
- Peak toward Brooklyn: **{hourly_bk.idxmax()}:00** ({hourly_bk.max():.0f} ped/hr)
- Peak toward Manhattan: **{hourly_mn.idxmax()}:00** ({hourly_mn.max():.0f} ped/hr)

**Sample Size:**
- {len(filtered):,} hourly observations
"""

    return pn.pane.Markdown(
        md, styles={"background": "#F5F5F5", "padding": "15px", "border-radius": "5px"}
    )


def create_year_comparison():
    """Create year-on-year stability comparison chart."""

    yearly = (
        df.groupby(["year", "hour"]).agg(net=("net_to_brooklyn", "mean")).reset_index()
    )

    chart = (
        alt.Chart(yearly)
        .mark_line(point=True)
        .encode(
            x=alt.X("hour:Q", title="Hour of Day", scale=alt.Scale(domain=[0, 23])),
            y=alt.Y("net:Q", title="Net Flow (+ = toward Brooklyn)"),
            color=alt.Color("year:N", title="Year"),
            strokeDash="year:N",
            tooltip=[
                alt.Tooltip("year:N", title="Year"),
                alt.Tooltip("hour:Q", title="Hour"),
                alt.Tooltip("net:Q", title="Net toward Brooklyn", format="+.0f"),
            ],
        )
        .properties(
            width=800,
            height=300,
            title="Year-on-Year Stability of the Tourist Loop Pattern",
        )
    )

    zero_line = (
        alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(strokeDash=[3, 3]).encode(y="y:Q")
    )

    return (chart + zero_line).configure_view(strokeWidth=0)


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD LAYOUT
# ══════════════════════════════════════════════════════════════════════════════

template = pn.template.FastListTemplate(
    title="The Brooklyn Bridge Tourist Loop",
    sidebar=[
        pn.pane.Markdown(
            "## Interactive Controls\nFilter the data to explore how the directional flow pattern changes:"
        ),
        day_type_select,
        season_select,
        weather_select,
        year_select,
        pn.layout.Divider(),
        show_variation,
        pn.layout.Divider(),
        create_summary_stats,
    ],
    main=[
        pn.pane.Markdown("""
## An Interactive Exploration of Directional Flow Patterns

This visualization focuses on the **most surprising finding** from the static analysis: 
the Brooklyn Bridge exhibits a daily "tourist loop" where pedestrian flow reverses direction mid-day.

**The Pattern:**
- **Morning (6am–noon):** More people walk toward Manhattan (tourists + commuters)
- **Afternoon (noon–8pm):** Flow reverses toward Brooklyn (tourists returning)

**Use the controls on the left** to explore how this pattern changes across different conditions.
        """),
        pn.layout.Divider(),
        create_directional_flow_chart,
        pn.layout.Divider(),
        pn.pane.Markdown("## Year-on-Year Stability"),
        create_year_comparison,
        pn.layout.Divider(),
        pn.pane.Markdown("""
### Key Insights from Interactivity:

1. **Weekends amplify the loop** — The reversal is more pronounced on weekends
2. **Weather is decisive** — Clear days show the strongest loop; rain nearly eliminates it
3. **Seasonal variation** — Summer shows the most dramatic reversal; winter mutes it
4. **Pattern stability** — The loop is consistent across 2017–2019

**What interactivity reveals that the static visualization couldn't:**
- Data variation (IQR bands show the pattern is robust, not noise)
- How contextual factors (weather, season, day type) modulate the core pattern
- Year-to-year stability
        """),
    ],
    accent_base_color=BROOKLYN_COLOR,
    header_background="#2C3E50",
)

# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    template.servable()
    print("  Interactive visualization created")
    print("  Run with: panel serve brooklyn_bridge_interactive.py --show")
