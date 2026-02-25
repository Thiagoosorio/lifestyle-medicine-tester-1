"""Evidence display components — badges, cards, pyramid, and callouts.

All HTML built as single-line strings (Streamlit markdown parser requirement).
Uses APPLE design tokens from custom_theme.py.
"""

import streamlit as st
from components.custom_theme import APPLE as A
from config.evidence import (
    EVIDENCE_GRADES, STUDY_TYPES, EVIDENCE_PYRAMID,
    JOURNAL_TIERS, RESEARCH_DOMAINS,
)

# ── Evidence Badge (compact inline) ─────────────────────────────────────────

def render_evidence_badge(grade, study_type, year=None):
    """Render a compact inline badge like [A] Meta-analysis (2023)."""
    g = EVIDENCE_GRADES.get(grade, EVIDENCE_GRADES["D"])
    st_info = STUDY_TYPES.get(study_type, {"short": "?", "label": study_type})
    year_str = f" ({year})" if year else ""
    html = (
        f'<span style="display:inline-flex;align-items:center;gap:6px;'
        f'background:rgba(0,0,0,0.3);border:1px solid {g["color"]}40;'
        f'border-radius:6px;padding:2px 8px;font-size:11px;font-weight:600;'
        f'font-family:{A["font_text"]};line-height:16px">'
        f'<span style="color:{g["color"]}">{grade}</span>'
        f'<span style="color:{A["label_secondary"]}">{st_info["label"]}{year_str}</span>'
        f'</span>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_evidence_badge_inline(grade, study_type, year=None):
    """Return badge HTML string (for embedding in other components)."""
    g = EVIDENCE_GRADES.get(grade, EVIDENCE_GRADES["D"])
    st_info = STUDY_TYPES.get(study_type, {"short": "?", "label": study_type})
    year_str = f" ({year})" if year else ""
    return (
        f'<span style="display:inline-flex;align-items:center;gap:6px;'
        f'background:rgba(0,0,0,0.3);border:1px solid {g["color"]}40;'
        f'border-radius:6px;padding:2px 8px;font-size:11px;font-weight:600;'
        f'font-family:{A["font_text"]};line-height:16px">'
        f'<span style="color:{g["color"]}">{grade}</span>'
        f'<span style="color:{A["label_secondary"]}">{st_info["label"]}{year_str}</span>'
        f'</span>'
    )


# ── Journal Tier Badge ─────────────────────────────────────────────────────

def render_journal_tier_badge_inline(tier):
    """Return HTML for a journal quality tier badge (Elite/Q1/Q2/Q3/Q4)."""
    if not tier:
        return ""
    t = JOURNAL_TIERS.get(tier)
    if not t:
        return ""
    flag_icon = " &#9888;" if t.get("flag") else ""
    return (
        f'<span style="display:inline-flex;align-items:center;gap:3px;'
        f'background:{t["color"]}18;border:1px solid {t["color"]}40;'
        f'border-radius:4px;padding:1px 6px;font-size:10px;font-weight:700;'
        f'letter-spacing:0.04em;color:{t["color"]};'
        f'font-family:{A["font_text"]};line-height:14px">'
        f'{t["label"]}{flag_icon}</span>'
    )


def render_domain_badge_inline(domain):
    """Return HTML for a research domain badge."""
    if not domain:
        return ""
    d = RESEARCH_DOMAINS.get(domain)
    label = d["label"] if d else domain.replace("_", " ").title()
    return (
        f'<span style="display:inline-flex;align-items:center;'
        f'background:rgba(0,0,0,0.04);border:1px solid {A["separator"]};'
        f'border-radius:4px;padding:1px 6px;font-size:10px;font-weight:500;'
        f'color:{A["label_tertiary"]};'
        f'font-family:{A["font_text"]};line-height:14px">'
        f'{label}</span>'
    )


# ── Evidence Card (full citation) ───────────────────────────────────────────

def render_evidence_card(evidence, show_details=True):
    """Render a full evidence card with citation details."""
    g = EVIDENCE_GRADES.get(evidence["evidence_grade"], EVIDENCE_GRADES["D"])
    st_info = STUDY_TYPES.get(evidence["study_type"], {"label": evidence["study_type"]})
    badge = render_evidence_badge_inline(
        evidence["evidence_grade"], evidence["study_type"], evidence.get("year")
    )

    # Key finding
    finding_html = ""
    if evidence.get("key_finding"):
        finding_html = (
            f'<div style="font-size:14px;line-height:20px;color:{A["label_primary"]};'
            f'margin-top:8px;padding:8px 12px;background:rgba(0,0,0,0.03);'
            f'border-radius:8px;border-left:2px solid {g["color"]}">'
            f'{evidence["key_finding"]}</div>'
        )

    # Effect size
    effect_html = ""
    if evidence.get("effect_size") and show_details:
        effect_html = (
            f'<div style="font-size:12px;color:{A["label_secondary"]};margin-top:6px">'
            f'<span style="color:{A["label_tertiary"]}">Effect: </span>'
            f'{evidence["effect_size"]}</div>'
        )

    # Sample size
    sample_html = ""
    if evidence.get("sample_size") and show_details:
        n = f"{evidence['sample_size']:,}" if isinstance(evidence["sample_size"], int) else str(evidence["sample_size"])
        sample_html = (
            f'<span style="font-size:11px;color:{A["label_tertiary"]};margin-left:12px">'
            f'N={n}</span>'
        )

    # Dose-response
    dose_html = ""
    if evidence.get("dose_response") and show_details:
        dose_html = (
            f'<div style="font-size:12px;color:{A["teal"]};margin-top:6px;'
            f'font-style:italic">&#x1F4C8; {evidence["dose_response"]}</div>'
        )

    # Causation note
    causation_html = ""
    if evidence.get("causation_note") and show_details:
        causation_html = (
            f'<div style="font-size:11px;color:{A["orange"]};margin-top:6px;'
            f'padding:4px 8px;background:rgba(255,159,10,0.08);border-radius:6px">'
            f'&#9888; {evidence["causation_note"]}</div>'
        )

    # Journal tier + domain badges
    tier_badge = render_journal_tier_badge_inline(evidence.get("journal_tier"))
    domain_badge = render_domain_badge_inline(evidence.get("domain"))
    tier_flag_html = ""
    if evidence.get("journal_tier") in ("q3", "q4"):
        t = JOURNAL_TIERS.get(evidence["journal_tier"], {})
        if t.get("flag"):
            tier_flag_html = (
                f'<div style="font-size:11px;color:{A["orange"]};margin-top:6px;'
                f'padding:4px 8px;background:rgba(255,159,10,0.08);border-radius:6px">'
                f'&#9888; {t["flag"]}</div>'
            )

    # PubMed link
    link_html = ""
    if evidence.get("pmid"):
        link_html = (
            f'<a href="https://pubmed.ncbi.nlm.nih.gov/{evidence["pmid"]}/" '
            f'target="_blank" style="font-size:11px;color:{A["blue"]};'
            f'text-decoration:none;margin-top:6px;display:inline-block">'
            f'PubMed: {evidence["pmid"]} &#8599;</a>'
        )
    elif evidence.get("doi"):
        link_html = (
            f'<a href="https://doi.org/{evidence["doi"]}" '
            f'target="_blank" style="font-size:11px;color:{A["blue"]};'
            f'text-decoration:none;margin-top:6px;display:inline-block">'
            f'DOI: {evidence["doi"]} &#8599;</a>'
        )

    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_lg"]};padding:16px;margin-bottom:12px;'
        f'transition:border-color 0.25s">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;'
        f'flex-wrap:wrap;gap:8px">'
        f'<div style="flex:1;min-width:200px">'
        f'<div style="font-family:{A["font_display"]};font-size:14px;font-weight:600;'
        f'color:{A["label_primary"]};line-height:18px">{evidence["title"]}</div>'
        f'<div style="font-size:12px;color:{A["label_tertiary"]};margin-top:4px">'
        f'{evidence.get("authors", "")}'
        f' &middot; <em>{evidence.get("journal", "")}</em>'
        f'{sample_html}</div>'
        f'<div style="display:flex;gap:6px;margin-top:6px;flex-wrap:wrap">'
        f'{tier_badge}{domain_badge}</div>'
        f'</div>'
        f'<div>{badge}</div>'
        f'</div>'
        f'{finding_html}'
        f'{effect_html}'
        f'{dose_html}'
        f'{causation_html}'
        f'{tier_flag_html}'
        f'<div style="margin-top:8px">{link_html}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ── Evidence Pyramid ────────────────────────────────────────────────────────

def render_evidence_pyramid():
    """Render the evidence hierarchy as a visual pyramid."""
    layers = ""
    for level in EVIDENCE_PYRAMID:
        g = EVIDENCE_GRADES[level["grade"]]
        layers += (
            f'<div style="width:{level["width"]}%;margin:0 auto 4px auto;'
            f'background:linear-gradient(90deg,{g["color"]}20,{g["color"]}08);'
            f'border:1px solid {g["color"]}30;border-radius:8px;padding:10px 16px;'
            f'text-align:center">'
            f'<div style="font-size:13px;font-weight:600;color:{g["color"]}">'
            f'{level["label"]}</div>'
            f'<div style="font-size:11px;color:{A["label_tertiary"]};margin-top:2px">'
            f'{level["description"]}</div>'
            f'</div>'
        )
    html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_xl"]};padding:24px;margin-bottom:16px">'
        f'<div style="font-family:{A["font_display"]};font-size:17px;font-weight:600;'
        f'color:{A["label_primary"]};text-align:center;margin-bottom:16px">'
        f'Evidence Hierarchy</div>'
        f'<div style="font-size:12px;color:{A["label_tertiary"]};text-align:center;'
        f'margin-bottom:16px">Stronger evidence at the top, weaker at the bottom</div>'
        f'{layers}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ── Dose-Response Note ──────────────────────────────────────────────────────

def render_dose_response_note(text):
    """Styled callout box for dose-response information."""
    html = (
        f'<div style="background:rgba(30,200,198,0.06);border:1px solid rgba(30,200,198,0.2);'
        f'border-radius:{A["radius_md"]};padding:12px 16px;margin:8px 0">'
        f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.06em;color:{A["teal"]};margin-bottom:4px">'
        f'&#x1F4C8; Dose-Response</div>'
        f'<div style="font-size:13px;line-height:18px;color:{A["label_secondary"]}">'
        f'{text}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ── Causation Warning ───────────────────────────────────────────────────────

def render_causation_warning(note):
    """Amber callout distinguishing correlation vs causation."""
    html = (
        f'<div style="background:rgba(255,159,10,0.06);border:1px solid rgba(255,159,10,0.2);'
        f'border-radius:{A["radius_md"]};padding:12px 16px;margin:8px 0">'
        f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.06em;color:{A["orange"]};margin-bottom:4px">'
        f'&#9888; Correlation vs Causation</div>'
        f'<div style="font-size:13px;line-height:18px;color:{A["label_secondary"]}">'
        f'{note}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ── Evidence Summary Strip ──────────────────────────────────────────────────

def render_evidence_summary_strip(stats):
    """Render a compact strip showing evidence counts by grade."""
    parts = ""
    for grade_key in ["A", "B", "C", "D"]:
        count = stats.get("by_grade", {}).get(grade_key, 0)
        if count == 0:
            continue
        g = EVIDENCE_GRADES[grade_key]
        parts += (
            f'<div style="display:flex;align-items:center;gap:4px">'
            f'<span style="width:8px;height:8px;border-radius:50%;'
            f'background:{g["color"]};display:inline-block"></span>'
            f'<span style="font-size:12px;color:{A["label_secondary"]}">'
            f'{count} {g["name"]}</span>'
            f'</div>'
        )
    # Tier breakdown
    tier_parts = ""
    for tier_key in ["elite", "q1", "q2", "q3", "q4"]:
        count = stats.get("by_tier", {}).get(tier_key, 0)
        if count == 0:
            continue
        t = JOURNAL_TIERS[tier_key]
        tier_parts += (
            f'<div style="display:flex;align-items:center;gap:4px">'
            f'<span style="width:8px;height:8px;border-radius:50%;'
            f'background:{t["color"]};display:inline-block"></span>'
            f'<span style="font-size:12px;color:{A["label_secondary"]}">'
            f'{count} {t["label"]}</span>'
            f'</div>'
        )
    html = (
        f'<div style="display:flex;gap:16px;align-items:center;'
        f'padding:8px 0;flex-wrap:wrap">'
        f'<span style="font-size:13px;font-weight:600;color:{A["label_primary"]}">'
        f'{stats.get("total", 0)} Studies</span>'
        f'{parts}'
        f'</div>'
    )
    if tier_parts:
        html += (
            f'<div style="display:flex;gap:16px;align-items:center;'
            f'padding:4px 0;flex-wrap:wrap">'
            f'<span style="font-size:12px;font-weight:500;color:{A["label_tertiary"]}">'
            f'Journal Tiers:</span>'
            f'{tier_parts}'
            f'</div>'
        )
    st.markdown(html, unsafe_allow_html=True)
