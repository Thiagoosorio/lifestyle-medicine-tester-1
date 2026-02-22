"""Research Library — Browse, search, and explore the evidence behind every recommendation."""

import streamlit as st
from components.custom_theme import APPLE, render_hero_banner, render_section_header
from components.evidence_display import (
    render_evidence_card,
    render_evidence_pyramid,
    render_evidence_summary_strip,
    render_evidence_badge_inline,
)
from config.settings import PILLARS
from config.evidence import EVIDENCE_GRADES, STUDY_TYPES, JOURNAL_TIERS, RESEARCH_DOMAINS
from services.evidence_service import (
    get_evidence_for_pillar,
    get_all_evidence,
    search_evidence,
    get_evidence_stats,
    get_evidence_for_entity,
    get_evidence_for_domain,
)
from services.protocol_service import (
    get_all_protocols,
    get_protocol_by_id,
    adopt_protocol,
    is_protocol_adopted,
)

A = APPLE
user_id = st.session_state.user_id

render_hero_banner(
    "Research Library",
    "Every recommendation backed by peer-reviewed science. Browse studies by pillar, search the evidence, or explore our protocol library."
)

# ── Stats Strip ───────────────────────────────────────────────────────────
stats = get_evidence_stats()
render_evidence_summary_strip(stats)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════
tab_browse, tab_domain, tab_search, tab_hierarchy, tab_protocols = st.tabs([
    "Browse by Pillar", "Browse by Domain", "Search", "Evidence Hierarchy", "Protocol Library"
])

# ── Tab 1: Browse by Pillar ───────────────────────────────────────────────
with tab_browse:
    # Pillar filter
    pillar_options = ["All Pillars"] + [PILLARS[pid]["display_name"] for pid in sorted(PILLARS.keys())]
    selected_pillar = st.selectbox("Filter by Pillar", pillar_options, key="browse_pillar")

    # Grade filter
    grade_options = ["All Grades"] + [f"Grade {g}: {info['name']}" for g, info in EVIDENCE_GRADES.items()]
    selected_grade = st.selectbox("Filter by Evidence Grade", grade_options, key="browse_grade")

    # Resolve filters
    grade_filter = None
    if selected_grade != "All Grades":
        grade_filter = selected_grade.split(":")[0].replace("Grade ", "").strip()

    if selected_pillar == "All Pillars":
        evidences = get_all_evidence(grade=grade_filter)
    else:
        pid = next(pid for pid, p in PILLARS.items() if p["display_name"] == selected_pillar)
        evidences = get_evidence_for_pillar(pid, grade=grade_filter)

    if not evidences:
        st.caption("No studies found for the selected filters.")
    else:
        st.caption(f"Showing {len(evidences)} studies")
        for ev in evidences:
            render_evidence_card(ev)

# ── Tab 2: Browse by Domain ─────────────────────────────────────────────────
with tab_domain:
    domain_options = ["All Domains"] + [d["label"] for d in RESEARCH_DOMAINS.values()]
    selected_domain = st.selectbox("Filter by Research Domain", domain_options, key="browse_domain")

    # Grade filter for domain tab
    domain_grade_options = ["All Grades"] + [f"Grade {g}: {info['name']}" for g, info in EVIDENCE_GRADES.items()]
    selected_domain_grade = st.selectbox("Filter by Evidence Grade", domain_grade_options, key="domain_grade")

    domain_grade_filter = None
    if selected_domain_grade != "All Grades":
        domain_grade_filter = selected_domain_grade.split(":")[0].replace("Grade ", "").strip()

    if selected_domain == "All Domains":
        domain_evidences = get_all_evidence(grade=domain_grade_filter)
    else:
        domain_key = next(k for k, v in RESEARCH_DOMAINS.items() if v["label"] == selected_domain)
        domain_evidences = get_evidence_for_domain(domain_key, grade=domain_grade_filter)

    if not domain_evidences:
        st.caption("No studies found for the selected filters.")
    else:
        st.caption(f"Showing {len(domain_evidences)} studies")
        for ev in domain_evidences:
            render_evidence_card(ev)

# ── Tab 3: Search ─────────────────────────────────────────────────────────
with tab_search:
    query = st.text_input("Search studies by keyword", placeholder="e.g., Mediterranean diet, MBSR, sleep duration...")
    if query:
        results = search_evidence(query)
        if results:
            st.caption(f"Found {len(results)} studies matching \"{query}\"")
            for ev in results:
                render_evidence_card(ev)
        else:
            st.caption(f"No studies found for \"{query}\".")
    else:
        st.caption("Enter a keyword to search across titles, summaries, findings, and tags.")

# ── Tab 3: Evidence Hierarchy ─────────────────────────────────────────────
with tab_hierarchy:
    render_evidence_pyramid()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    render_section_header("How We Grade Evidence", "Understanding the quality levels")

    for grade_key, grade_info in EVIDENCE_GRADES.items():
        grade_html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-left:3px solid {grade_info["color"]};'
            f'border-radius:{A["radius_md"]};padding:16px;margin-bottom:12px">'
            f'<div style="display:flex;align-items:center;gap:8px">'
            f'<span style="font-size:20px;color:{grade_info["color"]}">{grade_info["icon"]}</span>'
            f'<div>'
            f'<div style="font-family:{A["font_display"]};font-size:15px;font-weight:600;'
            f'color:{grade_info["color"]}">{grade_info["label"]}: {grade_info["name"]}</div>'
            f'<div style="font-size:13px;color:{A["label_secondary"]};margin-top:2px">'
            f'{grade_info["description"]}</div>'
            f'</div>'
            f'</div>'
            f'</div>'
        )
        st.markdown(grade_html, unsafe_allow_html=True)

    # Journal Quality Tiers explainer
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    render_section_header("Journal Quality Tiers", "Not all journals are equal")

    for tier_key, tier_info in JOURNAL_TIERS.items():
        flag_html = ""
        if tier_info.get("flag"):
            flag_html = (
                f'<div style="font-size:12px;color:{A["orange"]};margin-top:4px;'
                f'font-style:italic">&#9888; {tier_info["flag"]}</div>'
            )
        tier_html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
            f'border-left:3px solid {tier_info["color"]};'
            f'border-radius:{A["radius_md"]};padding:14px;margin-bottom:10px">'
            f'<div style="display:flex;align-items:center;gap:8px">'
            f'<span style="font-size:14px;font-weight:700;color:{tier_info["color"]};'
            f'min-width:40px">{tier_info["label"]}</span>'
            f'<span style="font-size:13px;color:{A["label_secondary"]}">'
            f'{tier_info["description"]}</span>'
            f'</div>'
            f'{flag_html}'
            f'</div>'
        )
        st.markdown(tier_html, unsafe_allow_html=True)

    # Correlation vs Causation explainer
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    render_section_header("Correlation vs Causation", "A critical distinction")
    explainer_html = (
        f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
        f'border-radius:{A["radius_xl"]};padding:20px;margin-bottom:16px">'
        f'<div style="font-size:14px;line-height:22px;color:{A["label_secondary"]}">'
        f'<span style="color:{A["green"]};font-weight:600">Causation</span> means one thing '
        f'directly causes another (proven through RCTs). '
        f'<span style="color:{A["orange"]};font-weight:600">Correlation</span> means two things '
        f'occur together but one may not cause the other (found in observational studies).'
        f'<br><br>'
        f'We mark each study with a '
        f'<span style="color:{A["orange"]}">&#9888;</span> warning when the evidence shows '
        f'correlation only, so you can interpret findings appropriately.'
        f'</div>'
        f'</div>'
    )
    st.markdown(explainer_html, unsafe_allow_html=True)

# ── Tab 4: Protocol Library ──────────────────────────────────────────────
with tab_protocols:
    render_section_header("Science-Backed Protocols", "Daily routines grounded in research")

    protocols = get_all_protocols()

    # Group by pillar
    pillar_proto_options = ["All Pillars"] + [PILLARS[pid]["display_name"] for pid in sorted(PILLARS.keys())]
    selected_proto_pillar = st.selectbox("Filter by Pillar", pillar_proto_options, key="proto_pillar")

    if selected_proto_pillar != "All Pillars":
        pid = next(pid for pid, p in PILLARS.items() if p["display_name"] == selected_proto_pillar)
        protocols = [p for p in protocols if p["pillar_id"] == pid]

    if not protocols:
        st.caption("No protocols available for the selected pillar.")
    else:
        for proto in protocols:
            pillar = PILLARS.get(proto["pillar_id"], {})
            pillar_name = pillar.get("display_name", "")
            pillar_color = pillar.get("color", A["blue"])
            difficulty_stars = "&#9733;" * proto["difficulty"] + "&#9734;" * (3 - proto["difficulty"])
            adopted = is_protocol_adopted(user_id, proto["id"])

            # Status badge
            status_badge = ""
            if adopted:
                status_badge = (
                    f'<span style="background:{A["green"]}20;color:{A["green"]};'
                    f'font-size:11px;font-weight:600;padding:2px 8px;'
                    f'border-radius:4px;margin-left:8px">ADOPTED</span>'
                )

            # Timing badge
            timing_html = ""
            if proto.get("timing"):
                timing_html = (
                    f'<span style="font-size:11px;color:{A["label_tertiary"]};'
                    f'margin-right:12px">&#128337; {proto["timing"]}</span>'
                )

            # Duration badge
            duration_html = ""
            if proto.get("duration"):
                duration_html = (
                    f'<span style="font-size:11px;color:{A["label_tertiary"]}">'
                    f'&#9203; {proto["duration"]}</span>'
                )

            # Get linked evidence
            linked_evidence = get_evidence_for_entity("protocol", proto["id"])
            evidence_count_html = ""
            if linked_evidence:
                evidence_count_html = (
                    f'<span style="font-size:11px;color:{A["blue"]};margin-left:8px">'
                    f'&#128218; {len(linked_evidence)} studies</span>'
                )

            card_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                f'border-left:3px solid {pillar_color};'
                f'border-radius:{A["radius_lg"]};padding:16px;margin-bottom:12px">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap">'
                f'<div style="flex:1;min-width:200px">'
                f'<div style="font-family:{A["font_display"]};font-size:15px;font-weight:600;'
                f'color:{A["label_primary"]}">{proto["name"]}{status_badge}</div>'
                f'<div style="font-size:11px;color:{pillar_color};font-weight:600;'
                f'text-transform:uppercase;letter-spacing:0.06em;margin-top:4px">'
                f'{pillar_name} &middot; {difficulty_stars}{evidence_count_html}</div>'
                f'</div>'
                f'<div style="font-size:12px;color:{A["label_tertiary"]}">'
                f'{timing_html}{duration_html}</div>'
                f'</div>'
                f'<div style="font-size:13px;line-height:18px;color:{A["label_secondary"]};'
                f'margin-top:8px">{proto["description"]}</div>'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

            with st.expander(f"Why it works: {proto['name']}"):
                if proto.get("mechanism"):
                    st.markdown(f"**Mechanism:** {proto['mechanism']}")
                if proto.get("expected_benefit"):
                    st.markdown(f"**Expected Benefit:** {proto['expected_benefit']}")
                if proto.get("contraindications"):
                    st.warning(f"**Contraindications:** {proto['contraindications']}")

                # Show linked evidence
                if linked_evidence:
                    st.markdown("**Supporting Research:**")
                    for ev in linked_evidence:
                        render_evidence_card(ev, show_details=False)

                # Adopt button
                if not adopted:
                    if st.button(f"Adopt This Protocol", key=f"adopt_{proto['id']}", use_container_width=True):
                        adopt_protocol(user_id, proto["id"])
                        st.toast(f"Protocol \"{proto['name']}\" adopted!")
                        st.rerun()
                else:
                    st.success("You're already following this protocol.")
