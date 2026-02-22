"""Calorie tracking display components — progress bars, donut chart, food rows."""

import streamlit as st
import plotly.graph_objects as go
from components.custom_theme import APPLE

A = APPLE


def render_calorie_progress(current, target, label, color="#0A84FF", unit=""):
    """Render a single calorie/macro progress bar with label and values."""
    pct = min(100, (current / target * 100)) if target > 0 else 0
    over = current > target
    bar_color = "#FF453A" if over else color
    display_val = f"{current:.0f}" if current == int(current) else f"{current:.1f}"
    target_val = f"{target:.0f}" if target == int(target) else f"{target:.1f}"

    html = (
        f'<div style="margin-bottom:12px">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px">'
        f'<div style="font-size:12px;font-weight:600;color:{A["label_secondary"]}">{label}</div>'
        f'<div style="font-size:13px;font-weight:700;color:{bar_color}">'
        f'{display_val}<span style="color:{A["label_tertiary"]};font-weight:400">/{target_val}{unit}</span></div>'
        f'</div>'
        f'<div style="background:{A["fill_tertiary"]};border-radius:9999px;height:8px;overflow:hidden">'
        f'<div style="background:{bar_color};width:{min(pct, 100):.1f}%;height:100%;border-radius:9999px;'
        f'transition:width 0.3s ease"></div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_macro_donut(protein_g, carbs_g, fat_g):
    """Render a Plotly donut chart showing macro breakdown."""
    total_cal = protein_g * 4 + carbs_g * 4 + fat_g * 9
    if total_cal == 0:
        st.caption("No food logged yet.")
        return

    fig = go.Figure(data=[go.Pie(
        labels=["Protein", "Carbs", "Fat"],
        values=[protein_g * 4, carbs_g * 4, fat_g * 9],
        hole=0.6,
        marker=dict(colors=["#0A84FF", "#30D158", "#FF375F"]),
        textinfo="percent",
        textfont=dict(size=12, color="white"),
        hovertemplate="%{label}: %{value:.0f} cal (%{percent})<extra></extra>",
    )])

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=A["font_text"]),
        margin=dict(l=10, r=10, t=10, b=10),
        height=200,
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.15,
            xanchor="center", x=0.5, font=dict(size=11),
        ),
        annotations=[dict(
            text=f"<b>{total_cal:.0f}</b><br>cal",
            x=0.5, y=0.5, font_size=16, showarrow=False,
            font=dict(color="white", family=A["font_display"]),
        )],
    )
    st.plotly_chart(fig, use_container_width=True)


def render_food_item_row(item):
    """Render a single food log item card."""
    color_map = {"green": "#30D158", "yellow": "#FFD60A", "red": "#FF453A"}
    border_color = color_map.get(item.get("color_category"), A["separator"])
    servings_str = f"{item['servings']:.1f}" if item["servings"] != int(item["servings"]) else f"{int(item['servings'])}"

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-left:3px solid {border_color};border-radius:{A["radius_md"]};'
        f'padding:10px 14px;margin-bottom:6px;display:flex;justify-content:space-between;'
        f'align-items:center;flex-wrap:wrap;gap:8px">'
        f'<div style="flex:1;min-width:140px">'
        f'<div style="font-size:13px;font-weight:600;color:{A["label_primary"]}">{item["food_name"]}</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]}">'
        f'{servings_str} serving{"s" if item["servings"] != 1 else ""} &middot; {item["meal_type"]}</div>'
        f'</div>'
        f'<div style="display:flex;gap:12px;font-size:11px;color:{A["label_secondary"]}">'
        f'<span style="color:#FF9F0A;font-weight:600">{item["calories"]:.0f} cal</span>'
        f'<span>P:{item["protein_g"]:.0f}g</span>'
        f'<span>C:{item["carbs_g"]:.0f}g</span>'
        f'<span>F:{item["fat_g"]:.0f}g</span>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_calorie_summary_card(summary, targets):
    """Render the daily calorie summary with all 4 progress bars."""
    if not summary:
        st.caption("No food logged today. Add foods to see your daily summary.")
        return

    from config.food_data import MACRO_COLORS

    cal_target = targets.get("calorie_target", targets.get("calories", 2000))
    pro_target = targets.get("protein_target_g", targets.get("protein_g", 50))
    carb_target = targets.get("carbs_target_g", targets.get("carbs_g", 250))
    fat_target = targets.get("fat_target_g", targets.get("fat_g", 65))

    render_calorie_progress(summary["total_calories"], cal_target, "Calories", MACRO_COLORS["calories"], " kcal")
    render_calorie_progress(summary["total_protein_g"], pro_target, "Protein", MACRO_COLORS["protein"], "g")
    render_calorie_progress(summary["total_carbs_g"], carb_target, "Carbs", MACRO_COLORS["carbs"], "g")
    render_calorie_progress(summary["total_fat_g"], fat_target, "Fat", MACRO_COLORS["fat"], "g")
