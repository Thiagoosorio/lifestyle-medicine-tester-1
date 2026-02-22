"""
Apple Design System for Streamlit — Inline-style helpers.

CRITICAL: Streamlit's st.markdown() processes HTML through a Markdown parser.
- Indented HTML (4+ spaces) is treated as a code block → shows as raw text
- Blank lines inside HTML blocks terminate the block
- Solution: Build all HTML as single-line strings with NO indentation, NO blank lines

The <style> block targets only Streamlit's own component selectors which DO work.
"""

import streamlit as st


# ══════════════════════════════════════════════════════════════════════════════
# APPLE HIG DESIGN TOKENS
# ══════════════════════════════════════════════════════════════════════════════

APPLE = {
    "bg_primary": "#000000",
    "bg_elevated": "#1C1C1E",
    "bg_secondary": "#2C2C2E",
    "bg_tertiary": "#3A3A3C",
    "label_primary": "rgba(255,255,255,1.0)",
    "label_secondary": "rgba(235,235,245,0.8)",
    "label_tertiary": "rgba(235,235,245,0.5)",
    "label_quaternary": "rgba(235,235,245,0.35)",
    "fill_tertiary": "rgba(118,118,128,0.24)",
    "separator": "rgba(84,84,88,0.6)",
    "glass_bg": "rgba(28,28,30,0.72)",
    "glass_bg_thin": "rgba(28,28,30,0.55)",
    "glass_border": "rgba(255,255,255,0.10)",
    "blue": "#0A84FF",
    "green": "#34C759",
    "red": "#FF453A",
    "orange": "#FF9F0A",
    "yellow": "#FFD60A",
    "pink": "#FF375F",
    "purple": "#BF5AF2",
    "teal": "#1EC8C6",
    "indigo": "#5E5CE6",
    "move": "#FA2D55",
    "font_display": "-apple-system,BlinkMacSystemFont,'SF Pro Display','Helvetica Neue',system-ui,sans-serif",
    "font_text": "-apple-system,BlinkMacSystemFont,'SF Pro Text','Helvetica Neue',system-ui,sans-serif",
    "radius_sm": "8px",
    "radius_md": "12px",
    "radius_lg": "16px",
    "radius_xl": "20px",
    "radius_2xl": "28px",
    "hero_gradient": "linear-gradient(135deg,#1a0a2e 0%,#16213e 30%,#0f3460 60%,#1a0a2e 100%)",
}


def inject_custom_css() -> None:
    """Inject Apple Design System CSS targeting Streamlit's own selectors."""

    st.markdown("""<style>
:root {
    --bg-primary: #000000;
    --bg-primary-elevated: #1C1C1E;
    --bg-secondary: #1C1C1E;
    --bg-tertiary: #2C2C2E;
    --label-primary: rgba(255,255,255,1.0);
    --label-secondary: rgba(235,235,245,0.8);
    --label-tertiary: rgba(235,235,245,0.5);
    --label-quaternary: rgba(235,235,245,0.35);
    --fill-tertiary: rgba(118,118,128,0.24);
    --separator: rgba(84,84,88,0.6);
    --separator-opaque: #38383A;
    --blue: #0A84FF;
    --green: #34C759;
    --red: #FF453A;
    --orange: #FF9F0A;
    --yellow: #FFD60A;
    --pink: #FF375F;
    --purple: #BF5AF2;
    --teal: #1EC8C6;
    --indigo: #5E5CE6;
    --move: #FA2D55;
    --font-display: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", system-ui, sans-serif;
    --font-text: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", system-ui, sans-serif;
    --ease-default: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    --ease-spring: 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
}
[data-testid="stDecoration"] { display:none !important; }
[data-testid="stStatusWidget"] { visibility:hidden !important; }
footer { visibility:hidden !important; height:0 !important; }
header[data-testid="stHeader"] { background:rgba(0,0,0,0.85) !important; backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px); }
.stApp {
    background-color: var(--bg-primary) !important;
    font-family: var(--font-text) !important;
    -webkit-font-smoothing: antialiased;
}
section.main .block-container {
    padding-top: 32px;
    padding-bottom: 40px;
    max-width: 1200px;
}
.main .block-container {
    animation: anim-fade-up 0.4s cubic-bezier(0.4,0,0.2,1) both !important;
}
html, body, [class*="css"] { font-family: var(--font-text) !important; }
.stMarkdown h1, [data-testid="stMarkdownContainer"] h1 {
    font-family: var(--font-display) !important;
    font-size: 34px !important; font-weight: 700 !important;
    line-height: 41px !important; letter-spacing: -0.02em;
    color: var(--label-primary) !important;
}
.stMarkdown h2, [data-testid="stMarkdownContainer"] h2 {
    font-family: var(--font-display) !important;
    font-size: 22px !important; font-weight: 700 !important;
    line-height: 28px !important; letter-spacing: -0.013em;
    color: var(--label-primary) !important;
}
.stMarkdown h3, [data-testid="stMarkdownContainer"] h3 {
    font-family: var(--font-display) !important;
    font-size: 20px !important; font-weight: 600 !important;
    line-height: 24px !important; letter-spacing: -0.01em;
    color: var(--label-primary) !important;
}
[data-testid="stSidebarCollapseButton"],
[data-testid="stExpandSidebarButton"] {
    background: var(--blue) !important;
    color: white !important;
    border-radius: 8px !important;
    min-width: 40px !important; min-height: 40px !important;
    border: none !important;
    opacity: 1 !important;
}
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="stExpandSidebarButton"] svg {
    color: white !important;
    fill: white !important;
    stroke: white !important;
}
[data-testid="stSidebarCollapseButton"]:hover,
[data-testid="stExpandSidebarButton"]:hover {
    background: var(--red) !important;
}
section[data-testid="stSidebar"] {
    background: rgba(28,28,30,0.88) !important;
    border-right: 1px solid var(--separator) !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {
    transition: var(--ease-default) !important;
    border-radius: 8px !important; margin: 2px 8px !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {
    background: rgba(255,255,255,0.06) !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-selected="true"],
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {
    background: rgba(94,92,230,0.15) !important;
}
[data-testid="stMetric"] {
    background: var(--bg-primary-elevated) !important;
    border: 1px solid var(--separator) !important;
    border-radius: 16px !important; padding: 20px !important;
    transition: var(--ease-default) !important;
}
[data-testid="stMetric"]:hover {
    border-color: rgba(255,255,255,0.18) !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4) !important;
    transform: translateY(-2px) !important;
}
[data-testid="stMetricLabel"] {
    font-family: var(--font-text) !important;
    font-size: 11px !important; font-weight: 600 !important;
    letter-spacing: 0.06em !important; text-transform: uppercase !important;
    color: var(--label-tertiary) !important;
}
[data-testid="stMetricValue"] {
    font-family: var(--font-display) !important;
    font-size: 28px !important; font-weight: 700 !important;
    letter-spacing: -0.016em !important;
    color: var(--label-primary) !important;
    font-variant-numeric: tabular-nums !important;
}
.stButton > button {
    border-radius: 9999px !important;
    font-family: var(--font-text) !important;
    font-size: 15px !important; font-weight: 600 !important;
    min-height: 44px !important;
    transition: var(--ease-default) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
}
.stButton > button:hover {
    transform: translateY(-1px) scale(1.01) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
}
.stButton > button:active { transform: scale(0.97) !important; }
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--indigo), #3634A3) !important;
    border: none !important;
    box-shadow: 0 4px 20px rgba(94,92,230,0.4) !important;
    color: white !important;
}
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: var(--bg-primary-elevated) !important;
    border: 1px solid var(--separator) !important;
    border-radius: 8px !important;
    font-family: var(--font-text) !important;
    font-size: 17px !important;
    color: var(--label-primary) !important;
    transition: var(--ease-default) !important;
    min-height: 44px !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus,
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--indigo) !important;
    box-shadow: 0 0 0 3px rgba(94,92,230,0.25) !important;
}
[data-testid="stProgress"] > div > div {
    background: var(--fill-tertiary) !important;
    border-radius: 9999px !important; height: 8px !important;
}
[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, var(--green), #32C8FF) !important;
    border-radius: 9999px !important;
    position: relative; overflow: hidden;
}
[data-testid="stProgress"] > div > div > div::after {
    content:''; position:absolute; inset:0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.25), transparent);
    animation: anim-shimmer 2.5s ease-in-out infinite;
}
.stTabs [data-baseweb="tab-list"] {
    background: var(--bg-primary-elevated) !important;
    border-radius: 8px !important; padding: 3px !important;
    gap: 2px !important;
    border: 1px solid var(--separator) !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 6px !important;
    font-family: var(--font-text) !important;
    font-size: 13px !important; font-weight: 600 !important;
    color: var(--label-secondary) !important;
    transition: var(--ease-default) !important;
}
.stTabs [aria-selected="true"] {
    background: rgba(255,255,255,0.10) !important;
    color: var(--label-primary) !important;
    border-bottom-color: transparent !important;
}
[data-testid="stForm"] {
    background: var(--bg-primary-elevated) !important;
    border: 1px solid var(--separator) !important;
    border-radius: 16px !important; padding: 20px !important;
}
[data-testid="stExpander"] {
    background: var(--bg-primary-elevated) !important;
    border: 1px solid var(--separator) !important;
    border-radius: 16px !important; overflow: hidden;
}
[data-testid="stExpander"]:hover { border-color: rgba(255,255,255,0.15) !important; }
[data-testid="stExpander"] summary { font-weight: 600; padding: 12px 16px; }
[data-testid="stAlert"] { border-radius: 12px !important; }
.stSlider [role="slider"] { transition: var(--ease-default) !important; }
.stSlider [role="slider"]:hover {
    transform: scale(1.12) !important;
    box-shadow: 0 0 12px rgba(94,92,230,0.4) !important;
}
[data-testid="stDivider"], hr {
    border: none !important; height: 1px !important;
    background: var(--separator) !important; margin: 24px 0 !important;
}
[data-testid="stPlotlyChart"] {
    background: var(--bg-primary-elevated) !important;
    border: 1px solid var(--separator) !important;
    border-radius: 16px !important; overflow: hidden !important;
    padding: 8px !important;
}
::-webkit-scrollbar { width:6px; height:6px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:rgba(255,255,255,0.15); border-radius:9999px; }
::-webkit-scrollbar-thumb:hover { background:rgba(255,255,255,0.25); }
* { scrollbar-width:thin; scrollbar-color:rgba(255,255,255,0.15) transparent; }
@keyframes anim-fade-up {
    from { opacity:0; transform:translateY(12px); }
    to { opacity:1; transform:translateY(0); }
}
@keyframes anim-shimmer {
    from { transform: translateX(-100%); }
    to { transform: translateX(200%); }
}
@keyframes anim-orb-drift {
    from { transform: translate(0,0) scale(1); }
    to { transform: translate(30px,20px) scale(1.1); }
}
[data-testid="stHorizontalBlock"] > div:nth-child(1) { animation: anim-fade-up 0.4s cubic-bezier(0.34,1.56,0.64,1) both; animation-delay:0.05s; }
[data-testid="stHorizontalBlock"] > div:nth-child(2) { animation: anim-fade-up 0.4s cubic-bezier(0.34,1.56,0.64,1) both; animation-delay:0.10s; }
[data-testid="stHorizontalBlock"] > div:nth-child(3) { animation: anim-fade-up 0.4s cubic-bezier(0.34,1.56,0.64,1) both; animation-delay:0.15s; }
[data-testid="stHorizontalBlock"] > div:nth-child(4) { animation: anim-fade-up 0.4s cubic-bezier(0.34,1.56,0.64,1) both; animation-delay:0.20s; }
[data-testid="stHorizontalBlock"] > div:nth-child(5) { animation: anim-fade-up 0.4s cubic-bezier(0.34,1.56,0.64,1) both; animation-delay:0.25s; }
@media (max-width: 768px) {
    section.main .block-container { padding-top:16px; padding-left:12px; padding-right:12px; }
    .stTabs [data-baseweb="tab"] { font-size:11px !important; padding:6px 8px !important; }
}
</style>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT HELPERS
# All HTML built as single-line strings via Python string concatenation.
# NO indentation, NO blank lines — avoids Markdown parser code-block trap.
# ══════════════════════════════════════════════════════════════════════════════

A = APPLE


def render_hero_banner(title: str, subtitle: str = "") -> None:
    """Render a gradient hero banner with animated orbs."""
    sub = ""
    if subtitle:
        sub = (
            f'<div style="font-family:{A["font_text"]};font-size:15px;'
            f'line-height:20px;color:{A["label_secondary"]};font-style:italic;'
            f'max-width:600px">{subtitle}</div>'
        )
    html = (
        f'<div style="background:{A["hero_gradient"]};border-radius:{A["radius_2xl"]};'
        f'padding:32px;position:relative;overflow:hidden;margin-bottom:24px">'
        f'<div style="position:absolute;top:-60px;left:-60px;width:280px;height:280px;'
        f'background:radial-gradient(circle,rgba(94,92,230,0.30) 0%,transparent 70%);'
        f'pointer-events:none;border-radius:50%;'
        f'animation:anim-orb-drift 8s ease-in-out infinite alternate"></div>'
        f'<div style="position:absolute;bottom:-70px;right:-30px;width:320px;height:320px;'
        f'background:radial-gradient(circle,rgba(250,45,85,0.20) 0%,transparent 70%);'
        f'pointer-events:none;border-radius:50%;'
        f'animation:anim-orb-drift 10s ease-in-out infinite alternate-reverse"></div>'
        f'<div style="position:relative;z-index:1">'
        f'<div style="font-family:{A["font_display"]};font-size:28px;line-height:34px;'
        f'font-weight:700;color:{A["label_primary"]};margin-bottom:8px;'
        f'letter-spacing:-0.016em">{title}</div>'
        f'{sub}'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_hero_stats(stats: list) -> None:
    """Render Apple Health-style stat cards. Single-line HTML per card."""
    cols = st.columns(len(stats))
    for i, col in enumerate(cols):
        with col:
            s = stats[i]
            icon = s.get("icon", "")
            value = s.get("value", "")
            label = s.get("label", "")
            color = s.get("color", A["green"])
            delta = s.get("delta")

            delta_html = ""
            if delta is not None and str(delta) != "":
                d = str(delta)
                if d.startswith("+"):
                    delta_html = (
                        f'<div style="font-size:13px;font-weight:600;'
                        f'margin-top:8px;color:{A["green"]}">&#9650; {d}</div>'
                    )
                elif d.startswith("-"):
                    delta_html = (
                        f'<div style="font-size:13px;font-weight:600;'
                        f'margin-top:8px;color:{A["red"]}">&#9660; {d}</div>'
                    )
                else:
                    delta_html = (
                        f'<div style="font-size:13px;margin-top:8px;'
                        f'color:{A["label_tertiary"]}">{d}</div>'
                    )

            html = (
                f'<div style="background:{A["glass_bg"]};'
                f'border:1px solid {A["glass_border"]};'
                f'border-left:3px solid {color};'
                f'border-radius:{A["radius_xl"]};padding:20px;'
                f'position:relative;overflow:hidden">'
                f'<div style="position:absolute;top:-30px;right:-20px;'
                f'width:120px;height:120px;border-radius:50%;pointer-events:none;'
                f'background:radial-gradient(circle,{color}20 0%,transparent 70%)"></div>'
                f'<div style="position:relative;z-index:1">'
                f'<div style="font-size:22px;line-height:1;margin-bottom:8px">{icon}</div>'
                f'<div style="font-family:{A["font_display"]};font-size:28px;'
                f'font-weight:700;color:{A["label_primary"]};'
                f'font-variant-numeric:tabular-nums;line-height:1;'
                f'letter-spacing:-0.016em">{value}</div>'
                f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
                f'letter-spacing:0.06em;color:{A["label_tertiary"]};'
                f'margin-top:8px">{label}</div>'
                f'{delta_html}'
                f'</div>'
                f'</div>'
            )
            st.markdown(html, unsafe_allow_html=True)


def render_glass_card(title: str, content: str, color: str = "#5E5CE6", icon: str = "") -> None:
    """Render a glass card with accent color."""
    html = (
        f'<div style="background:{A["glass_bg"]};'
        f'border:1px solid {A["glass_border"]};'
        f'border-radius:{A["radius_xl"]};padding:20px;'
        f'position:relative;overflow:hidden;margin-bottom:16px">'
        f'<div style="position:absolute;bottom:-40px;right:-20px;'
        f'width:120px;height:120px;border-radius:50%;pointer-events:none;'
        f'background:radial-gradient(circle,{color}18 0%,transparent 70%)"></div>'
        f'<div style="position:relative;z-index:1">'
        f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.06em;margin-bottom:8px;color:{color}">{icon} {title}</div>'
        f'<div style="font-size:15px;line-height:1.5;'
        f'color:{A["label_secondary"]}">{content}</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_section_header(title: str, subtitle: str = "") -> None:
    """Render a section header with Apple HIG typography."""
    sub = ""
    if subtitle:
        sub = (
            f'<div style="font-size:13px;line-height:18px;'
            f'color:{A["label_tertiary"]};margin-top:4px">{subtitle}</div>'
        )
    html = (
        f'<div style="margin-bottom:16px;margin-top:8px">'
        f'<div style="font-family:{A["font_display"]};font-size:20px;'
        f'line-height:24px;font-weight:600;color:{A["label_primary"]};'
        f'letter-spacing:-0.01em">{title}</div>'
        f'{sub}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_pillar_icons() -> None:
    """Render the 6 ACLM pillar icons in a horizontal flex row."""
    pillars = [
        ("&#127823;", "Nutrition"),
        ("&#127939;", "Activity"),
        ("&#128564;", "Sleep"),
        ("&#129495;", "Stress"),
        ("&#129309;", "Social"),
        ("&#128170;", "Clean"),
    ]
    cards = ""
    for emoji, name in pillars:
        cards += (
            f'<div style="background:{A["glass_bg_thin"]};'
            f'border:1px solid {A["glass_border"]};'
            f'border-radius:{A["radius_lg"]};padding:12px;'
            f'text-align:center;min-width:72px">'
            f'<div style="font-size:1.5rem">{emoji}</div>'
            f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:0.06em;color:{A["label_tertiary"]};'
            f'margin-top:4px">{name}</div>'
            f'</div>'
        )
    html = (
        f'<div style="display:flex;justify-content:center;'
        f'gap:16px;flex-wrap:wrap;margin-bottom:32px">'
        f'{cards}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
