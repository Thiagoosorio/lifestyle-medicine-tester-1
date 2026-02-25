"""Display components for SIBO & FODMAP Tracker: disclaimer, symptom charts, badges, correlations."""

import streamlit as st
from components.custom_theme import APPLE
from config.sibo_data import (
    SIBO_DISCLAIMER, GI_SYMPTOMS, FODMAP_GROUPS, FODMAP_PHASES,
    SIBO_DIET_TYPES, CORRELATION_STRENGTH,
)

A = APPLE


# ══════════════════════════════════════════════════════════════════════════════
# DISCLAIMER — shown on every tab
# ══════════════════════════════════════════════════════════════════════════════

def render_sibo_disclaimer():
    """Render the medical disclaimer banner (orange border)."""
    html = (
        f'<div style="background:rgba(255,159,10,0.06);border:1px solid rgba(255,159,10,0.3);'
        f'border-left:3px solid {A["orange"]};border-radius:{A["radius_md"]};'
        f'padding:12px 16px;margin-bottom:16px">'
        f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.05em;color:{A["orange"]};margin-bottom:4px">'
        f'&#9888; Medical Disclaimer</div>'
        f'<div style="font-size:12px;line-height:18px;color:{A["label_secondary"]}">'
        f'{SIBO_DISCLAIMER}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SYMPTOM DISPLAY
# ══════════════════════════════════════════════════════════════════════════════

def render_symptom_summary(averages):
    """Render horizontal stat cards for symptom averages."""
    if not averages:
        st.caption("No symptom data yet.")
        return

    cards = ""
    for key in ["bloating", "abdominal_pain", "gas", "nausea", "fatigue", "overall"]:
        sym = GI_SYMPTOMS.get(key, {})
        label = sym.get("label", key.replace("_", " ").title())
        if key == "overall":
            label = "Overall"
        val = averages.get(key, 0)
        max_val = sym.get("max", 10) if key != "overall" else 10
        color = A["green"] if val <= max_val * 0.3 else (A["orange"] if val <= max_val * 0.6 else A["red"])
        cards += (
            f'<div style="flex:1;min-width:80px;background:{A["bg_elevated"]};'
            f'border:1px solid {A["separator"]};border-radius:{A["radius_md"]};'
            f'padding:10px;text-align:center">'
            f'<div style="font-family:{A["font_display"]};font-size:18px;'
            f'font-weight:700;color:{color}">{val}</div>'
            f'<div style="font-size:10px;color:{A["label_tertiary"]}">{label}</div>'
            f'</div>'
        )

    html = (
        f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">'
        f'{cards}</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_symptom_chart(history):
    """Render a Plotly line chart of symptom scores over time."""
    if not history or len(history) < 2:
        st.caption("Log at least 2 days of symptoms to see trends.")
        return

    import plotly.graph_objects as go

    data = list(reversed(history))
    dates = [d["log_date"] for d in data]

    fig = go.Figure()
    symptom_configs = [
        ("overall_score", "Overall", A["teal"], 3),
        ("bloating", "Bloating", "#FF9F0A", 1.5),
        ("abdominal_pain", "Pain", "#FF453A", 1.5),
        ("gas", "Gas", "#BF5AF2", 1.5),
        ("nausea", "Nausea", "#5E5CE6", 1.5),
        ("fatigue", "Fatigue", "#64D2FF", 1.5),
    ]

    for key, label, color, width in symptom_configs:
        values = [d.get(key) for d in data]
        if all(v is None for v in values):
            continue
        fig.add_trace(go.Scatter(
            x=dates, y=values, name=label, mode="lines+markers",
            line=dict(color=color, width=width),
            marker=dict(size=4, color=color),
            hovertemplate=f"{label}: %{{y}}<br>%{{x}}<extra></extra>",
        ))

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=A["chart_bg"],
        font=dict(family=A["font_text"], color=A["chart_text"]),
        margin=dict(l=30, r=10, t=10, b=30),
        height=250,
        xaxis=dict(gridcolor=A["chart_grid"]),
        yaxis=dict(title="Score", gridcolor=A["chart_grid"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=10)),
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# FODMAP BADGES & FOOD LOG
# ══════════════════════════════════════════════════════════════════════════════

def render_fodmap_badge(rating):
    """Render a small colored badge for FODMAP rating."""
    colors = {"low": "#30D158", "moderate": "#FF9F0A", "high": "#FF453A"}
    color = colors.get(rating, A["label_tertiary"])
    html = (
        f'<span style="display:inline-block;font-size:10px;font-weight:600;'
        f'padding:2px 8px;border-radius:4px;background:{color}20;color:{color};'
        f'text-transform:uppercase;letter-spacing:0.04em">{rating or "unknown"}</span>'
    )
    return html


def render_food_log_row(entry):
    """Render a compact food log row with FODMAP badges."""
    badge = render_fodmap_badge(entry.get("fodmap_rating"))
    groups = entry.get("fodmap_groups_list", [])
    group_tags = ""
    for g in groups:
        ginfo = FODMAP_GROUPS.get(g, {})
        gc = ginfo.get("color", A["label_tertiary"])
        gl = ginfo.get("label", g)
        group_tags += (
            f'<span style="font-size:9px;padding:1px 5px;border-radius:3px;'
            f'background:{gc}15;color:{gc};margin-left:4px">{gl}</span>'
        )

    serving = ""
    if entry.get("serving_size") and entry.get("serving_unit"):
        serving = f'{entry["serving_size"]} {entry["serving_unit"]}'

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_sm"]};padding:10px 14px;margin-bottom:4px;'
        f'display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap">'
        f'<div>'
        f'<span style="font-size:13px;font-weight:600;color:{A["label_primary"]}">'
        f'{entry["food_name"]}</span>'
        f'<span style="font-size:11px;color:{A["label_tertiary"]};margin-left:8px">'
        f'{entry.get("meal_type", "")}</span>'
        f'{group_tags}'
        f'</div>'
        f'<div style="display:flex;align-items:center;gap:8px">'
        f'<span style="font-size:11px;color:{A["label_tertiary"]}">{serving}</span>'
        f'{badge}'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_fodmap_exposure_bar(exposure):
    """Render a horizontal bar showing daily FODMAP group exposure."""
    if not exposure or all(v == 0 for v in exposure.values()):
        return

    max_exp = max(exposure.values()) if max(exposure.values()) > 0 else 1
    bars = ""
    for group, val in exposure.items():
        ginfo = FODMAP_GROUPS.get(group, {})
        color = ginfo.get("color", A["label_tertiary"])
        label = ginfo.get("label", group)
        pct = min(val / max_exp * 100, 100) if max_exp > 0 else 0
        bars += (
            f'<div style="margin-bottom:4px">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:2px">'
            f'<span style="font-size:11px;color:{A["label_secondary"]}">{label}</span>'
            f'<span style="font-size:11px;color:{A["label_tertiary"]}">{val:.1f}</span>'
            f'</div>'
            f'<div style="background:{A["separator"]};border-radius:3px;height:6px;overflow:hidden">'
            f'<div style="background:{color};width:{pct}%;height:100%;border-radius:3px"></div>'
            f'</div>'
            f'</div>'
        )

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_md"]};padding:12px 16px;margin-bottom:12px">'
        f'<div style="font-size:12px;font-weight:600;color:{A["label_secondary"]};'
        f'margin-bottom:8px">Daily FODMAP Exposure</div>'
        f'{bars}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PHASE INDICATOR
# ══════════════════════════════════════════════════════════════════════════════

def render_phase_indicator(phase_data):
    """Render the current phase card with days in phase."""
    if not phase_data:
        html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-radius:{A["radius_md"]};padding:16px;margin-bottom:12px;text-align:center">'
            f'<div style="font-size:13px;color:{A["label_tertiary"]}">'
            f'No active Low-FODMAP phase. Start one below.</div>'
            f'</div>'
        )
        st.markdown(html, unsafe_allow_html=True)
        return

    phase_key = phase_data["phase"]
    phase_info = FODMAP_PHASES.get(phase_key, {})
    color = phase_info.get("color", A["teal"])
    label = phase_info.get("label", phase_key.title())

    from datetime import date
    started = date.fromisoformat(phase_data["started_date"])
    days_in = (date.today() - started).days

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-left:4px solid {color};border-radius:{A["radius_lg"]};'
        f'padding:16px 20px;margin-bottom:12px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'<div>'
        f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.05em;color:{color};margin-bottom:4px">Current Phase</div>'
        f'<div style="font-family:{A["font_display"]};font-size:20px;font-weight:700;'
        f'color:{A["label_primary"]}">{label}</div>'
        f'<div style="font-size:12px;color:{A["label_tertiary"]};margin-top:2px">'
        f'{phase_info.get("description", "")}</div>'
        f'</div>'
        f'<div style="text-align:center">'
        f'<div style="font-family:{A["font_display"]};font-size:28px;font-weight:700;'
        f'color:{A["label_primary"]}">{days_in}</div>'
        f'<div style="font-size:10px;color:{A["label_tertiary"]}">days</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# REINTRODUCTION & TOLERANCE
# ══════════════════════════════════════════════════════════════════════════════

def render_tolerance_summary(summary):
    """Render per-FODMAP-group tolerance badges."""
    if not summary:
        st.caption("No reintroduction challenges completed yet.")
        return

    items = ""
    for group, data in summary.items():
        ginfo = FODMAP_GROUPS.get(group, {})
        glabel = ginfo.get("label", group)
        tol = data["tolerance"]
        tol_colors = {
            "tolerated": "#30D158",
            "partial": "#FF9F0A",
            "not_tolerated": "#FF453A",
        }
        tol_labels = {
            "tolerated": "Tolerated",
            "partial": "Partial",
            "not_tolerated": "Not Tolerated",
        }
        tc = tol_colors.get(tol, A["label_tertiary"])
        tl = tol_labels.get(tol, tol)

        items += (
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:8px 0;border-bottom:1px solid {A["separator"]}">'
            f'<div>'
            f'<span style="font-size:13px;font-weight:600;color:{A["label_primary"]}">'
            f'{glabel}</span>'
            f'<span style="font-size:11px;color:{A["label_tertiary"]};margin-left:8px">'
            f'{data["food"]}</span>'
            f'</div>'
            f'<span style="font-size:10px;font-weight:600;padding:2px 8px;border-radius:4px;'
            f'background:{tc}20;color:{tc}">{tl}</span>'
            f'</div>'
        )

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_md"]};padding:12px 16px;margin-bottom:12px">'
        f'<div style="font-size:12px;font-weight:600;color:{A["label_secondary"]};'
        f'margin-bottom:4px">Tolerance Results</div>'
        f'{items}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_reintro_timeline(challenges):
    """Render a compact timeline of reintroduction challenges."""
    if not challenges:
        return

    items = ""
    for c in challenges[:10]:
        ginfo = FODMAP_GROUPS.get(c["fodmap_group"], {})
        gc = ginfo.get("color", A["label_tertiary"])
        tol = c.get("tolerance", "pending")
        tol_colors = {"tolerated": "#30D158", "partial": "#FF9F0A", "not_tolerated": "#FF453A"}
        tc = tol_colors.get(tol, A["label_quaternary"])

        items += (
            f'<div style="display:flex;align-items:center;gap:8px;padding:6px 0;'
            f'border-bottom:1px solid {A["separator"]}">'
            f'<div style="width:8px;height:8px;border-radius:50%;background:{tc};flex-shrink:0"></div>'
            f'<div style="flex:1">'
            f'<span style="font-size:12px;font-weight:600;color:{gc}">'
            f'{ginfo.get("label", c["fodmap_group"])}</span>'
            f'<span style="font-size:11px;color:{A["label_tertiary"]};margin-left:6px">'
            f'{c["challenge_food"]} &middot; {c["start_date"]}</span>'
            f'</div>'
            f'</div>'
        )

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_md"]};padding:12px 16px;margin-bottom:12px">'
        f'<div style="font-size:12px;font-weight:600;color:{A["label_secondary"]};'
        f'margin-bottom:4px">Challenge Timeline</div>'
        f'{items}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# CORRELATION DISPLAY
# ══════════════════════════════════════════════════════════════════════════════

def render_correlation_disclaimer():
    """Render 'Correlation does not imply causation' callout."""
    html = (
        f'<div style="background:rgba(255,159,10,0.06);border:1px solid rgba(255,159,10,0.2);'
        f'border-radius:{A["radius_md"]};padding:10px 14px;margin-bottom:12px">'
        f'<div style="font-size:11px;color:{A["orange"]}">'
        f'&#9888; <strong>Correlation does not imply causation.</strong> '
        f'These patterns may suggest associations worth discussing with your healthcare provider, '
        f'but they do not prove that a specific food group causes your symptoms.</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_correlation_table(correlations):
    """Render a table of Spearman rho values with strength labels."""
    if not correlations:
        st.caption("Not enough data for correlations. Log at least 10 days of both symptoms and food.")
        return

    rows = ""
    for c in correlations:
        ginfo = FODMAP_GROUPS.get(c["group"], {})
        gc = ginfo.get("color", A["label_tertiary"])
        glabel = ginfo.get("label", c["group"])

        sym_info = GI_SYMPTOMS.get(c["symptom"], {})
        sym_label = sym_info.get("label", c["symptom"].replace("_", " ").title())
        if c["symptom"] == "overall_score":
            sym_label = "Overall"

        rho = c["rho"]
        strength = c["strength"]
        strength_info = CORRELATION_STRENGTH.get(strength, {})
        sc = strength_info.get("color", A["label_tertiary"])
        sl = strength_info.get("label", strength)

        direction = "+" if rho > 0 else "-" if rho < 0 else ""
        p_str = f'p={c["p"]:.3f}' if c["p"] is not None else ""

        rows += (
            f'<div style="display:flex;align-items:center;padding:6px 0;'
            f'border-bottom:1px solid {A["separator"]};gap:8px">'
            f'<div style="flex:1;font-size:12px;color:{gc};font-weight:600">{glabel}</div>'
            f'<div style="flex:1;font-size:12px;color:{A["label_secondary"]}">{sym_label}</div>'
            f'<div style="width:60px;font-family:{A["font_display"]};font-size:13px;'
            f'font-weight:700;color:{A["label_primary"]};text-align:right">'
            f'{direction}{abs(rho):.2f}</div>'
            f'<div style="width:80px;text-align:center">'
            f'<span style="font-size:10px;font-weight:600;padding:2px 6px;border-radius:3px;'
            f'background:{sc}20;color:{sc}">{sl}</span></div>'
            f'<div style="width:60px;font-size:10px;color:{A["label_quaternary"]};'
            f'text-align:right">n={c["n"]} {p_str}</div>'
            f'</div>'
        )

    # Header
    header = (
        f'<div style="display:flex;align-items:center;padding:6px 0;'
        f'border-bottom:2px solid {A["separator"]};gap:8px">'
        f'<div style="flex:1;font-size:10px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.05em;color:{A["label_tertiary"]}">FODMAP Group</div>'
        f'<div style="flex:1;font-size:10px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.05em;color:{A["label_tertiary"]}">Symptom</div>'
        f'<div style="width:60px;font-size:10px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.05em;color:{A["label_tertiary"]};text-align:right">Rho</div>'
        f'<div style="width:80px;font-size:10px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.05em;color:{A["label_tertiary"]};text-align:center">Strength</div>'
        f'<div style="width:60px;font-size:10px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.05em;color:{A["label_tertiary"]};text-align:right">Details</div>'
        f'</div>'
    )

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_md"]};padding:12px 16px;margin-bottom:12px">'
        f'{header}{rows}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# EVIDENCE & CONFIDENCE
# ══════════════════════════════════════════════════════════════════════════════

def render_confidence_badge(confidence):
    """Render an A/B/C confidence badge for a diet type."""
    colors = {"A": "#30D158", "B": "#0A84FF", "C": "#FF9F0A", "D": "#FF453A"}
    labels = {"A": "Tier A", "B": "Tier B", "C": "Tier C", "D": "Tier D"}
    c = colors.get(confidence, A["label_tertiary"])
    l = labels.get(confidence, f"Tier {confidence}")
    html = (
        f'<span style="display:inline-block;font-size:10px;font-weight:700;'
        f'padding:2px 8px;border-radius:4px;background:{c}20;color:{c};'
        f'text-transform:uppercase;letter-spacing:0.05em">{l}</span>'
    )
    return html


def render_evidence_coverage_box():
    """Render the evidence coverage and limitations box."""
    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px;margin-bottom:12px">'
        f'<div style="font-family:{A["font_display"]};font-size:15px;font-weight:600;'
        f'color:{A["label_primary"]};margin-bottom:12px">Evidence Coverage &amp; Limitations</div>'
        f'<div style="margin-bottom:10px">'
        f'<div style="font-size:12px;font-weight:600;color:{A["green"]};margin-bottom:4px">'
        f'What this tool covers:</div>'
        f'<div style="font-size:12px;color:{A["label_secondary"]};line-height:18px">'
        f'&#8226; Daily GI symptom tracking (7 symptoms, standardized scales)<br>'
        f'&#8226; FODMAP-aware food diary with Monash-aligned serving thresholds<br>'
        f'&#8226; 3-phase Low-FODMAP protocol management (Elimination, Reintroduction, Personalization)<br>'
        f'&#8226; Pattern analysis: Spearman rank correlations between food groups and symptoms (n&ge;10 gate)<br>'
        f'&#8226; Evidence library: 6 PubMed-verified references (Tier A &amp; B only)</div>'
        f'</div>'
        f'<div style="margin-bottom:10px">'
        f'<div style="font-size:12px;font-weight:600;color:{A["red"]};margin-bottom:4px">'
        f'What this tool does NOT do:</div>'
        f'<div style="font-size:12px;color:{A["label_secondary"]};line-height:18px">'
        f'&#8226; Diagnose SIBO or any gastrointestinal condition<br>'
        f'&#8226; Replace breath testing, jejunal aspirate, or clinical evaluation<br>'
        f'&#8226; Provide medical advice or treatment recommendations<br>'
        f'&#8226; Substitute for consultation with a gastroenterologist or dietitian<br>'
        f'&#8226; Guarantee accuracy of FODMAP ratings (individual tolerance varies)</div>'
        f'</div>'
        f'<div style="font-size:11px;color:{A["label_tertiary"]};font-style:italic">'
        f'FODMAP serving-size thresholds are aligned with Monash University guidance but may '
        f'not reflect the most recent updates. Always verify with the official Monash FODMAP app '
        f'or a qualified dietitian.</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_diet_confidence_table():
    """Render the diet types with confidence ratings."""
    rows = ""
    for key, dt in SIBO_DIET_TYPES.items():
        badge = render_confidence_badge(dt["confidence"])
        rows += (
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;'
            f'padding:10px 0;border-bottom:1px solid {A["separator"]}">'
            f'<div style="flex:1">'
            f'<div style="font-size:13px;font-weight:600;color:{A["label_primary"]}">'
            f'{dt["label"]}</div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]};margin-top:2px">'
            f'{dt["note"]}</div>'
            f'</div>'
            f'<div style="margin-left:12px">{badge}</div>'
            f'</div>'
        )

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_md"]};padding:12px 16px;margin-bottom:12px">'
        f'<div style="font-size:12px;font-weight:600;color:{A["label_secondary"]};'
        f'margin-bottom:4px">Dietary Approaches — Evidence Confidence</div>'
        f'{rows}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
