"""
Custom premium CSS theme for the Lifestyle Medicine Coach app.

Provides glassmorphism cards, gradient headers, animated sidebar,
custom progress bars, smooth transitions, and hero stat cards.

Usage:
    from components.custom_theme import inject_custom_css, render_hero_stats
    inject_custom_css()   # call once at top of every page
    render_hero_stats([{"label": "Streak", "value": "12 days", "icon": "...", "color": "#4CAF50"}])
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Color constants (re-usable across the module)
# ---------------------------------------------------------------------------
PRIMARY = "#4CAF50"       # health green
SECONDARY = "#2196F3"     # blue
WARNING = "#FF9800"       # orange
BG_DARK = "#0e1117"       # Streamlit dark background base
SURFACE = "rgba(14, 17, 23, 0.65)"
TEXT_PRIMARY = "#FAFAFA"
TEXT_SECONDARY = "#B0B0B0"


def inject_custom_css() -> None:
    """Inject the full premium CSS theme.  Call once at the top of each page."""

    css = """
<style>
/* ==========================================================================
   0.  CSS CUSTOM PROPERTIES
   ========================================================================== */
:root {
    --lm-primary: #4CAF50;
    --lm-primary-glow: rgba(76, 175, 80, 0.35);
    --lm-secondary: #2196F3;
    --lm-warning: #FF9800;
    --lm-bg: #0e1117;
    --lm-surface: rgba(14, 17, 23, 0.65);
    --lm-surface-hover: rgba(14, 17, 23, 0.80);
    --lm-border: rgba(76, 175, 80, 0.15);
    --lm-border-hover: rgba(76, 175, 80, 0.35);
    --lm-text: #FAFAFA;
    --lm-text-secondary: #B0B0B0;
    --lm-radius: 14px;
    --lm-radius-sm: 10px;
    --lm-transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ==========================================================================
   1.  FADE-IN PAGE ANIMATION
   ========================================================================== */
@keyframes lmFadeInUp {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
}

@keyframes lmPulseGlow {
    0%, 100% { box-shadow: 0 0 8px var(--lm-primary-glow); }
    50%      { box-shadow: 0 0 20px var(--lm-primary-glow); }
}

@keyframes lmShimmer {
    0%   { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

/* Apply fade-in to the main block-container */
section.main .block-container {
    animation: lmFadeInUp 0.5s ease-out both;
}

/* ==========================================================================
   2.  BETTER SPACING
   ========================================================================== */
section.main .block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1100px;
}

/* Tighten up default vertical gaps inside columns */
[data-testid="column"] > div {
    gap: 0.5rem;
}

/* ==========================================================================
   3.  GLASSMORPHISM METRIC CARDS
   ========================================================================== */
[data-testid="stMetric"],
[data-testid="metric-container"] {
    background: var(--lm-surface);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--lm-border);
    border-radius: var(--lm-radius);
    padding: 1rem 1.25rem;
    transition: var(--lm-transition);
    animation: lmFadeInUp 0.45s ease-out both;
}

[data-testid="stMetric"]:hover,
[data-testid="metric-container"]:hover {
    border-color: var(--lm-border-hover);
    box-shadow: 0 0 18px var(--lm-primary-glow),
                0 4px 24px rgba(0, 0, 0, 0.3);
    transform: translateY(-2px);
    background: var(--lm-surface-hover);
}

/* Metric label */
[data-testid="stMetricLabel"] {
    color: var(--lm-text-secondary) !important;
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* Metric value */
[data-testid="stMetricValue"] {
    font-weight: 700 !important;
    font-size: 1.6rem !important;
    color: var(--lm-text) !important;
}

/* Metric delta (positive) */
[data-testid="stMetricDelta"] svg {
    width: 12px; height: 12px;
}

/* ==========================================================================
   4.  GRADIENT SECTION HEADERS (h3)
   ========================================================================== */
.stMarkdown h3,
[data-testid="stMarkdownContainer"] h3 {
    background: linear-gradient(135deg, #ffffff 0%, var(--lm-primary) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 700;
    letter-spacing: -0.01em;
    padding-bottom: 0.15em;
}

/* h2 gets a subtler gradient */
.stMarkdown h2,
[data-testid="stMarkdownContainer"] h2 {
    background: linear-gradient(135deg, #ffffff 20%, var(--lm-secondary) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* ==========================================================================
   5.  ANIMATED SIDEBAR
   ========================================================================== */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(14,17,23,0.97) 0%, rgba(14,17,23,0.92) 100%);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border-right: 1px solid var(--lm-border);
}

/* Sidebar navigation links / items */
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"],
section[data-testid="stSidebar"] a {
    transition: var(--lm-transition);
    border-radius: var(--lm-radius-sm);
}

section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover,
section[data-testid="stSidebar"] a:hover {
    background: rgba(76, 175, 80, 0.08);
    padding-left: 6px;
    border-left: 3px solid var(--lm-primary);
}

/* Sidebar active link highlight */
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-selected="true"],
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {
    background: rgba(76, 175, 80, 0.12) !important;
    border-left: 3px solid var(--lm-primary);
}

/* Sidebar button hover */
section[data-testid="stSidebar"] button:hover {
    border-color: var(--lm-primary) !important;
    color: var(--lm-primary) !important;
    transition: var(--lm-transition);
}

/* ==========================================================================
   6.  CUSTOM PROGRESS BARS
   ========================================================================== */
[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, var(--lm-primary), #26c6da) !important;
    border-radius: 999px;
    transition: width 0.6s ease-out;
}

/* Track */
[data-testid="stProgress"] > div > div {
    background: rgba(76, 175, 80, 0.10) !important;
    border-radius: 999px;
    height: 8px !important;
}

/* ==========================================================================
   7.  CARD-STYLE CONTAINERS  (expanders, forms)
   ========================================================================== */
/* Expander */
[data-testid="stExpander"] {
    background: var(--lm-surface);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--lm-border) !important;
    border-radius: var(--lm-radius) !important;
    transition: var(--lm-transition);
    overflow: hidden;
}

[data-testid="stExpander"]:hover {
    border-color: var(--lm-border-hover) !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
}

[data-testid="stExpander"] summary {
    font-weight: 600;
    padding: 0.75rem 1rem;
}

/* Form wrapper */
[data-testid="stForm"] {
    background: var(--lm-surface);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--lm-border);
    border-radius: var(--lm-radius);
    padding: 1.25rem;
    transition: var(--lm-transition);
}

[data-testid="stForm"]:hover {
    border-color: var(--lm-border-hover);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.20);
}

/* ==========================================================================
   8.  BUTTON HOVER EFFECTS
   ========================================================================== */
.stButton > button {
    border-radius: var(--lm-radius-sm);
    transition: var(--lm-transition);
    font-weight: 600;
    letter-spacing: 0.02em;
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(76, 175, 80, 0.25);
}

/* Primary button glow */
.stButton > button[kind="primary"],
.stButton > button[data-testid="stFormSubmitButton"] {
    box-shadow: 0 0 0 0 var(--lm-primary-glow);
}

.stButton > button[kind="primary"]:hover {
    box-shadow: 0 0 20px var(--lm-primary-glow);
}

/* ==========================================================================
   9.  CUSTOM SCROLLBAR
   ========================================================================== */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}

::-webkit-scrollbar-track {
    background: transparent;
}

::-webkit-scrollbar-thumb {
    background: rgba(76, 175, 80, 0.25);
    border-radius: 999px;
}

::-webkit-scrollbar-thumb:hover {
    background: rgba(76, 175, 80, 0.45);
}

/* Firefox */
* {
    scrollbar-width: thin;
    scrollbar-color: rgba(76, 175, 80, 0.25) transparent;
}

/* ==========================================================================
   10. GLOWING ACCENT COLORS ON ACTIVE / FOCUSED ELEMENTS
   ========================================================================== */
/* Text inputs */
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus,
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--lm-primary) !important;
    box-shadow: 0 0 0 2px var(--lm-primary-glow) !important;
    transition: var(--lm-transition);
}

/* Select boxes */
.stSelectbox > div > div:focus-within,
[data-testid="stSelectbox"] > div > div:focus-within {
    border-color: var(--lm-primary) !important;
    box-shadow: 0 0 0 2px var(--lm-primary-glow) !important;
}

/* Sliders - thumb glow */
.stSlider [role="slider"] {
    box-shadow: 0 0 8px var(--lm-primary-glow);
    transition: var(--lm-transition);
}

.stSlider [role="slider"]:hover {
    box-shadow: 0 0 16px var(--lm-primary-glow);
    transform: scale(1.15);
}

/* Checkbox / toggle */
[data-testid="stCheckbox"]:hover {
    color: var(--lm-primary);
}

/* ==========================================================================
   11. DIVIDER STYLING
   ========================================================================== */
[data-testid="stDivider"],
hr {
    border-color: var(--lm-border) !important;
    opacity: 0.5;
    margin-top: 1.5rem;
    margin-bottom: 1.5rem;
}

/* ==========================================================================
   12. TOAST / SUCCESS / INFO ALERTS POLISHING
   ========================================================================== */
[data-testid="stAlert"],
.stAlert {
    border-radius: var(--lm-radius-sm) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
}

/* ==========================================================================
   13. TAB CONTAINER
   ========================================================================== */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
}

.stTabs [data-baseweb="tab"] {
    border-radius: var(--lm-radius-sm) var(--lm-radius-sm) 0 0;
    transition: var(--lm-transition);
    font-weight: 600;
}

.stTabs [data-baseweb="tab"]:hover {
    background: rgba(76, 175, 80, 0.06);
}

.stTabs [aria-selected="true"] {
    border-bottom-color: var(--lm-primary) !important;
}

/* ==========================================================================
   14. HERO STAT CARDS (injected via render_hero_stats)
   ========================================================================== */
.lm-hero-grid {
    display: grid;
    gap: 1rem;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    margin: 0.75rem 0 1.25rem 0;
}

.lm-hero-card {
    background: var(--lm-surface);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid var(--lm-border);
    border-radius: var(--lm-radius);
    padding: 1.25rem 1.35rem;
    transition: var(--lm-transition);
    animation: lmFadeInUp 0.5s ease-out both;
    position: relative;
    overflow: hidden;
}

/* stagger the fade-in for each card */
.lm-hero-card:nth-child(1) { animation-delay: 0.00s; }
.lm-hero-card:nth-child(2) { animation-delay: 0.07s; }
.lm-hero-card:nth-child(3) { animation-delay: 0.14s; }
.lm-hero-card:nth-child(4) { animation-delay: 0.21s; }
.lm-hero-card:nth-child(5) { animation-delay: 0.28s; }
.lm-hero-card:nth-child(6) { animation-delay: 0.35s; }

/* Accent bar at the top */
.lm-hero-card::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--card-accent);
    border-radius: var(--lm-radius) var(--lm-radius) 0 0;
    opacity: 0.85;
}

/* Subtle background glow */
.lm-hero-card::after {
    content: "";
    position: absolute;
    top: -40%; right: -30%;
    width: 120px; height: 120px;
    background: radial-gradient(circle, var(--card-accent) 0%, transparent 70%);
    opacity: 0.06;
    border-radius: 50%;
    pointer-events: none;
    transition: opacity var(--lm-transition);
}

.lm-hero-card:hover {
    transform: translateY(-3px);
    border-color: var(--card-accent, var(--lm-border-hover));
    box-shadow: 0 0 22px color-mix(in srgb, var(--card-accent) 35%, transparent),
                0 8px 32px rgba(0, 0, 0, 0.3);
}

.lm-hero-card:hover::after {
    opacity: 0.12;
}

.lm-hero-icon {
    font-size: 2rem;
    line-height: 1;
    margin-bottom: 0.5rem;
    filter: drop-shadow(0 0 6px var(--card-accent));
}

.lm-hero-value {
    font-size: 1.85rem;
    font-weight: 800;
    color: var(--lm-text);
    line-height: 1.15;
    margin-bottom: 0.15rem;
}

.lm-hero-label {
    font-size: 0.78rem;
    color: var(--lm-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
}

.lm-hero-delta {
    display: inline-block;
    font-size: 0.76rem;
    font-weight: 700;
    margin-top: 0.45rem;
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    line-height: 1.4;
}

.lm-hero-delta.positive {
    color: #4CAF50;
    background: rgba(76, 175, 80, 0.12);
}

.lm-hero-delta.negative {
    color: #F44336;
    background: rgba(244, 67, 54, 0.12);
}

.lm-hero-delta.neutral {
    color: #B0B0B0;
    background: rgba(176, 176, 176, 0.10);
}

/* ==========================================================================
   15. RESPONSIVE TWEAKS
   ========================================================================== */
@media (max-width: 768px) {
    .lm-hero-grid {
        grid-template-columns: repeat(2, 1fr);
    }
    .lm-hero-value {
        font-size: 1.45rem;
    }
    section.main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
}

@media (max-width: 480px) {
    .lm-hero-grid {
        grid-template-columns: 1fr;
    }
}
</style>
"""

    st.markdown(css, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Hero stat cards
# ---------------------------------------------------------------------------

def render_hero_stats(stats: list[dict]) -> None:
    """Render large, beautiful stat cards with icons, values, deltas, and animations.

    Parameters
    ----------
    stats : list[dict]
        Each dict may have the following keys:
            label : str          – metric label text
            value : str          – display value (e.g. "12 days", "87%")
            delta : str | None   – optional delta string (e.g. "+3", "-2%"). Prefix
                                   with ``+`` for positive styling, ``-`` for negative,
                                   or anything else for neutral.
            icon  : str          – emoji displayed above the value (e.g. "\U0001f525")
            color : str          – hex accent color for this card (e.g. "#4CAF50")

    Example
    -------
    >>> render_hero_stats([
    ...     {"label": "Current Streak", "value": "12 days",
    ...      "delta": "+3", "icon": "\U0001f525", "color": "#4CAF50"},
    ...     {"label": "Habits Today",   "value": "5/7",
    ...      "icon": "\u2705", "color": "#2196F3"},
    ... ])
    """

    cards_html_parts: list[str] = []
    for stat in stats:
        icon = stat.get("icon", "")
        value = stat.get("value", "")
        label = stat.get("label", "")
        color = stat.get("color", PRIMARY)
        delta = stat.get("delta")

        delta_html = ""
        if delta is not None and delta != "":
            delta_str = str(delta)
            if delta_str.startswith("+"):
                cls = "positive"
                arrow = "&#9650; "  # ▲
            elif delta_str.startswith("-"):
                cls = "negative"
                arrow = "&#9660; "  # ▼
            else:
                cls = "neutral"
                arrow = ""
            delta_html = (
                f'<span class="lm-hero-delta {cls}">{arrow}{_escape_html(delta_str)}</span>'
            )

        card = f"""
        <div class="lm-hero-card" style="--card-accent: {_escape_html(color)};">
            <div class="lm-hero-icon">{icon}</div>
            <div class="lm-hero-value">{_escape_html(str(value))}</div>
            <div class="lm-hero-label">{_escape_html(str(label))}</div>
            {delta_html}
        </div>"""
        cards_html_parts.append(card)

    grid_html = f'<div class="lm-hero-grid">{"".join(cards_html_parts)}</div>'
    st.markdown(grid_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _escape_html(text: str) -> str:
    """Minimal HTML escaping to prevent XSS while keeping emoji intact."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )
