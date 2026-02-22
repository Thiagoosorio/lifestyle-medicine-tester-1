"""
Apple-style premium CSS theme for the Lifestyle Medicine Coach app.

Clean, minimal design inspired by Apple Health / Fitness+ aesthetic.
Uses system fonts, subtle shadows, rounded surfaces, and refined spacing.

Usage:
    from components.custom_theme import inject_custom_css, render_hero_stats
    inject_custom_css()
    render_hero_stats([{"label": "Streak", "value": "12 days", "icon": "flame", "color": "#FF9F0A"}])
"""

import streamlit as st


def inject_custom_css() -> None:
    """Inject the Apple-style CSS theme. Call once at the top of each page."""

    st.markdown("""<style>
/* ── APPLE-STYLE THEME ─────────────────────────────────────────────────── */

/* 0. Root Variables */
:root {
    --apple-bg: #000000;
    --apple-surface: rgba(28, 28, 30, 0.95);
    --apple-surface-2: rgba(44, 44, 46, 0.90);
    --apple-border: rgba(255, 255, 255, 0.08);
    --apple-border-hover: rgba(255, 255, 255, 0.15);
    --apple-text: #F5F5F7;
    --apple-text-2: rgba(235, 235, 245, 0.6);
    --apple-text-3: rgba(235, 235, 245, 0.3);
    --apple-green: #30D158;
    --apple-blue: #0A84FF;
    --apple-orange: #FF9F0A;
    --apple-red: #FF453A;
    --apple-purple: #BF5AF2;
    --apple-pink: #FF375F;
    --apple-teal: #64D2FF;
    --apple-radius: 16px;
    --apple-radius-sm: 12px;
    --apple-radius-xs: 8px;
    --apple-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    --apple-shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.4);
    --apple-transition: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    --apple-font: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", system-ui, sans-serif;
}

/* 1. Global Typography & Spacing */
html, body, [class*="css"] {
    font-family: var(--apple-font) !important;
}

section.main .block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1100px;
}

/* 2. Clean Headers - Apple style white, no gradient tricks */
.stMarkdown h1, [data-testid="stMarkdownContainer"] h1 {
    font-weight: 700 !important;
    letter-spacing: -0.025em;
    color: var(--apple-text) !important;
}

.stMarkdown h2, [data-testid="stMarkdownContainer"] h2 {
    font-weight: 600 !important;
    letter-spacing: -0.02em;
    color: var(--apple-text) !important;
}

.stMarkdown h3, [data-testid="stMarkdownContainer"] h3 {
    font-weight: 600 !important;
    letter-spacing: -0.015em;
    color: var(--apple-text) !important;
    font-size: 1.25rem !important;
}

/* 3. Metric Cards - Clean Apple surfaces */
[data-testid="stMetric"],
[data-testid="metric-container"] {
    background: var(--apple-surface);
    border: 1px solid var(--apple-border);
    border-radius: var(--apple-radius);
    padding: 1rem 1.2rem;
    transition: var(--apple-transition);
}

[data-testid="stMetric"]:hover,
[data-testid="metric-container"]:hover {
    border-color: var(--apple-border-hover);
    box-shadow: var(--apple-shadow);
    transform: translateY(-1px);
}

[data-testid="stMetricLabel"] {
    color: var(--apple-text-2) !important;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-weight: 500;
}

[data-testid="stMetricValue"] {
    font-weight: 700 !important;
    font-size: 1.5rem !important;
    color: var(--apple-text) !important;
    letter-spacing: -0.02em;
}

/* 4. Sidebar - Clean dark surface */
section[data-testid="stSidebar"] {
    background: var(--apple-surface) !important;
    border-right: 1px solid var(--apple-border);
}

section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"],
section[data-testid="stSidebar"] a {
    transition: var(--apple-transition);
    border-radius: var(--apple-radius-xs);
}

section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover,
section[data-testid="stSidebar"] a:hover {
    background: rgba(255, 255, 255, 0.06);
}

section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-selected="true"],
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {
    background: rgba(10, 132, 255, 0.12) !important;
}

/* 5. Progress Bars - Apple green gradient */
[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, var(--apple-green), var(--apple-teal)) !important;
    border-radius: 999px;
    transition: width 0.5s ease-out;
}

[data-testid="stProgress"] > div > div {
    background: rgba(255, 255, 255, 0.06) !important;
    border-radius: 999px;
    height: 6px !important;
}

/* 6. Expanders - Clean card style */
[data-testid="stExpander"] {
    background: var(--apple-surface);
    border: 1px solid var(--apple-border) !important;
    border-radius: var(--apple-radius) !important;
    transition: var(--apple-transition);
    overflow: hidden;
}

[data-testid="stExpander"]:hover {
    border-color: var(--apple-border-hover) !important;
    box-shadow: var(--apple-shadow);
}

[data-testid="stExpander"] summary {
    font-weight: 600;
    padding: 0.7rem 1rem;
}

/* 7. Forms - Subtle surface */
[data-testid="stForm"] {
    background: var(--apple-surface);
    border: 1px solid var(--apple-border);
    border-radius: var(--apple-radius);
    padding: 1.25rem;
    transition: var(--apple-transition);
}

/* 8. Buttons - Apple rounded pill style */
.stButton > button {
    border-radius: var(--apple-radius-sm);
    transition: var(--apple-transition);
    font-weight: 600;
    letter-spacing: 0.01em;
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: var(--apple-shadow);
}

/* 9. Input Focus - Blue ring (Apple style) */
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus,
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--apple-blue) !important;
    box-shadow: 0 0 0 3px rgba(10, 132, 255, 0.25) !important;
    transition: var(--apple-transition);
}

.stSelectbox > div > div:focus-within,
[data-testid="stSelectbox"] > div > div:focus-within {
    border-color: var(--apple-blue) !important;
    box-shadow: 0 0 0 3px rgba(10, 132, 255, 0.25) !important;
}

/* 10. Slider thumb */
.stSlider [role="slider"] {
    transition: var(--apple-transition);
}

.stSlider [role="slider"]:hover {
    transform: scale(1.1);
    box-shadow: 0 0 12px rgba(10, 132, 255, 0.3);
}

/* 11. Custom Scrollbar - Thin, minimal */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.15); border-radius: 999px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.25); }
* { scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.15) transparent; }

/* 12. Dividers */
[data-testid="stDivider"], hr {
    border-color: var(--apple-border) !important;
    opacity: 0.6;
    margin-top: 1.5rem;
    margin-bottom: 1.5rem;
}

/* 13. Tabs - Apple segmented control feel */
.stTabs [data-baseweb="tab-list"] { gap: 2px; }

.stTabs [data-baseweb="tab"] {
    border-radius: var(--apple-radius-xs) var(--apple-radius-xs) 0 0;
    transition: var(--apple-transition);
    font-weight: 600;
}

.stTabs [data-baseweb="tab"]:hover {
    background: rgba(255, 255, 255, 0.04);
}

.stTabs [aria-selected="true"] {
    border-bottom-color: var(--apple-blue) !important;
}

/* 14. Alerts */
[data-testid="stAlert"], .stAlert {
    border-radius: var(--apple-radius-sm) !important;
}
</style>""", unsafe_allow_html=True)


def render_hero_stats(stats: list) -> None:
    """Render Apple-style stat cards using st.columns for reliable rendering.

    Each stat dict: label, value, icon (emoji), color (hex), delta (optional).
    """
    cols = st.columns(len(stats))
    for i, stat in enumerate(stats):
        with cols[i]:
            icon = stat.get("icon", "")
            value = stat.get("value", "")
            label = stat.get("label", "")
            color = stat.get("color", "#30D158")
            delta = stat.get("delta")

            # Build delta HTML
            delta_html = ""
            if delta is not None and str(delta) != "":
                d = str(delta)
                if d.startswith("+"):
                    delta_html = f'<div style="color:#30D158;font-size:0.8rem;font-weight:600;margin-top:4px">&#9650; {d}</div>'
                elif d.startswith("-"):
                    delta_html = f'<div style="color:#FF453A;font-size:0.8rem;font-weight:600;margin-top:4px">&#9660; {d}</div>'
                else:
                    delta_html = f'<div style="color:rgba(235,235,245,0.6);font-size:0.8rem;margin-top:4px">{d}</div>'

            st.markdown(f"""<div style="
                background: rgba(28,28,30,0.95);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 16px;
                padding: 20px;
                border-top: 3px solid {color};
                transition: 0.25s ease;
            ">
                <div style="font-size:1.8rem;line-height:1;margin-bottom:8px">{icon}</div>
                <div style="font-size:1.7rem;font-weight:700;color:#F5F5F7;letter-spacing:-0.02em;line-height:1.2">{value}</div>
                <div style="font-size:0.75rem;color:rgba(235,235,245,0.6);text-transform:uppercase;letter-spacing:0.05em;font-weight:500;margin-top:4px">{label}</div>
                {delta_html}
            </div>""", unsafe_allow_html=True)
