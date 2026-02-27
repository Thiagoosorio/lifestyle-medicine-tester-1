import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta
from components.custom_theme import APPLE
from services.body_metrics_service import (
    log_body_metrics,
    get_body_metrics_history,
    get_latest_height,
    delete_body_metrics,
    get_goal_weight,
    set_goal_weight,
    compute_bmi,
    get_dexa_history,
    get_latest_dexa,
    save_dexa_scan,
    delete_dexa_scan,
    extract_dexa_from_pdf,
)
from components.custom_theme import render_section_header

A = APPLE
user_id = st.session_state.user_id

# ── Helpers ─────────────────────────────────────────────────────────────────

PLOTLY_LAYOUT_DEFAULTS = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color=A["chart_text"]),
    margin=dict(t=40, b=40, l=50, r=20),
    hoverlabel=dict(bgcolor="#FFFFFF", font_size=13, font_color=A["label_primary"]),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02,
        xanchor="center", x=0.5, font=dict(size=11),
    ),
)


def bmi_category(bmi):
    """Return (label, color) for a BMI value."""
    if bmi is None:
        return ("--", "#AEAEB2")
    if bmi < 18.5:
        return ("Underweight", "#FFC107")
    if bmi < 25.0:
        return ("Normal", "#4CAF50")
    if bmi < 30.0:
        return ("Overweight", "#FF9800")
    return ("Obese", "#F44336")


def bmi_bar_color(bmi):
    """Return color for BMI bar chart segment."""
    if bmi is None:
        return "#AEAEB2"
    if bmi < 18.5:
        return "#FFC107"
    if bmi < 25.0:
        return "#4CAF50"
    if bmi < 30.0:
        return "#FF9800"
    return "#F44336"


def waist_hip_zone(ratio, gender="unknown"):
    """Return (label, color) health zone for waist-to-hip ratio."""
    if ratio is None:
        return ("--", "#AEAEB2")
    # General guidelines (WHO)
    if gender == "female":
        if ratio <= 0.80:
            return ("Low Risk", "#4CAF50")
        if ratio <= 0.85:
            return ("Moderate Risk", "#FF9800")
        return ("High Risk", "#F44336")
    else:
        if ratio <= 0.90:
            return ("Low Risk", "#4CAF50")
        if ratio <= 0.95:
            return ("Moderate Risk", "#FF9800")
        return ("High Risk", "#F44336")


# ── Page Title ──────────────────────────────────────────────────────────────
st.title("Body Metrics Tracker")
st.markdown("Track your weight, body measurements, and composition over time.")

# Retrieve stored height from session or database
if "body_height_cm" not in st.session_state:
    stored_height = get_latest_height(user_id)
    if stored_height:
        st.session_state.body_height_cm = stored_height

# Goal weight from DB (persistent)
if "goal_weight_kg" not in st.session_state:
    st.session_state.goal_weight_kg = get_goal_weight(user_id)

# Load all data
entries = get_body_metrics_history(user_id)

tab_tracker, tab_dexa = st.tabs(["Body Tracker", "DEXA Scans"])

with tab_tracker:
    # ═══════════════════════════════════════════════════════════════════════
    # 1. LOG ENTRY FORM
    # ═══════════════════════════════════════════════════════════════════════
    st.divider()
    st.markdown("### Log New Entry")

    with st.form("body_metrics_form", clear_on_submit=True):
        form_row1 = st.columns([1, 1, 1])

        with form_row1[0]:
            log_date = st.date_input("Date", value=date.today(), max_value=date.today())
        with form_row1[1]:
            weight_kg = st.number_input(
                "Weight (kg) *", min_value=20.0, max_value=350.0,
                value=None, step=0.1, format="%.1f",
                placeholder="e.g. 85.0",
            )
        with form_row1[2]:
            height_cm_input = st.number_input(
                "Height (cm)",
                min_value=50.0, max_value=250.0,
                value=st.session_state.get("body_height_cm"),
                step=0.1, format="%.1f",
                help="Set once; stored for future entries.",
                placeholder="e.g. 175.0",
            )

        form_row2 = st.columns([1, 1, 1])
        with form_row2[0]:
            waist_cm = st.number_input(
                "Waist circumference (cm)", min_value=0.0, max_value=250.0,
                value=None, step=0.1, format="%.1f",
                placeholder="Optional",
            )
        with form_row2[1]:
            hip_cm = st.number_input(
                "Hip circumference (cm)", min_value=0.0, max_value=250.0,
                value=None, step=0.1, format="%.1f",
                placeholder="Optional",
            )
        with form_row2[2]:
            body_fat_pct = st.number_input(
                "Body fat %", min_value=0.0, max_value=70.0,
                value=None, step=0.1, format="%.1f",
                placeholder="Optional",
            )

        notes = st.text_area("Notes (optional)", height=68, placeholder="How you're feeling, changes in routine, etc.")
        photo_note = st.text_input(
            "Photo comparison note (optional)",
            placeholder="e.g. Face looks slimmer, belt notch down, clothes fitting looser...",
        )

        submitted = st.form_submit_button("Save Entry", use_container_width=True, type="primary")

        if submitted:
            if weight_kg is None:
                st.error("Weight is required.")
            else:
                # Persist height in session
                if height_cm_input:
                    st.session_state.body_height_cm = height_cm_input

                log_body_metrics(
                    user_id=user_id,
                    log_date=log_date.isoformat(),
                    weight_kg=weight_kg,
                    height_cm=height_cm_input if height_cm_input else None,
                    waist_cm=waist_cm if waist_cm else None,
                    hip_cm=hip_cm if hip_cm else None,
                    body_fat_pct=body_fat_pct if body_fat_pct else None,
                    notes=notes if notes else None,
                    photo_note=photo_note if photo_note else None,
                )
                st.success("Entry saved!")
                st.rerun()

    # Settings row: goal weight
    with st.expander("Settings: Goal Weight & Height"):
        set_col1, set_col2 = st.columns(2)
        with set_col1:
            new_goal = st.number_input(
                "Goal weight (kg)", min_value=30.0, max_value=300.0,
                value=st.session_state.get("goal_weight_kg"),
                step=0.5, format="%.1f",
                placeholder="e.g. 75.0",
            )
            if st.button("Set Goal Weight"):
                set_goal_weight(user_id, new_goal)
                st.session_state.goal_weight_kg = new_goal
                st.success(f"Goal weight set to {new_goal} kg")
                st.rerun()
        with set_col2:
            new_height = st.number_input(
                "Update height (cm)", min_value=50.0, max_value=250.0,
                value=st.session_state.get("body_height_cm"),
                step=0.1, format="%.1f",
                placeholder="e.g. 175.0",
            )
            if st.button("Update Height"):
                st.session_state.body_height_cm = new_height
                st.success(f"Height updated to {new_height} cm")
                st.rerun()

    # Reload entries after potential save
    entries = get_body_metrics_history(user_id)

    if not entries:
        st.info("No body metrics logged yet. Use the form above to record your first entry!")
        st.stop()

    # ── Build DataFrame ─────────────────────────────────────────────────────────
    df = pd.DataFrame(entries)
    df["log_date"] = pd.to_datetime(df["log_date"])
    df = df.sort_values("log_date").reset_index(drop=True)

    # Resolve height: use session value, or forward-fill from entries
    height = st.session_state.get("body_height_cm")
    if height is None and df["height_cm"].notna().any():
        height = df.loc[df["height_cm"].notna(), "height_cm"].iloc[-1]
        st.session_state.body_height_cm = height

    # Compute BMI column
    df["bmi"] = df["weight_kg"].apply(lambda w: compute_bmi(w, height))

    # ═══════════════════════════════════════════════════════════════════════════
    # 2. CURRENT STATS DASHBOARD
    # ═══════════════════════════════════════════════════════════════════════════
    st.divider()
    st.markdown("### Current Stats")

    latest = df.iloc[-1]
    first = df.iloc[0]

    current_weight = latest["weight_kg"]
    start_weight = first["weight_kg"]
    weight_delta = round(current_weight - start_weight, 1) if (current_weight and start_weight) else None
    total_lost = round(start_weight - current_weight, 1) if (current_weight and start_weight) else None

    current_bmi = compute_bmi(current_weight, height)
    bmi_label, bmi_color = bmi_category(current_bmi)

    # Waist-to-hip ratio from latest available
    latest_waist = df.loc[df["waist_cm"].notna(), "waist_cm"].iloc[-1] if df["waist_cm"].notna().any() else None
    latest_hip = df.loc[df["hip_cm"].notna(), "hip_cm"].iloc[-1] if df["hip_cm"].notna().any() else None
    wh_ratio = round(latest_waist / latest_hip, 2) if (latest_waist and latest_hip and latest_hip > 0) else None
    wh_label, wh_color = waist_hip_zone(wh_ratio)

    latest_bf = df.loc[df["body_fat_pct"].notna(), "body_fat_pct"].iloc[-1] if df["body_fat_pct"].notna().any() else None

    # Metric cards
    metric_cols = st.columns(5)

    with metric_cols[0]:
        delta_str = f"{weight_delta:+.1f} kg from start" if weight_delta is not None else None
        st.metric(
            label="Current Weight",
            value=f"{current_weight:.1f} kg" if current_weight else "--",
            delta=delta_str,
            delta_color="inverse",
        )

    with metric_cols[1]:
        st.metric(
            label="BMI",
            value=f"{current_bmi}" if current_bmi else "--",
            help=f"Category: {bmi_label}",
        )
        st.markdown(
            f"<span style='background-color:{bmi_color};color:#fff;padding:2px 10px;border-radius:12px;font-size:0.8em;'>"
            f"{bmi_label}</span>",
            unsafe_allow_html=True,
        )

    with metric_cols[2]:
        st.metric(
            label="Waist-to-Hip Ratio",
            value=f"{wh_ratio}" if wh_ratio else "--",
        )
        if wh_ratio:
            st.markdown(
                f"<span style='background-color:{wh_color};color:#fff;padding:2px 10px;border-radius:12px;font-size:0.8em;'>"
                f"{wh_label}</span>",
                unsafe_allow_html=True,
            )

    with metric_cols[3]:
        st.metric(
            label="Body Fat %",
            value=f"{latest_bf:.1f}%" if latest_bf else "--",
        )

    with metric_cols[4]:
        if total_lost is not None:
            color = "#4CAF50" if total_lost >= 0 else "#F44336"
            direction = "lost" if total_lost >= 0 else "gained"
            st.metric(
                label="Total Weight Change",
                value=f"{abs(total_lost):.1f} kg",
                help=f"{abs(total_lost):.1f} kg {direction} since first entry",
            )
            st.markdown(
                f"<span style='background-color:{color};color:#fff;padding:2px 10px;border-radius:12px;font-size:0.8em;'>"
                f"{abs(total_lost):.1f} kg {direction}</span>",
                unsafe_allow_html=True,
            )
        else:
            st.metric(label="Total Weight Change", value="--")

    # ═══════════════════════════════════════════════════════════════════════════
    # 3. WEIGHT TREND CHART
    # ═══════════════════════════════════════════════════════════════════════════
    st.divider()
    st.markdown("### Weight Trend")

    weight_df = df[df["weight_kg"].notna()].copy()

    if len(weight_df) >= 1:
        # 7-day moving average
        weight_df = weight_df.set_index("log_date").resample("D").mean(numeric_only=True).interpolate(method="linear")
        weight_df["ma7"] = weight_df["weight_kg"].rolling(window=7, min_periods=1).mean()
        weight_df = weight_df.reset_index()

        fig_weight = go.Figure()

        goal_weight = st.session_state.get("goal_weight_kg")

        # Goal weight shaded zone (if set)
        if goal_weight:
            fig_weight.add_hrect(
                y0=goal_weight - 1, y1=goal_weight + 1,
                fillcolor="rgba(76, 175, 80, 0.08)",
                line_width=0,
                annotation_text="Goal Zone",
                annotation_position="top left",
                annotation_font=dict(color="rgba(76, 175, 80, 0.6)", size=10),
            )
            fig_weight.add_hline(
                y=goal_weight,
                line_dash="dash", line_color="#4CAF50", line_width=1.5,
                annotation_text=f"Goal: {goal_weight} kg",
                annotation_position="bottom right",
                annotation_font=dict(color="#4CAF50", size=11),
            )

        # Actual weight scatter
        # Use only actual logged data points for scatter (not interpolated)
        actual_df = df[df["weight_kg"].notna()].copy()
        fig_weight.add_trace(go.Scatter(
            x=actual_df["log_date"],
            y=actual_df["weight_kg"],
            mode="markers",
            name="Actual Weight",
            marker=dict(color="#2196F3", size=8, line=dict(width=1, color="#fff")),
            hovertemplate="<b>%{x|%b %d, %Y}</b><br>Weight: %{y:.1f} kg<extra></extra>",
        ))

        # 7-day moving average line
        fig_weight.add_trace(go.Scatter(
            x=weight_df["log_date"],
            y=weight_df["ma7"],
            mode="lines",
            name="7-Day Average",
            line=dict(color="#FF9800", width=3, shape="spline"),
            fill="tozeroy",
            fillcolor="rgba(255, 152, 0, 0.05)",
            hovertemplate="<b>%{x|%b %d, %Y}</b><br>7d Avg: %{y:.1f} kg<extra></extra>",
        ))

        # Milestone annotations
        if start_weight:
            milestones = [10, 20, 30, 40]
            for ms in milestones:
                ms_weight = start_weight - ms
                if ms_weight > 0:
                    # Check if user has reached this milestone
                    reached = actual_df[actual_df["weight_kg"] <= ms_weight]
                    if not reached.empty:
                        first_reach = reached.iloc[0]
                        fig_weight.add_annotation(
                            x=first_reach["log_date"],
                            y=first_reach["weight_kg"],
                            text=f"-{ms} kg!",
                            showarrow=True,
                            arrowhead=2,
                            arrowcolor="#4CAF50",
                            font=dict(color="#4CAF50", size=12, family="Arial Black"),
                            bgcolor="rgba(76,175,80,0.15)",
                            bordercolor="#4CAF50",
                            borderwidth=1,
                            borderpad=4,
                            ax=0, ay=-35,
                        )

        # Y-axis range with padding
        all_weights = actual_df["weight_kg"].tolist()
        if goal_weight:
            all_weights.append(goal_weight)
        y_min = min(all_weights) - 3
        y_max = max(all_weights) + 3

        fig_weight.update_layout(
            **PLOTLY_LAYOUT_DEFAULTS,
            height=420,
            yaxis=dict(
                title="Weight (kg)",
                range=[y_min, y_max],
                showgrid=True, gridcolor=A["chart_grid"],
                color=A["chart_text"],
            ),
            xaxis=dict(
                title="Date",
                showgrid=False,
                tickformat="%b %d",
                color=A["chart_text"],
            ),
            hovermode="x unified",
        )

        st.plotly_chart(fig_weight, use_container_width=True)
    else:
        st.info("Log at least one weight entry to see your trend chart.")

    # ═══════════════════════════════════════════════════════════════════════════
    # 4. BODY COMPOSITION OVER TIME
    # ═══════════════════════════════════════════════════════════════════════════
    has_waist = df["waist_cm"].notna().any()
    has_hip = df["hip_cm"].notna().any()
    has_bf = df["body_fat_pct"].notna().any()

    if has_waist or has_hip or has_bf:
        st.divider()
        st.markdown("### Body Composition Over Time")

        fig_comp = go.Figure()

        if has_waist:
            waist_data = df[df["waist_cm"].notna()]
            fig_comp.add_trace(go.Scatter(
                x=waist_data["log_date"],
                y=waist_data["waist_cm"],
                mode="lines+markers",
                name="Waist (cm)",
                line=dict(color="#E91E63", width=2.5),
                marker=dict(size=6),
                hovertemplate="<b>%{x|%b %d}</b><br>Waist: %{y:.1f} cm<extra></extra>",
            ))

        if has_hip:
            hip_data = df[df["hip_cm"].notna()]
            fig_comp.add_trace(go.Scatter(
                x=hip_data["log_date"],
                y=hip_data["hip_cm"],
                mode="lines+markers",
                name="Hip (cm)",
                line=dict(color="#9C27B0", width=2.5),
                marker=dict(size=6),
                hovertemplate="<b>%{x|%b %d}</b><br>Hip: %{y:.1f} cm<extra></extra>",
            ))

        if has_bf:
            bf_data = df[df["body_fat_pct"].notna()]
            fig_comp.add_trace(go.Scatter(
                x=bf_data["log_date"],
                y=bf_data["body_fat_pct"],
                mode="lines+markers",
                name="Body Fat %",
                line=dict(color="#00BCD4", width=2.5, dash="dot"),
                marker=dict(size=6),
                yaxis="y2",
                hovertemplate="<b>%{x|%b %d}</b><br>Body Fat: %{y:.1f}%<extra></extra>",
            ))

        layout_updates = dict(
            **PLOTLY_LAYOUT_DEFAULTS,
            height=380,
            xaxis=dict(title="Date", showgrid=False, tickformat="%b %d", color=A["chart_text"]),
            yaxis=dict(
                title="Measurement (cm)",
                showgrid=True, gridcolor=A["chart_grid"],
                color=A["chart_text"],
            ),
            hovermode="x unified",
        )

        if has_bf:
            layout_updates["yaxis2"] = dict(
                title="Body Fat %",
                overlaying="y", side="right",
                showgrid=False,
            )

        fig_comp.update_layout(**layout_updates)
        st.plotly_chart(fig_comp, use_container_width=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # 5. BMI TIMELINE
    # ═══════════════════════════════════════════════════════════════════════════
    bmi_df = df[df["bmi"].notna()].copy()

    if len(bmi_df) >= 1 and height:
        st.divider()
        st.markdown("### BMI Timeline")

        bmi_df["bar_color"] = bmi_df["bmi"].apply(bmi_bar_color)
        bmi_df["category"] = bmi_df["bmi"].apply(lambda b: bmi_category(b)[0])

        fig_bmi = go.Figure()

        # Zone backgrounds
        bmi_y_min = max(bmi_df["bmi"].min() - 2, 10)
        bmi_y_max = bmi_df["bmi"].max() + 3

        zone_ranges = [
            (10, 18.5, "rgba(255,193,7,0.08)", "Underweight"),
            (18.5, 25, "rgba(76,175,80,0.08)", "Normal"),
            (25, 30, "rgba(255,152,0,0.08)", "Overweight"),
            (30, 50, "rgba(244,67,54,0.08)", "Obese"),
        ]
        for y0, y1, fill, label in zone_ranges:
            if y1 > bmi_y_min and y0 < bmi_y_max:
                fig_bmi.add_hrect(
                    y0=max(y0, bmi_y_min), y1=min(y1, bmi_y_max),
                    fillcolor=fill, line_width=0,
                )

        # Zone boundary lines
        for boundary, color, label in [(18.5, "#FFC107", "18.5"), (25, "#FF9800", "25"), (30, "#F44336", "30")]:
            if bmi_y_min < boundary < bmi_y_max:
                fig_bmi.add_hline(
                    y=boundary, line_dash="dot", line_color=color, line_width=1,
                    annotation_text=label,
                    annotation_position="right",
                    annotation_font=dict(color=color, size=10),
                )

        fig_bmi.add_trace(go.Bar(
            x=bmi_df["log_date"],
            y=bmi_df["bmi"],
            marker_color=bmi_df["bar_color"].tolist(),
            text=bmi_df.apply(lambda r: f'{r["bmi"]:.1f}<br><sub>{r["category"]}</sub>', axis=1),
            textposition="outside",
            textfont=dict(size=10),
            hovertemplate="<b>%{x|%b %d, %Y}</b><br>BMI: %{y:.1f}<extra></extra>",
            showlegend=False,
        ))

        # Custom legend for zones
        for label, color in [("Underweight", "#FFC107"), ("Normal", "#4CAF50"), ("Overweight", "#FF9800"), ("Obese", "#F44336")]:
            fig_bmi.add_trace(go.Scatter(
                x=[None], y=[None], mode="markers",
                marker=dict(size=10, color=color, symbol="square"),
                name=label,
            ))

        fig_bmi.update_layout(
            **PLOTLY_LAYOUT_DEFAULTS,
            height=400,
            yaxis=dict(
                title="BMI",
                range=[bmi_y_min, bmi_y_max + 2],
                showgrid=True, gridcolor=A["chart_grid"],
                color=A["chart_text"],
            ),
            xaxis=dict(title="Date", showgrid=False, tickformat="%b %d", color=A["chart_text"]),
            bargap=0.3,
        )

        st.plotly_chart(fig_bmi, use_container_width=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # 6. MONTHLY COMPARISON TABLE
    # ═══════════════════════════════════════════════════════════════════════════
    weight_entries = df[df["weight_kg"].notna()].copy()

    if len(weight_entries) >= 2:
        st.divider()
        st.markdown("### Monthly Comparison")

        weight_entries["month"] = weight_entries["log_date"].dt.to_period("M")
        monthly = weight_entries.groupby("month").agg(
            avg_weight=("weight_kg", "mean"),
            min_weight=("weight_kg", "min"),
            max_weight=("weight_kg", "max"),
            entries=("weight_kg", "count"),
        ).reset_index()

        monthly["avg_weight"] = monthly["avg_weight"].round(1)
        monthly["min_weight"] = monthly["min_weight"].round(1)
        monthly["max_weight"] = monthly["max_weight"].round(1)

        # Calculate month-over-month delta
        monthly["delta"] = monthly["avg_weight"].diff().round(1)
        monthly["delta_str"] = monthly["delta"].apply(
            lambda d: f"{d:+.1f} kg" if pd.notna(d) else "--"
        )

        # Format for display
        display_df = pd.DataFrame({
            "Month": monthly["month"].astype(str),
            "Avg Weight (kg)": monthly["avg_weight"],
            "Min (kg)": monthly["min_weight"],
            "Max (kg)": monthly["max_weight"],
            "Change": monthly["delta_str"],
            "Entries": monthly["entries"].astype(int),
        })

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Month": st.column_config.TextColumn("Month", width="medium"),
                "Avg Weight (kg)": st.column_config.NumberColumn("Avg Weight (kg)", format="%.1f"),
                "Min (kg)": st.column_config.NumberColumn("Min (kg)", format="%.1f"),
                "Max (kg)": st.column_config.NumberColumn("Max (kg)", format="%.1f"),
                "Change": st.column_config.TextColumn("Month-over-Month", width="medium"),
                "Entries": st.column_config.NumberColumn("Entries", format="%d"),
            },
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # 7. BEFORE / AFTER SUMMARY
    # ═══════════════════════════════════════════════════════════════════════════
    if len(df) >= 2:
        st.divider()
        st.markdown("### Before & After Summary")

        first_entry = df.iloc[0]
        latest_entry = df.iloc[-1]

        days_elapsed = (latest_entry["log_date"] - first_entry["log_date"]).days

        col_before, col_spacer, col_after = st.columns([5, 1, 5])

        with col_before:
            st.markdown(
                "<div style='background:rgba(244,67,54,0.06);border:1px solid rgba(244,67,54,0.25);"
                "border-radius:12px;padding:20px;'>"
                "<h4 style='margin-top:0;color:#F44336;'>First Entry</h4>",
                unsafe_allow_html=True,
            )
            st.markdown(f"**Date:** {first_entry['log_date'].strftime('%b %d, %Y')}")
            st.markdown(f"**Weight:** {first_entry['weight_kg']:.1f} kg" if first_entry["weight_kg"] else "**Weight:** --")
            first_bmi = compute_bmi(first_entry["weight_kg"], height)
            if first_bmi:
                cat, clr = bmi_category(first_bmi)
                st.markdown(f"**BMI:** {first_bmi} ({cat})")
            if pd.notna(first_entry.get("waist_cm")):
                st.markdown(f"**Waist:** {first_entry['waist_cm']:.1f} cm")
            if pd.notna(first_entry.get("hip_cm")):
                st.markdown(f"**Hip:** {first_entry['hip_cm']:.1f} cm")
            if pd.notna(first_entry.get("body_fat_pct")):
                st.markdown(f"**Body Fat:** {first_entry['body_fat_pct']:.1f}%")
            if first_entry.get("photo_note"):
                st.markdown(f"**Photo Note:** {first_entry['photo_note']}")
            st.markdown("</div>", unsafe_allow_html=True)

        with col_spacer:
            st.markdown(
                "<div style='display:flex;align-items:center;justify-content:center;height:100%;padding-top:60px;'>"
                "<span style='font-size:2em;color:#AEAEB2;'>&#10132;</span></div>",
                unsafe_allow_html=True,
            )

        with col_after:
            st.markdown(
                "<div style='background:rgba(76,175,80,0.06);border:1px solid rgba(76,175,80,0.25);"
                "border-radius:12px;padding:20px;'>"
                "<h4 style='margin-top:0;color:#4CAF50;'>Latest Entry</h4>",
                unsafe_allow_html=True,
            )
            st.markdown(f"**Date:** {latest_entry['log_date'].strftime('%b %d, %Y')}")
            st.markdown(f"**Weight:** {latest_entry['weight_kg']:.1f} kg" if latest_entry["weight_kg"] else "**Weight:** --")
            latest_bmi = compute_bmi(latest_entry["weight_kg"], height)
            if latest_bmi:
                cat, clr = bmi_category(latest_bmi)
                st.markdown(f"**BMI:** {latest_bmi} ({cat})")
            if pd.notna(latest_entry.get("waist_cm")):
                st.markdown(f"**Waist:** {latest_entry['waist_cm']:.1f} cm")
            if pd.notna(latest_entry.get("hip_cm")):
                st.markdown(f"**Hip:** {latest_entry['hip_cm']:.1f} cm")
            if pd.notna(latest_entry.get("body_fat_pct")):
                st.markdown(f"**Body Fat:** {latest_entry['body_fat_pct']:.1f}%")
            if latest_entry.get("photo_note"):
                st.markdown(f"**Photo Note:** {latest_entry['photo_note']}")
            st.markdown("</div>", unsafe_allow_html=True)

        # Delta summary row
        st.markdown("")
        delta_cols = st.columns(4)

        with delta_cols[0]:
            if first_entry["weight_kg"] and latest_entry["weight_kg"]:
                w_change = latest_entry["weight_kg"] - first_entry["weight_kg"]
                st.metric(
                    "Weight Change",
                    f"{abs(w_change):.1f} kg",
                    delta=f"{'lost' if w_change < 0 else 'gained'}" if w_change != 0 else "no change",
                    delta_color="inverse" if w_change != 0 else "off",
                )

        with delta_cols[1]:
            if first_bmi and latest_bmi:
                bmi_change = latest_bmi - first_bmi
                st.metric(
                    "BMI Change",
                    f"{abs(bmi_change):.1f}",
                    delta=f"{bmi_change:+.1f}",
                    delta_color="inverse",
                )

        with delta_cols[2]:
            first_waist = first_entry.get("waist_cm")
            latest_waist_val = latest_entry.get("waist_cm")
            if pd.notna(first_waist) and pd.notna(latest_waist_val):
                waist_change = latest_waist_val - first_waist
                st.metric(
                    "Waist Change",
                    f"{abs(waist_change):.1f} cm",
                    delta=f"{waist_change:+.1f} cm",
                    delta_color="inverse",
                )

        with delta_cols[3]:
            st.metric("Time Span", f"{days_elapsed} days")

    # ── Data Management ─────────────────────────────────────────────────────────
    st.divider()
    with st.expander("View / Delete Entries"):
        if entries:
            for entry in reversed(entries):
                entry_date = entry["log_date"] if isinstance(entry["log_date"], str) else entry["log_date"].strftime("%Y-%m-%d")
                entry_label = f"{entry_date} — {entry['weight_kg']:.1f} kg" if entry["weight_kg"] else f"{entry_date} — no weight"
                ecol1, ecol2 = st.columns([5, 1])
                with ecol1:
                    parts = [entry_label]
                    if entry.get("waist_cm"):
                        parts.append(f"Waist: {entry['waist_cm']:.1f}")
                    if entry.get("hip_cm"):
                        parts.append(f"Hip: {entry['hip_cm']:.1f}")
                    if entry.get("body_fat_pct"):
                        parts.append(f"BF: {entry['body_fat_pct']:.1f}%")
                    if entry.get("notes"):
                        parts.append(f'"{entry["notes"][:50]}"')
                    st.markdown(" | ".join(parts))
                with ecol2:
                    if st.button("Delete", key=f"del_{entry['id']}", type="secondary"):
                        delete_body_metrics(user_id, entry["id"])
                        st.rerun()
        else:
            st.caption("No entries yet.")

# ══════════════════════════════════════════════════════════════════════════════
# DEXA SCANS TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_dexa:
    render_section_header("DEXA Body Composition", "Track fat, lean mass, and bone density from DEXA scans")

    dexa_history = get_dexa_history(user_id)
    latest_dexa = dexa_history[-1] if dexa_history else None

    # ── Stats Cards ──────────────────────────────────────────────────────
    if latest_dexa:
        dc = st.columns(6)
        with dc[0]:
            v = latest_dexa.get("total_fat_pct")
            st.metric("Body Fat %", f"{v:.1f}%" if v else "--")
        with dc[1]:
            v = latest_dexa.get("lean_mass_g")
            st.metric("Lean Mass", f"{v / 1000:.1f} kg" if v else "--")
        with dc[2]:
            bmd = latest_dexa.get("bmd_g_cm2")
            ts = latest_dexa.get("t_score")
            label = "--"
            if bmd:
                label = f"{bmd:.3f}"
            st.metric("BMD (g/cm2)", label,
                       help=f"T-score: {ts}" if ts else None)
            if ts is not None:
                if ts >= -1.0:
                    badge = ("Normal", "#4CAF50")
                elif ts >= -2.5:
                    badge = ("Osteopenia", "#FF9800")
                else:
                    badge = ("Osteoporosis", "#F44336")
                st.markdown(
                    f"<span style='background:{badge[1]};color:#fff;padding:2px 10px;"
                    f"border-radius:12px;font-size:0.8em'>{badge[0]}</span>",
                    unsafe_allow_html=True,
                )
        with dc[3]:
            v = latest_dexa.get("vat_mass_g")
            st.metric("Visceral Fat", f"{v:.0f} g" if v else "--")
        with dc[4]:
            v = latest_dexa.get("alm_h2")
            st.metric("ALM/h2", f"{v:.2f}" if v else "--",
                       help="Appendicular lean mass / height^2 (kg/m2)")
        with dc[5]:
            v = latest_dexa.get("ag_ratio")
            st.metric("A/G Ratio", f"{v:.2f}" if v else "--",
                       help="Android/Gynoid fat ratio")

    # ── Upload DEXA PDF ──────────────────────────────────────────────────
    st.divider()
    st.markdown("### Upload DEXA Report")

    if "dexa_extracted" not in st.session_state:
        dexa_pdf = st.file_uploader(
            "Drop DEXA PDF here or click Browse",
            type=["pdf"], key="dexa_uploader",
        )
        if dexa_pdf:
            if st.button("Extract DEXA Values with AI", type="primary",
                          use_container_width=True, key="dexa_extract_btn"):
                with st.spinner("Reading DEXA report..."):
                    try:
                        pdf_bytes = dexa_pdf.read()
                        extracted = extract_dexa_from_pdf(pdf_bytes)
                        st.session_state["dexa_extracted"] = extracted
                        st.rerun()
                    except Exception as exc:
                        st.error(f"DEXA extraction failed: {exc}")
    else:
        # Review extracted DEXA values
        ex = st.session_state["dexa_extracted"]
        st.success("DEXA values extracted. Review and save:")

        from datetime import datetime as _dt
        default_date = date.today()
        if ex.get("scan_date"):
            try:
                default_date = _dt.strptime(ex["scan_date"], "%Y-%m-%d").date()
            except ValueError:
                pass

        r1 = st.columns(3)
        with r1[0]:
            dexa_date = st.date_input("Scan Date", value=default_date, key="dexa_scan_date")
        with r1[1]:
            dexa_lab = st.text_input("Lab/Clinic", value=ex.get("lab_name") or "", key="dexa_lab")
        with r1[2]:
            dexa_scanner = st.text_input("Scanner", value=ex.get("scanner_model") or "", key="dexa_scanner")

        r2 = st.columns(4)
        with r2[0]:
            dexa_weight = st.number_input("Weight (kg)", value=ex.get("weight_kg"), format="%.1f", key="dexa_w")
        with r2[1]:
            dexa_fat = st.number_input("Total Fat %", value=ex.get("total_fat_pct"), format="%.1f", key="dexa_fat")
        with r2[2]:
            dexa_lean = st.number_input("Lean Mass (g)", value=ex.get("lean_mass_g"), format="%.0f", key="dexa_lean")
        with r2[3]:
            dexa_bone = st.number_input("Bone Mass (g)", value=ex.get("bone_mass_g"), format="%.0f", key="dexa_bone")

        r3 = st.columns(4)
        with r3[0]:
            dexa_bmd = st.number_input("BMD (g/cm2)", value=ex.get("bmd_g_cm2"), format="%.3f", key="dexa_bmd")
        with r3[1]:
            dexa_ts = st.number_input("T-score", value=ex.get("t_score"), format="%.1f", key="dexa_ts")
        with r3[2]:
            dexa_android = st.number_input("Android Fat %", value=ex.get("android_fat_pct"), format="%.1f", key="dexa_and")
        with r3[3]:
            dexa_gynoid = st.number_input("Gynoid Fat %", value=ex.get("gynoid_fat_pct"), format="%.1f", key="dexa_gyn")

        col_s, col_c = st.columns([3, 1])
        with col_s:
            if st.button("Save DEXA Scan", type="primary", use_container_width=True, key="dexa_save"):
                save_dexa_scan(
                    user_id, dexa_date.isoformat(),
                    lab_name=dexa_lab or None, scanner_model=dexa_scanner or None,
                    weight_kg=dexa_weight, total_fat_pct=dexa_fat,
                    total_fat_g=ex.get("total_fat_g"),
                    lean_mass_g=dexa_lean, bone_mass_g=dexa_bone,
                    bmi=ex.get("bmi"), bmd_g_cm2=dexa_bmd,
                    t_score=dexa_ts, z_score=ex.get("z_score"),
                    vat_mass_g=ex.get("vat_mass_g"),
                    vat_volume_cm3=ex.get("vat_volume_cm3"),
                    vat_area_cm2=ex.get("vat_area_cm2"),
                    android_fat_pct=dexa_android, gynoid_fat_pct=dexa_gynoid,
                    ag_ratio=ex.get("ag_ratio"),
                    left_arm_fat_pct=ex.get("left_arm_fat_pct"),
                    right_arm_fat_pct=ex.get("right_arm_fat_pct"),
                    trunk_fat_pct=ex.get("trunk_fat_pct"),
                    left_leg_fat_pct=ex.get("left_leg_fat_pct"),
                    right_leg_fat_pct=ex.get("right_leg_fat_pct"),
                    left_arm_lean_g=ex.get("left_arm_lean_g"),
                    right_arm_lean_g=ex.get("right_arm_lean_g"),
                    trunk_lean_g=ex.get("trunk_lean_g"),
                    left_leg_lean_g=ex.get("left_leg_lean_g"),
                    right_leg_lean_g=ex.get("right_leg_lean_g"),
                    source="pdf",
                )
                del st.session_state["dexa_extracted"]
                st.toast("DEXA scan saved!")
                st.rerun()
        with col_c:
            if st.button("Cancel", use_container_width=True, key="dexa_cancel"):
                del st.session_state["dexa_extracted"]
                st.rerun()

    # ── Manual Entry Form ────────────────────────────────────────────────
    st.divider()
    with st.expander("Manual DEXA Entry"):
        with st.form("dexa_manual_form", clear_on_submit=True):
            mr1 = st.columns(3)
            with mr1[0]:
                m_date = st.date_input("Scan Date", value=date.today(), key="dexa_m_date")
            with mr1[1]:
                m_lab = st.text_input("Lab/Clinic", key="dexa_m_lab")
            with mr1[2]:
                m_scanner = st.text_input("Scanner Model", key="dexa_m_scanner")

            mr2 = st.columns(4)
            with mr2[0]:
                m_weight = st.number_input("Weight (kg)", value=None, format="%.1f", key="dexa_m_w")
            with mr2[1]:
                m_fat = st.number_input("Total Fat %", value=None, format="%.1f", key="dexa_m_fat")
            with mr2[2]:
                m_lean = st.number_input("Lean Mass (g)", value=None, format="%.0f", key="dexa_m_lean")
            with mr2[3]:
                m_bone = st.number_input("Bone Mass (g)", value=None, format="%.0f", key="dexa_m_bone")

            mr3 = st.columns(4)
            with mr3[0]:
                m_bmd = st.number_input("BMD (g/cm2)", value=None, format="%.3f", key="dexa_m_bmd")
            with mr3[1]:
                m_ts = st.number_input("T-score", value=None, format="%.1f", key="dexa_m_ts")
            with mr3[2]:
                m_android = st.number_input("Android Fat %", value=None, format="%.1f", key="dexa_m_and")
            with mr3[3]:
                m_gynoid = st.number_input("Gynoid Fat %", value=None, format="%.1f", key="dexa_m_gyn")

            m_notes = st.text_area("Notes", key="dexa_m_notes", height=68)

            if st.form_submit_button("Save DEXA Entry", use_container_width=True, type="primary"):
                if m_fat is None and m_weight is None:
                    st.error("Enter at least body fat % or weight.")
                else:
                    save_dexa_scan(
                        user_id, m_date.isoformat(),
                        lab_name=m_lab or None, scanner_model=m_scanner or None,
                        weight_kg=m_weight, total_fat_pct=m_fat,
                        lean_mass_g=m_lean, bone_mass_g=m_bone,
                        bmd_g_cm2=m_bmd, t_score=m_ts,
                        android_fat_pct=m_android, gynoid_fat_pct=m_gynoid,
                        notes=m_notes or None, source="manual",
                    )
                    st.success("DEXA scan saved!")
                    st.rerun()

    # ── Trend Charts ─────────────────────────────────────────────────────
    if len(dexa_history) >= 2:
        dexa_df = pd.DataFrame(dexa_history)
        dexa_df["scan_date"] = pd.to_datetime(dexa_df["scan_date"])

        # Chart 1: Body Composition Over Time
        st.divider()
        st.markdown("### Body Composition Trends")

        fig_bc = go.Figure()
        if dexa_df["total_fat_pct"].notna().any():
            fig_bc.add_trace(go.Scatter(
                x=dexa_df["scan_date"], y=dexa_df["total_fat_pct"],
                mode="lines+markers", name="Body Fat %",
                line=dict(color="#FF5722", width=3),
                marker=dict(size=8),
                hovertemplate="<b>%{x|%b %Y}</b><br>Fat: %{y:.1f}%<extra></extra>",
            ))
        if dexa_df["lean_mass_g"].notna().any():
            fig_bc.add_trace(go.Scatter(
                x=dexa_df["scan_date"], y=dexa_df["lean_mass_g"] / 1000,
                mode="lines+markers", name="Lean Mass (kg)",
                line=dict(color="#2196F3", width=3),
                marker=dict(size=8), yaxis="y2",
                hovertemplate="<b>%{x|%b %Y}</b><br>Lean: %{y:.1f} kg<extra></extra>",
            ))
        if dexa_df["bone_mass_g"].notna().any():
            fig_bc.add_trace(go.Scatter(
                x=dexa_df["scan_date"], y=dexa_df["bone_mass_g"] / 1000,
                mode="lines+markers", name="Bone Mass (kg)",
                line=dict(color="#9C27B0", width=2, dash="dot"),
                marker=dict(size=6), yaxis="y2",
                hovertemplate="<b>%{x|%b %Y}</b><br>Bone: %{y:.2f} kg<extra></extra>",
            ))
        fig_bc.update_layout(
            **PLOTLY_LAYOUT_DEFAULTS, height=420,
            yaxis=dict(title="Body Fat %", showgrid=True, gridcolor=A["chart_grid"]),
            yaxis2=dict(title="Mass (kg)", overlaying="y", side="right", showgrid=False),
            xaxis=dict(title="Scan Date", tickformat="%b %Y"),
            hovermode="x unified",
        )
        st.plotly_chart(fig_bc, use_container_width=True)

        # Chart 2: Bone Density with T-score zones
        if dexa_df["bmd_g_cm2"].notna().any():
            st.markdown("### Bone Density")
            fig_bone = go.Figure()
            fig_bone.add_trace(go.Scatter(
                x=dexa_df["scan_date"], y=dexa_df["bmd_g_cm2"],
                mode="lines+markers", name="BMD",
                line=dict(color="#4CAF50", width=3),
                marker=dict(size=10),
                hovertemplate="<b>%{x|%b %Y}</b><br>BMD: %{y:.3f} g/cm2<extra></extra>",
            ))
            fig_bone.update_layout(
                **PLOTLY_LAYOUT_DEFAULTS, height=350,
                yaxis=dict(title="BMD (g/cm2)", showgrid=True, gridcolor=A["chart_grid"]),
                xaxis=dict(title="Scan Date", tickformat="%b %Y"),
            )
            st.plotly_chart(fig_bone, use_container_width=True)

        # Chart 3: Regional Fat Distribution
        has_regional = dexa_df[["left_arm_fat_pct", "trunk_fat_pct", "left_leg_fat_pct"]].notna().any().any()
        if has_regional:
            st.markdown("### Regional Fat Distribution")
            fig_reg = go.Figure()
            regions = [
                ("left_arm_fat_pct", "L Arm", "#FF9800"),
                ("right_arm_fat_pct", "R Arm", "#FFC107"),
                ("trunk_fat_pct", "Trunk", "#F44336"),
                ("left_leg_fat_pct", "L Leg", "#2196F3"),
                ("right_leg_fat_pct", "R Leg", "#03A9F4"),
            ]
            for col_name, label, color in regions:
                if dexa_df[col_name].notna().any():
                    fig_reg.add_trace(go.Bar(
                        x=dexa_df["scan_date"].dt.strftime("%b %Y"),
                        y=dexa_df[col_name], name=label,
                        marker_color=color,
                    ))
            fig_reg.update_layout(
                **PLOTLY_LAYOUT_DEFAULTS, height=380,
                barmode="group", bargap=0.15, bargroupgap=0.1,
                yaxis=dict(title="Fat %", showgrid=True, gridcolor=A["chart_grid"]),
                xaxis=dict(title="Scan Date"),
            )
            st.plotly_chart(fig_reg, use_container_width=True)

    elif dexa_history:
        st.info("Upload a second DEXA scan to see trend charts.")
    else:
        st.info("No DEXA scans yet. Upload a PDF or log manually above.")

    # ── Scan History / Delete ────────────────────────────────────────────
    if dexa_history:
        st.divider()
        with st.expander("View / Delete DEXA Scans"):
            for scan in reversed(dexa_history):
                s_date = scan["scan_date"]
                fat = scan.get("total_fat_pct")
                lean = scan.get("lean_mass_g")
                bmd_val = scan.get("bmd_g_cm2")
                parts = [f"**{s_date}**"]
                if fat:
                    parts.append(f"Fat: {fat:.1f}%")
                if lean:
                    parts.append(f"Lean: {lean / 1000:.1f} kg")
                if bmd_val:
                    parts.append(f"BMD: {bmd_val:.3f}")
                if scan.get("lab_name"):
                    parts.append(scan["lab_name"])
                sc1, sc2 = st.columns([5, 1])
                with sc1:
                    st.markdown(" | ".join(parts))
                with sc2:
                    if st.button("Delete", key=f"del_dexa_{scan['id']}", type="secondary"):
                        delete_dexa_scan(user_id, scan["id"])
                        st.rerun()
