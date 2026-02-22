"""Nutrition Logger — Meal tracking with Noom-style color coding, plant score, and calorie counter."""

import streamlit as st
import plotly.graph_objects as go
from datetime import date, timedelta
from components.custom_theme import APPLE, render_hero_banner, render_section_header
from services.nutrition_service import (
    log_meal,
    get_meals_for_date,
    delete_meal,
    get_daily_summary,
    get_nutrition_trends,
    get_nutrition_averages,
)

A = APPLE
user_id = st.session_state.user_id

render_hero_banner(
    "Nutrition Logger",
    "Track meals with color coding, plant diversity, fiber, and calorie counting. Inspired by ACLM guidelines and the science of plant-forward eating."
)

COLOR_INFO = {
    "green": {"label": "Green", "color": "#30D158", "icon": "&#127811;",
              "desc": "Whole, unprocessed plant foods (fruits, vegetables, whole grains, legumes)"},
    "yellow": {"label": "Yellow", "color": "#FFD60A", "icon": "&#127828;",
               "desc": "Lean proteins, dairy, processed grains, healthy fats"},
    "red": {"label": "Red", "color": "#FF453A", "icon": "&#127853;",
            "desc": "Ultra-processed foods, added sugars, fried foods, desserts"},
}

tab_log, tab_today, tab_trends, tab_calories = st.tabs(["Log Meal", "Today's Summary", "Trends", "Calorie Tracker"])

# ══════════════════════════════════════════════════════════════════════════
# Tab 1: Log Meal
# ══════════════════════════════════════════════════════════════════════════
with tab_log:
    render_section_header("Log a Meal")

    # Color guide
    guide_html = ""
    for ck, ci in COLOR_INFO.items():
        guide_html += (
            f'<span style="display:inline-flex;align-items:center;gap:4px;margin-right:16px">'
            f'<span style="width:10px;height:10px;border-radius:50%;background:{ci["color"]};'
            f'display:inline-block"></span>'
            f'<span style="font-size:12px;color:{A["label_secondary"]}">'
            f'{ci["icon"]} {ci["label"]}: {ci["desc"]}</span>'
            f'</span>'
        )
    st.markdown(
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_md"]};padding:12px;margin-bottom:16px">'
        f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-bottom:6px">'
        f'Color Guide</div>'
        f'<div style="display:flex;flex-direction:column;gap:4px">{guide_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.form("meal_log_form"):
        log_date = st.date_input("Date", value=date.today())
        meal_type = st.selectbox("Meal Type", ["breakfast", "lunch", "dinner", "snack"])
        description = st.text_area("What did you eat?", placeholder="e.g., Grilled salmon with quinoa and roasted broccoli")

        color = st.radio(
            "Food Color Category",
            ["green", "yellow", "red"],
            format_func=lambda c: f"{COLOR_INFO[c]['icon']} {COLOR_INFO[c]['label']} — {COLOR_INFO[c]['desc']}",
            horizontal=False,
        )

        st.markdown("**Plant Servings** (1 serving ≈ 1/2 cup cooked or 1 cup raw)")
        col1, col2, col3 = st.columns(3)
        with col1:
            fruit = st.number_input("Fruit", min_value=0, max_value=10, value=0)
            legumes = st.number_input("Legumes", min_value=0, max_value=10, value=0)
        with col2:
            veg = st.number_input("Vegetables", min_value=0, max_value=10, value=0)
            nuts = st.number_input("Nuts/Seeds", min_value=0, max_value=10, value=0)
        with col3:
            grains = st.number_input("Whole Grains", min_value=0, max_value=10, value=0)

        total_plant = fruit + veg + grains + legumes + nuts

        fiber = st.number_input("Estimated fiber (grams)", min_value=0, max_value=100, value=0,
                                help="A serving of vegetables ≈ 3-5g fiber, legumes ≈ 7-8g, whole grains ≈ 3g")
        water = st.number_input("Water glasses with this meal", min_value=0, max_value=10, value=0)
        notes = st.text_input("Notes (optional)")

        submitted = st.form_submit_button("Log Meal", use_container_width=True)
        if submitted:
            if not description:
                st.warning("Please describe what you ate.")
            else:
                log_meal(
                    user_id=user_id,
                    log_date=log_date.isoformat(),
                    meal_type=meal_type,
                    description=description,
                    color_category=color,
                    plant_servings=total_plant,
                    fruit_servings=fruit,
                    vegetable_servings=veg,
                    whole_grain_servings=grains,
                    legume_servings=legumes,
                    nut_seed_servings=nuts,
                    fiber_grams=fiber,
                    water_glasses=water,
                    notes=notes if notes else None,
                )
                st.toast(f"Meal logged! ({COLOR_INFO[color]['label']})")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# Tab 2: Today's Summary
# ══════════════════════════════════════════════════════════════════════════
with tab_today:
    view_date = st.date_input("View date", value=date.today(), key="view_date")
    date_str = view_date.isoformat()

    meals = get_meals_for_date(user_id, date_str)
    summary = get_daily_summary(user_id, date_str)

    if not meals:
        st.info("No meals logged for this date.")
    else:
        # Score and summary cards
        if summary:
            ps = summary.get("plant_score", 0)
            ns = summary.get("nutrition_score", 0)
            ps_color = "#30D158" if ps >= 70 else "#FFD60A" if ps >= 40 else "#FF453A"
            ns_color = "#30D158" if ns >= 70 else "#FFD60A" if ns >= 40 else "#FF453A"

            score_html = (
                f'<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px">'
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_lg"]};padding:16px;flex:1;min-width:120px;text-align:center">'
                f'<div style="font-family:{A["font_display"]};font-size:28px;'
                f'font-weight:700;color:{ps_color}">{ps}</div>'
                f'<div style="font-size:10px;font-weight:600;text-transform:uppercase;'
                f'letter-spacing:0.06em;color:{A["label_tertiary"]}">Plant Score</div>'
                f'</div>'
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_lg"]};padding:16px;flex:1;min-width:120px;text-align:center">'
                f'<div style="font-family:{A["font_display"]};font-size:28px;'
                f'font-weight:700;color:{ns_color}">{ns}</div>'
                f'<div style="font-size:10px;font-weight:600;text-transform:uppercase;'
                f'letter-spacing:0.06em;color:{A["label_tertiary"]}">Nutrition Score</div>'
                f'</div>'
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_lg"]};padding:16px;flex:1;min-width:120px;text-align:center">'
                f'<div style="font-family:{A["font_display"]};font-size:28px;'
                f'font-weight:700;color:{A["label_primary"]}">{summary.get("total_plant_servings", 0)}</div>'
                f'<div style="font-size:10px;font-weight:600;text-transform:uppercase;'
                f'letter-spacing:0.06em;color:{A["label_tertiary"]}">Plant Servings</div>'
                f'</div>'
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-radius:{A["radius_lg"]};padding:16px;flex:1;min-width:120px;text-align:center">'
                f'<div style="font-family:{A["font_display"]};font-size:28px;'
                f'font-weight:700;color:{A["label_primary"]}">{summary.get("total_fiber_grams", 0)}g</div>'
                f'<div style="font-size:10px;font-weight:600;text-transform:uppercase;'
                f'letter-spacing:0.06em;color:{A["label_tertiary"]}">Fiber</div>'
                f'</div>'
                f'</div>'
            )
            st.markdown(score_html, unsafe_allow_html=True)

            # Color breakdown bar
            g = summary.get("green_count", 0)
            y = summary.get("yellow_count", 0)
            r = summary.get("red_count", 0)
            total = g + y + r
            if total > 0:
                gp = g / total * 100
                yp = y / total * 100
                rp = r / total * 100
                bar_html = (
                    f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                    f'border-radius:{A["radius_md"]};padding:12px;margin-bottom:16px">'
                    f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
                    f'letter-spacing:0.06em;color:{A["label_tertiary"]};margin-bottom:8px">'
                    f'Color Balance</div>'
                    f'<div style="display:flex;height:20px;border-radius:10px;overflow:hidden">'
                    f'<div style="width:{gp}%;background:#30D158"></div>'
                    f'<div style="width:{yp}%;background:#FFD60A"></div>'
                    f'<div style="width:{rp}%;background:#FF453A"></div>'
                    f'</div>'
                    f'<div style="display:flex;justify-content:space-between;margin-top:6px">'
                    f'<span style="font-size:11px;color:#30D158">{g} green</span>'
                    f'<span style="font-size:11px;color:#FFD60A">{y} yellow</span>'
                    f'<span style="font-size:11px;color:#FF453A">{r} red</span>'
                    f'</div>'
                    f'</div>'
                )
                st.markdown(bar_html, unsafe_allow_html=True)

        # Meal list
        render_section_header("Meals", f"{len(meals)} entries")
        for m in meals:
            ci = COLOR_INFO.get(m["color_category"], COLOR_INFO["yellow"])
            meal_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-left:3px solid {ci["color"]};'
                f'border-radius:{A["radius_md"]};padding:12px 16px;margin-bottom:6px">'
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'<div>'
                f'<span style="font-size:11px;font-weight:600;text-transform:uppercase;'
                f'color:{ci["color"]}">{m["meal_type"]}</span>'
                f'<div style="font-size:13px;color:{A["label_primary"]};margin-top:2px">'
                f'{m["description"]}</div>'
                f'</div>'
                f'<div style="text-align:right;font-size:11px;color:{A["label_tertiary"]}">'
                f'{m.get("plant_servings", 0)} plants &middot; {m.get("fiber_grams", 0)}g fiber'
                f'</div>'
                f'</div>'
                f'</div>'
            )
            st.markdown(meal_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Tab 3: Trends
# ══════════════════════════════════════════════════════════════════════════
with tab_trends:
    render_section_header("Nutrition Trends", "Your nutrition patterns over time")

    avgs = get_nutrition_averages(user_id, days=30)
    if not avgs or not avgs.get("log_count"):
        st.caption("Not enough data for trends. Keep logging meals!")
    else:
        # Average stats
        stats_html = (
            f'<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px">'
            f'<div style="background:{A["glass_bg"]};border:1px solid {A["glass_border"]};'
            f'border-radius:{A["radius_lg"]};padding:14px;flex:1;min-width:100px;text-align:center">'
            f'<div style="font-family:{A["font_display"]};font-size:20px;'
            f'font-weight:700;color:#30D158">{avgs["avg_plant_score"]:.0f}</div>'
            f'<div style="font-size:10px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:0.06em;color:{A["label_tertiary"]}">Avg Plant Score</div>'
            f'</div>'
            f'<div style="background:{A["glass_bg"]};border:1px solid {A["glass_border"]};'
            f'border-radius:{A["radius_lg"]};padding:14px;flex:1;min-width:100px;text-align:center">'
            f'<div style="font-family:{A["font_display"]};font-size:20px;'
            f'font-weight:700;color:{A["blue"]}">{avgs["avg_plants"]:.1f}</div>'
            f'<div style="font-size:10px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:0.06em;color:{A["label_tertiary"]}">Avg Plants/Day</div>'
            f'</div>'
            f'<div style="background:{A["glass_bg"]};border:1px solid {A["glass_border"]};'
            f'border-radius:{A["radius_lg"]};padding:14px;flex:1;min-width:100px;text-align:center">'
            f'<div style="font-family:{A["font_display"]};font-size:20px;'
            f'font-weight:700;color:{A["orange"]}">{avgs["avg_fiber"]:.0f}g</div>'
            f'<div style="font-size:10px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:0.06em;color:{A["label_tertiary"]}">Avg Fiber/Day</div>'
            f'</div>'
            f'</div>'
        )
        st.markdown(stats_html, unsafe_allow_html=True)

        # Chart
        trends = get_nutrition_trends(user_id, days=30)
        if trends:
            dates = [t["summary_date"] for t in trends]
            plant_scores = [t.get("plant_score", 0) for t in trends]
            plants = [t.get("total_plant_servings", 0) for t in trends]

            metric = st.selectbox("Metric", ["Plant Score", "Plant Servings", "Fiber (g)"], key="nut_metric")

            if metric == "Plant Score":
                y_data = plant_scores
                color = "#30D158"
                y_title = "Score"
            elif metric == "Plant Servings":
                y_data = plants
                color = "#0A84FF"
                y_title = "Servings"
            else:
                y_data = [t.get("total_fiber_grams", 0) for t in trends]
                color = "#FF9F0A"
                y_title = "Grams"

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=dates, y=y_data,
                marker_color=color, opacity=0.8,
                hovertemplate="%{y}<br>%{x}<extra></extra>",
            ))

            if metric == "Plant Servings":
                fig.add_hline(y=10, line_dash="dash", line_color="#30D158", opacity=0.5,
                              annotation_text="10/day target")
            elif metric == "Fiber (g)":
                fig.add_hline(y=30, line_dash="dash", line_color="#30D158", opacity=0.5,
                              annotation_text="30g target")

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#1C1C1E",
                font=dict(family=A["font_text"]),
                margin=dict(l=40, r=20, t=30, b=40),
                height=300,
                xaxis=dict(gridcolor="rgba(84,84,88,0.3)"),
                yaxis=dict(title=y_title, gridcolor="rgba(84,84,88,0.3)"),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════
# Tab 4: Calorie Tracker
# ══════════════════════════════════════════════════════════════════════════
with tab_calories:
    from services.calorie_service import (
        get_all_foods, log_food_item, delete_food_item,
        get_food_items_for_date, get_calorie_summary,
        get_calorie_targets, set_calorie_targets, get_calorie_trends,
    )
    from components.calorie_display import (
        render_calorie_summary_card, render_macro_donut, render_food_item_row,
    )

    render_section_header("Calorie Tracker", "Log foods and track daily macros")

    # ── Targets expander ──────────────────────────────────────────────────
    targets = get_calorie_targets(user_id)
    with st.expander("Set Calorie/Macro Targets"):
        with st.form("calorie_targets_form"):
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                cal_target = st.number_input("Daily Calories (kcal)", min_value=800, max_value=5000,
                                             value=int(targets.get("calorie_target", targets.get("calories", 2000))))
                pro_target = st.number_input("Protein (g)", min_value=10, max_value=300,
                                             value=int(targets.get("protein_target_g", targets.get("protein_g", 50))))
            with col_t2:
                carb_target = st.number_input("Carbs (g)", min_value=20, max_value=600,
                                              value=int(targets.get("carbs_target_g", targets.get("carbs_g", 250))))
                fat_target = st.number_input("Fat (g)", min_value=10, max_value=200,
                                             value=int(targets.get("fat_target_g", targets.get("fat_g", 65))))
            if st.form_submit_button("Save Targets", use_container_width=True):
                set_calorie_targets(user_id, cal_target, pro_target, carb_target, fat_target)
                st.toast("Targets saved!")
                st.rerun()

    # ── Add food form ─────────────────────────────────────────────────────
    cal_date = st.date_input("Date", value=date.today(), key="cal_date")
    cal_date_str = cal_date.isoformat()

    all_foods = get_all_foods()
    if not all_foods:
        st.warning("Food database is empty. Please restart the app to seed it.")
    else:
        food_options = {f"{fd['name']} ({fd['category']}) — {fd['calories']} cal/{fd['serving_size']}{fd['serving_unit']}": fd["id"] for fd in all_foods}
        with st.form("add_food_form"):
            food_label = st.selectbox("Search food", options=list(food_options.keys()))
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                servings = st.number_input("Servings", min_value=0.25, max_value=10.0, value=1.0, step=0.25)
            with col_f2:
                meal_type = st.selectbox("Meal", ["breakfast", "lunch", "dinner", "snack"], key="cal_meal")
            if st.form_submit_button("Add Food", use_container_width=True):
                food_id = food_options[food_label]
                result = log_food_item(user_id, food_id, cal_date_str, meal_type, servings)
                if result:
                    st.toast(f"Added {result['food_name']} — {result['calories']:.0f} cal")
                    st.rerun()

    # ── Daily summary ─────────────────────────────────────────────────────
    cal_summary = get_calorie_summary(user_id, cal_date_str)
    targets = get_calorie_targets(user_id)

    col_bars, col_donut = st.columns([3, 2])
    with col_bars:
        render_calorie_summary_card(cal_summary, targets)
    with col_donut:
        if cal_summary:
            render_macro_donut(
                cal_summary["total_protein_g"],
                cal_summary["total_carbs_g"],
                cal_summary["total_fat_g"],
            )

    # ── Food log ──────────────────────────────────────────────────────────
    food_items = get_food_items_for_date(user_id, cal_date_str)
    if food_items:
        render_section_header("Food Log", f"{len(food_items)} items")
        for item in food_items:
            col_item, col_del = st.columns([9, 1])
            with col_item:
                render_food_item_row(item)
            with col_del:
                if st.button("X", key=f"del_food_{item['id']}", help="Remove"):
                    delete_food_item(item["id"], user_id)
                    st.rerun()

    # ── Calorie trends ────────────────────────────────────────────────────
    cal_trend_data = get_calorie_trends(user_id, days=30)
    if cal_trend_data and len(cal_trend_data) >= 2:
        render_section_header("Calorie Trends", "Last 30 days")
        t_dates = [t["summary_date"] for t in cal_trend_data]
        t_cals = [t["total_calories"] for t in cal_trend_data]
        fig_cal = go.Figure()
        fig_cal.add_trace(go.Bar(
            x=t_dates, y=t_cals, marker_color="#FF9F0A", opacity=0.8,
            hovertemplate="%{y:.0f} cal<br>%{x}<extra></extra>",
        ))
        cal_tgt = targets.get("calorie_target", targets.get("calories", 2000))
        fig_cal.add_hline(y=cal_tgt, line_dash="dash", line_color="#30D158", opacity=0.5,
                          annotation_text=f"{cal_tgt} cal target")
        fig_cal.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#1C1C1E",
            font=dict(family=A["font_text"]),
            margin=dict(l=40, r=20, t=30, b=40),
            height=250,
            xaxis=dict(gridcolor="rgba(84,84,88,0.3)"),
            yaxis=dict(title="Calories", gridcolor="rgba(84,84,88,0.3)"),
            showlegend=False,
        )
        st.plotly_chart(fig_cal, use_container_width=True)
