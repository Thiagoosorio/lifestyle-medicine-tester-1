"""Premium, client-shareable CPET report — self-contained HTML (inline CSS + SVG).

Downloadable and print-to-PDF from any browser; no external libraries, fonts, or
native dependencies (deploy-safe). Built from the same data as the coach view
(services.cpet_service.build_cpet_coach_summary), rendered summary-first and
prescriptive per the researched design spec.
"""

from __future__ import annotations

import html
from typing import Any

from services.cpet_service import (
    ZONE2_CORE_WIDTH_BPM,
    ZONE2_TARGET_OFFSET_BPM,
    build_cpet_coach_summary,
)

ZONE_COLORS = ["#1F9E7A", "#7FC24B", "#F4C430", "#EF7D2B", "#D7263D"]
ZONE_NAMES = ["Z1 Recovery", "Z2 Endurance", "Z3 Tempo", "Z4 Threshold", "Z5 VO2max"]
ZONE_RPE = ["1-2 / very easy", "3-4 / conversational", "5-6 / comfortably hard", "7-8 / hard", "9-10 / max"]
ZONE_FEEL = [
    "Recovery only; barely working.",
    "Full sentences, nose-breathing possible — the base you build on.",
    "Talking gets choppy; the 'grey zone' — use sparingly.",
    "A few words at a time; the lever that raises your red-line.",
    "No talking; short, maximal efforts.",
]
ZONE_ADAPT = [
    "Active recovery, blood flow, warm-up/cool-down.",
    "Mitochondria + fat oxidation. Most weekly hours live here.",
    "Aerobic-threshold work; fatiguing for the adaptation it gives.",
    "Lifts the anaerobic threshold (VT2) — your sustainable ceiling.",
    "Maximal aerobic power and anaerobic capacity.",
]


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _r0(x: float | None) -> str:
    return "--" if x is None else f"{round(x)}"


def _r1(x: float | None) -> str:
    return "--" if x is None else f"{x:.1f}"


def _r2(x: float | None) -> str:
    return "--" if x is None else f"{x:.2f}"


def _r5(x: float | None) -> str:
    return "--" if x is None else f"{int(round(x / 5.0) * 5)}"


# ── inline SVG components ────────────────────────────────────────────────────

def _zone_bar_svg(chart: dict, z2: dict, has_power: bool) -> str:
    hr = chart.get("hr")
    if not hr or hr.get("vt1") is None or hr.get("vt2") is None:
        return ""
    power = chart.get("power") or {}
    floor, vt1, mid, vt2, peak = hr["floor"], hr["vt1"], hr["mid"], hr["vt2"], hr["peak"]
    if floor is None:
        floor = vt1 - 12
    XL, PW = 24.0, 652.0
    dmin = min(round(0.55 * peak), floor - 6)
    dmax = max(peak, vt2 + 6)
    span = max(1.0, dmax - dmin)

    def x(v):
        return XL + (v - dmin) / span * PW

    bar_y, bar_h = 66.0, 52.0
    edges = [dmin, floor, vt1, mid, vt2, dmax]
    p_edges = None
    if power and power.get("vt1") is not None:
        p_edges = [None, power["floor"], power["vt1"], power["mid"], power["vt2"], None]
    parts = ['<svg viewBox="0 0 700 168" role="img" aria-label="Training zones by heart rate">']
    for i in range(5):
        x0, x1 = x(edges[i]), x(edges[i + 1])
        w = max(0.5, x1 - x0)
        parts.append(f'<rect x="{x0:.1f}" y="{bar_y}" width="{w:.1f}" height="{bar_h}" fill="{ZONE_COLORS[i]}"/>')
        cx = x0 + w / 2
        parts.append(f'<text x="{cx:.1f}" y="{bar_y+20:.1f}" text-anchor="middle" font-size="10" font-weight="700" fill="#14181F">{_esc(ZONE_NAMES[i])}</text>')
        lo = "" if i == 0 else f"{round(edges[i])}"
        hi = "" if i == 4 else f"{round(edges[i+1])}"
        rng = f"&lt;{round(floor)}" if i == 0 else (f"&ge;{round(vt2)}" if i == 4 else f"{lo}-{hi}")
        parts.append(f'<text x="{cx:.1f}" y="{bar_y+34:.1f}" text-anchor="middle" font-size="9" fill="#14181F">{rng} bpm</text>')
        if p_edges:
            plo = p_edges[i] if i > 0 else None
            phi = p_edges[i + 1] if i < 4 else None
            ptxt = f"&lt;{plo}W" if i == 0 else (f"&ge;{p_edges[4]}W" if i == 4 else f"{plo}-{phi}W")
            parts.append(f'<text x="{cx:.1f}" y="{bar_y+46:.1f}" text-anchor="middle" font-size="8" fill="#3A4049">{ptxt}</text>')
    # Zone 2 target band overlay
    z2_lo = hr.get("fatmax_low") or floor
    parts.append(f'<rect x="{x(z2_lo):.1f}" y="{bar_y}" width="{x(vt1)-x(z2_lo):.1f}" height="{bar_h}" fill="#14181F" fill-opacity="0.05" stroke="#14181F" stroke-opacity="0.35" stroke-dasharray="3 2"/>')
    parts.append(f'<text x="{(x(z2_lo)+x(vt1))/2:.1f}" y="{bar_y-6:.1f}" text-anchor="middle" font-size="9" font-weight="700" fill="#0A5C5B">Zone 2 target</text>')
    # threshold markers
    for hrv, lbl in ((vt1, "VT1 / LT1"), (vt2, "VT2 / LT2")):
        anchor = "start" if hrv == vt1 else "end"
        dx = 3 if hrv == vt1 else -3
        parts.append(f'<line x1="{x(hrv):.1f}" y1="{bar_y-2:.1f}" x2="{x(hrv):.1f}" y2="{bar_y+bar_h+6:.1f}" stroke="#14181F" stroke-width="1.25" stroke-dasharray="3 2"/>')
        parts.append(f'<text x="{x(hrv)+dx:.1f}" y="{bar_y+bar_h+18:.1f}" text-anchor="{anchor}" font-size="9" font-weight="700" fill="#14181F">{lbl} · {round(hrv)} bpm</text>')
    # FatMax point
    fm = _num(chart.get("hr", {}).get("fatmax_low"))
    fm_hr = _num(z2.get("fatmax_vt1_gap"))
    fatmax_hr = None
    if hr.get("fatmax_low") is not None and hr.get("fatmax_high") is not None:
        fatmax_hr = (hr["fatmax_low"] + hr["fatmax_high"]) / 2
    if fatmax_hr is not None:
        fx = x(fatmax_hr)
        parts.append(f'<polygon points="{fx-5:.1f},{bar_y-9:.1f} {fx+5:.1f},{bar_y-9:.1f} {fx:.1f},{bar_y:.1f}" fill="#E8A13A"/>')
        parts.append(f'<text x="{fx:.1f}" y="{bar_y-13:.1f}" text-anchor="middle" font-size="8" fill="#8a5a0a">FatMax</text>')
    # peak caret
    parts.append(f'<text x="{x(peak):.1f}" y="{bar_y+bar_h+18:.1f}" text-anchor="end" font-size="9" fill="#6B7280">Peak {round(peak)}</text>')
    # axis ticks
    step = 10 if span <= 90 else 20
    t = int((dmin // step + 1) * step)
    while t < dmax:
        parts.append(f'<line x1="{x(t):.1f}" y1="{bar_y+bar_h:.1f}" x2="{x(t):.1f}" y2="{bar_y+bar_h+4:.1f}" stroke="#C9C9C2"/>')
        parts.append(f'<text x="{x(t):.1f}" y="{bar_y+bar_h+30:.1f}" text-anchor="middle" font-size="8" fill="#9aa0a6">{t}</text>')
        t += step
    parts.append("</svg>")
    return "".join(parts)


def _percentile_bullet_svg(fitness: dict) -> str:
    pct = _num(fitness.get("percentile"))
    if pct is None:
        return ""
    XL, W = 24.0, 536.0

    def x(p):
        return XL + max(0.0, min(100.0, p)) / 100.0 * W

    bands = [(0, 20, "#D8E6E5", "Poor"), (20, 40, "#B6D4D2", "Fair"), (40, 60, "#8FBFBD", "Average"),
             (60, 80, "#57A3A1", "Good"), (80, 95, "#2A8785", "Excellent"), (95, 100, "#0E7C7B", "Superior")]
    y, h = 34.0, 20.0
    parts = ['<svg viewBox="0 0 584 92" role="img" aria-label="Aerobic fitness percentile versus age and sex norms">']
    for lo, hi, col, name in bands:
        parts.append(f'<rect x="{x(lo):.1f}" y="{y}" width="{x(hi)-x(lo):.1f}" height="{h}" fill="{col}"/>')
        if hi - lo >= 15:
            tc = "#0A5C5B" if lo >= 60 else "#5a6b6a"
            parts.append(f'<text x="{(x(lo)+x(hi))/2:.1f}" y="{y+h/2+3:.1f}" text-anchor="middle" font-size="7.5" fill="{tc}">{name}</text>')
    # 0-100 axis ticks
    for p in (0, 20, 40, 60, 80, 100):
        parts.append(f'<text x="{x(p):.1f}" y="{y+h+13:.1f}" text-anchor="middle" font-size="8" fill="#9aa0a6">{p}</text>')
    parts.append(f'<text x="{XL+W/2:.1f}" y="{y+h+26:.1f}" text-anchor="middle" font-size="8" fill="#9aa0a6">percentile vs age &amp; sex</text>')
    # median tick
    parts.append(f'<line x1="{x(50):.1f}" y1="{y-4:.1f}" x2="{x(50):.1f}" y2="{y+h+2:.1f}" stroke="#14181F" stroke-width="1.5"/>')
    parts.append(f'<text x="{x(50):.1f}" y="{y-8:.1f}" text-anchor="middle" font-size="8" fill="#6B7280">median</text>')
    # measure bar + endpoint marker with value callout (offset from median to avoid collision)
    parts.append(f'<rect x="{XL:.1f}" y="{y+6:.1f}" width="{max(0.0, x(pct)-XL):.1f}" height="8" rx="4" fill="#14181F"/>')
    parts.append(f'<circle cx="{x(pct):.1f}" cy="{y+10:.1f}" r="6" fill="#14181F" stroke="#FFFFFF" stroke-width="1.5"/>')
    cval = _esc(fitness.get("percentile_label", "").replace("~", ""))
    if abs(pct - 50) >= 12:
        parts.append(f'<text x="{x(pct):.1f}" y="{y-8:.1f}" text-anchor="middle" font-size="11" font-weight="700" fill="#0A5C5B">{cval}</text>')
    parts.append("</svg>")
    return "".join(parts)


# ── copy / interpretation ────────────────────────────────────────────────────

_CHIP_COLORS = {"pass": "#18733A", "caution": "#765100", "alert": "#A51D2D",
                "accent": "#0A6665", "good": "#176D6B", "muted": "#555D68"}


def _chip(text: str, kind: str = "muted") -> str:
    if not text:
        return ""
    return f'<span class="chip" style="background:{_CHIP_COLORS.get(kind, "#6B7280")}">{_esc(text)}</span>'


def _norm_citation(fitness: dict) -> str:
    ref = (fitness.get("reference") or "").lower()
    if "cycle" in ref:
        return ("FRIEND registry cycle-ergometry reference standards "
                "(Kaminsky, de Souza e Silva et al., Mayo Clin Proc 2017)")
    if "treadmill" in ref:
        return ("FRIEND registry / ACSM treadmill reference standards "
                "(Kaminsky et al., Mayo Clin Proc 2015; ACSM Guidelines, 11th ed.)")
    return fitness.get("reference") or "population reference standards (FRIEND / ACSM)"


def _fitness_kind(fitness: dict | None) -> str:
    pct = _num((fitness or {}).get("percentile"))
    if pct is None:
        return "muted"
    return "accent" if pct >= 75 else ("good" if pct >= 55 else ("caution" if pct >= 25 else "alert"))


def _arena_label(slope: float | None) -> str:
    if slope is None:
        return ""
    if slope >= 45:
        return "Class IV"
    if slope >= 36:
        return "Class III"
    if slope >= 30:
        return "Class II"
    return "Class I (efficient)"


def _arena_kind(slope: float | None) -> str:
    if slope is None:
        return "muted"
    return "alert" if slope >= 36 else ("caution" if slope >= 30 else "pass")


def _primary_limiter(metrics: dict) -> tuple[str, str]:
    br = _num(metrics.get("breathing_reserve_pct"))
    spo2 = _num(metrics.get("spo2_nadir_pct"))
    o2p = _num(metrics.get("o2_pulse_pct_pred"))
    slope = _num(metrics.get("ve_vco2_slope"))
    if br is not None and br < 15 and spo2 is not None and spo2 < 94:
        return ("ventilatory / pulmonary", "breathing reached its ceiling with oxygen desaturation")
    if o2p is not None and o2p < 80:
        return ("central / cardiac (oxygen delivery)", "the stroke-volume proxy (O2 pulse) is low")
    if slope is not None and slope >= 36:
        return ("ventilatory efficiency (clinician review)", "the VE/VCO2 slope is elevated")
    return ("peripheral / metabolic — the muscles' ability to use oxygen",
            "the heart and lungs kept healthy reserve, so the trainable gap is in the muscle")


def _headline(fitness: dict | None, metrics: dict) -> str:
    pct = _num((fitness or {}).get("percentile"))
    engine = "developing"
    if pct is not None:
        engine = "powerful" if pct >= 80 else ("strong" if pct >= 60 else ("solid" if pct >= 40 else "developing"))
    vt2_pct = _num(metrics.get("vt2_pct_peak_vo2"))
    gap = ("with thresholds already high — the next gains are durability, economy and fueling"
           if (vt2_pct is not None and vt2_pct >= 85) else "with clear room to raise your red-line")
    return f"A {engine} aerobic engine, {gap}."


def _tile(label: str, big: str, unit: str, sub: str = "", chip: str = "") -> str:
    return (f'<div class="card kpi"><div class="kpi__label">{_esc(label)}</div>'
            f'<div class="kpi__val">{big}<span class="kpi__unit">{_esc(unit)}</span></div>'
            f'<div class="small">{sub} {chip}</div></div>')


def _kpi_tiles(metrics: dict, summary: dict, has_power: bool) -> str:
    fitness = summary.get("fitness_classification") or {}
    metab = summary.get("metabolic_profile") or {}
    rel, ab, pct_pred = _num(metrics.get("peak_vo2_ml_kg_min")), _num(metrics.get("peak_vo2_l_min")), _num(metrics.get("peak_vo2_pct_pred"))
    vt1_hr, vt1_pw, vt1_pk = _num(metrics.get("vt1_hr_bpm")), _num(metrics.get("vt1_power_w")), _num(metrics.get("vt1_pct_peak_vo2"))
    vt2_hr, vt2_pw, vt2_pk = _num(metrics.get("vt2_hr_bpm")), _num(metrics.get("vt2_power_w")), _num(metrics.get("vt2_pct_peak_vo2"))
    peak_pw = _num(metrics.get("peak_power_w"))
    mfo, fatmax_hr = _num(metrics.get("fatmax_g_min")), _num(metrics.get("fatmax_hr_bpm"))
    slope = _num(metrics.get("ve_vco2_slope"))
    tiles = []
    vo2_sub = f"{_r2(ab)} L/min · {_r0(pct_pred)}% pred" if ab else f"{_r0(pct_pred)}% pred"
    fit_chip = _chip(f"{fitness.get('percentile_label','')} · {fitness.get('category','')}", _fitness_kind(fitness)) if fitness.get("percentile") is not None else ""
    tiles.append(_tile("VO2peak", _r1(rel), "mL/kg/min", vo2_sub, fit_chip))
    vt1_sub = f"{_r0(vt1_hr)} bpm" + (f" · {_r5(vt1_pw)} W" if (has_power and vt1_pw) else "") + (f" · {_r0(vt1_pk)}% VO2peak" if vt1_pk else "")
    tiles.append(_tile("Aerobic threshold (VT1/LT1)", _r0(vt1_hr), "bpm", vt1_sub))
    vt2_sub = f"{_r0(vt2_hr)} bpm" + (f" · {_r5(vt2_pw)} W" if (has_power and vt2_pw) else "") + (f" · {_r0(vt2_pk)}% VO2peak" if vt2_pk else "")
    tiles.append(_tile("Red-line (VT2/LT2)", _r0(vt2_hr), "bpm", vt2_sub))
    if has_power and peak_pw:
        tiles.append(_tile("Peak work rate", _r5(peak_pw), "W", "maximal aerobic power"))
    if mfo is not None or fatmax_hr is not None:
        tiles.append(_tile("FatMax", _r0(fatmax_hr), "bpm", f"{_r2(mfo)} g fat/min", _chip(metab.get("mfo_class", ""), "good")))
    if slope is not None:
        tiles.append(_tile("Ventilatory efficiency", _r1(slope), "VE/VCO2", "", _chip(_arena_label(slope), _arena_kind(slope))))
    return f'<div class="kpi-row">{"".join(tiles)}</div>'


def _effort_badge(metrics: dict) -> str:
    rer, hr_pct, br = _num(metrics.get("peak_rer")), _num(metrics.get("hr_pct_pred")), _num(metrics.get("breathing_reserve_pct"))
    ok_rer = rer is not None and rer >= 1.10
    ok_hr = hr_pct is None or hr_pct >= 90
    passed = ok_rer and ok_hr
    rows = []
    def row(ok, txt):
        g = '<span style="color:#2E9E5B">&#10003;</span>' if ok else '<span style="color:#E0A100">!</span>'
        return f"<li>{g} {txt}</li>"
    if rer is not None:
        rows.append(row(ok_rer, f"Peak RER <b>{_r2(rer)}</b> ({'meets' if ok_rer else 'below'} the 1.10 maximal-effort mark)"))
    if hr_pct is not None:
        rows.append(row(hr_pct >= 90, f"Peak HR <b>{_r0(hr_pct)}% of predicted</b>"))
    if br is not None:
        rows.append(row(True, f"Breathing reserve <b>{_r0(br)}%</b>"))
    chip = _chip("Maximal effort confirmed", "pass") if passed else _chip("Interpret with care", "caution")
    return f'<div class="card"><div class="card-title">Test quality {chip}</div><ul class="checks">{"".join(rows)}</ul></div>'


def _threshold_ladder(metrics: dict, has_power: bool) -> str:
    def cells(hr, pw, vo2, pk, name, meaning, dot):
        p = f"{_r5(pw)} W" if (has_power and pw is not None) else "--"
        return (f'<tr><td><span class="dot" style="background:{dot}"></span>{_esc(name)}</td>'
                f'<td class="num">{_r0(hr)}</td><td class="num">{p}</td><td class="num">{_r1(vo2)}</td>'
                f'<td class="num">{_r0(pk)}</td><td class="small">{_esc(meaning)}</td></tr>')
    rows = [cells(_num(metrics.get("vt1_hr_bpm")), _num(metrics.get("vt1_power_w")), _num(metrics.get("vt1_vo2_ml_kg_min")), _num(metrics.get("vt1_pct_peak_vo2")), "VT1 / LT1 (aerobic threshold)", "all-day pace; ~2 mmol lactate line", "#1F9E7A")]
    fm = _num(metrics.get("fatmax_hr_bpm"))
    if fm is not None:
        rows.append(cells(fm, None, None, None, "FatMax", "peak fat-burning; floor of Zone 2", "#E8A13A"))
    rows.append(cells(_num(metrics.get("vt2_hr_bpm")), _num(metrics.get("vt2_power_w")), _num(metrics.get("vt2_vo2_ml_kg_min")), _num(metrics.get("vt2_pct_peak_vo2")), "VT2 / LT2 (red-line)", "the wall; ~4 mmol lactate line", "#EF7D2B"))
    rows.append(cells(_num(metrics.get("peak_hr_bpm")), _num(metrics.get("peak_power_w")), _num(metrics.get("peak_vo2_ml_kg_min")), 100, "VO2peak", "your ceiling", "#D7263D"))
    return ('<table><thead><tr><th scope="col">Milestone</th><th scope="col" class="num">HR</th>'
            '<th scope="col" class="num">Power</th><th scope="col" class="num">VO2</th>'
            '<th scope="col" class="num">%peak</th><th scope="col">What it is</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>')


def _zone_table(summary: dict, has_power: bool) -> str:
    zt = (summary.get("training_zones") or {}).get("zone_table") or []
    rows = []
    for i, r in enumerate(zt):
        col = ZONE_COLORS[i] if i < len(ZONE_COLORS) else "#999"
        pw = r.get("Power (W)", "--") if has_power else "--"
        emphasis = ' style="background:#0E7C7B12"' if i == 1 else ""
        rows.append(
            f'<tr{emphasis}><td><span class="dot" style="background:{col}"></span><b>{_esc(r.get("Zone",""))}</b></td>'
            f'<td class="num">{_esc(r.get("HR (bpm)","--"))}</td><td class="num">{_esc(pw)}</td>'
            f'<td class="small">{_esc(ZONE_RPE[i] if i < 5 else "")}</td>'
            f'<td class="small">{_esc(ZONE_FEEL[i] if i < 5 else "")}</td>'
            f'<td class="small">{_esc(ZONE_ADAPT[i] if i < 5 else r.get("Purpose",""))}</td></tr>')
    return ('<table><thead><tr><th scope="col">Zone</th><th scope="col" class="num">HR</th>'
            '<th scope="col" class="num">Power</th><th scope="col">RPE</th>'
            '<th scope="col">How it feels</th><th scope="col">What it trains</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>')


def _service_rows_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return ""
    head = "".join(f'<th scope="col">{_esc(col)}</th>' for col in columns)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f'<td class="small">{_esc(row.get(col, ""))}</td>' for col in columns) + "</tr>")
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def _clinical_review_section(summary: dict) -> str:
    flags = summary.get("clinical_review_flags") or []
    if not flags:
        return ""
    high_risk = bool(summary.get("prescriptions_suppressed"))
    intro = (
        "Training zones and exercise prescriptions are withheld until the supervising clinician confirms clearance "
        "and limits."
        if high_risk
        else "Review these CPET signals with the supervising clinician alongside symptoms and test quality."
    )
    handoff = ""
    action_plan = summary.get("action_plan") or []
    if high_risk and action_plan:
        handoff = _service_rows_table(action_plan, ["Focus", "Do this", "Dose / target", "Guardrail"])
    tone = " clinical-review--high" if high_risk else ""
    return (
        f'<section class="clinical-review{tone}" aria-labelledby="clinical-review-title">'
        '<h2 class="section-title" id="clinical-review-title">Clinical review and clearance</h2>'
        f'<p class="lead">{_esc(intro)}</p>'
        + _service_rows_table(flags, ["Priority", "Area", "Signal", "Coach action"])
        + handoff
        + "</section>"
    )


def _action_plan(metrics: dict, summary: dict, has_power: bool) -> str:
    service_plan = summary.get("action_plan") or []
    if service_plan:
        return _service_rows_table(service_plan, ["Focus", "Do this", "Dose / target", "Guardrail"])

    z2 = (summary.get("training_zones") or {}).get("zone2") or {}
    vt2_hr, vt2_pw = _num(metrics.get("vt2_hr_bpm")), _num(metrics.get("vt2_power_w"))
    z2_prescr = z2.get("power") if (has_power and z2.get("power")) else z2.get("hr", "your Zone 2 band")
    z4 = f"{_r5(vt2_pw)} W / ~{_r0(vt2_hr)} bpm" if (has_power and vt2_pw) else f"~{_r0(vt2_hr)} bpm"
    week = f"Reprogram easy sessions to <b>Zone 2</b> ({_esc(z2_prescr)}); hold the discipline to stay under LT1 and work the top, ~{_esc(z2.get('target_hr','the top of the band'))} — the fat-oxidation sweet spot."
    block = f"Raise the red-line: 2x/week threshold work at <b>{_esc(z4)}</b> (e.g. 3-4 x 8 min, easy between), with ~80% of total time in Zone 2. Minimise the grey-zone tempo that eats recovery."
    retest = "Re-test in 6-8 weeks. Expect the red-line (VT2) to climb and FatMax to shift later; VO2peak may hold. If they move we progress the stimulus; if not we change it."
    return (f'<div class="plan"><div class="plan__h">THIS WEEK</div><p>{week}</p>'
            f'<div class="plan__h">THIS BLOCK (~6 weeks)</div><p>{block}</p>'
            f'<div class="plan__h">RE-TEST</div><p>{retest}</p></div>')


_CSS = """
:root{--ink:#14181F;--ink-2:#3A4049;--muted:#6B7280;--paper:#FBFBF9;--card:#FFFFFF;
--hairline:#DADBD6;--accent:#0A6665;--accent-ink:#075453;--alert:#A51D2D;--r:8px;--pad:20px;--gap:16px;}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
font-family:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;font-size:12px;line-height:1.5;
-webkit-font-smoothing:antialiased;-webkit-print-color-adjust:exact;print-color-adjust:exact;}
.wrap{max-width:860px;margin:0 auto;padding:16px;}
.num,.kpi__val,td.num,th.num{font-variant-numeric:tabular-nums;}
.kpi__val{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;font-size:40px;line-height:1;letter-spacing:0;overflow-wrap:anywhere;}
.kpi__unit{font-size:11px;color:var(--muted);margin-left:5px;font-family:system-ui;}
.kpi__label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0;font-weight:700;margin-bottom:6px;}
h1{font-size:20px;letter-spacing:0;margin:0;}
.verdict{font-size:16px;font-weight:700;margin:0 0 6px;}
.section-title{font-size:14px;text-transform:uppercase;letter-spacing:0;color:var(--ink);
margin:26px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--hairline);font-weight:700;}
.card-title{font-size:13px;font-weight:700;margin-bottom:8px;}
.small{font-size:11px;color:var(--muted);} .body{font-size:12px;}
.card{background:var(--card);border:1px solid var(--hairline);border-radius:var(--r);padding:var(--pad);
box-shadow:0 1px 3px rgba(20,24,31,.06);margin-bottom:var(--gap);break-inside:avoid;}
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:var(--gap);}
.kpi{padding:14px 16px;}
.chip{display:inline-block;padding:2px 8px;border-radius:999px;font-size:10px;font-weight:700;letter-spacing:0;color:#fff;}
table{width:100%;border-collapse:collapse;} th,td{padding:7px 9px;border-bottom:1px solid var(--hairline);text-align:left;vertical-align:top;}
th{font-size:10px;text-transform:uppercase;letter-spacing:0;color:var(--ink-2);}
td.num,th.num{text-align:right;} .table-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;}
.dot{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:7px;vertical-align:middle;}
svg{display:block;width:100%;height:auto;}
.checks{list-style:none;margin:4px 0 0;padding:0;} .checks li{padding:3px 0;font-size:12px;}
.hdr{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;
background:linear-gradient(120deg,#14181F,#0A5C5B);color:#fff;border-radius:var(--r);padding:22px 24px;margin-bottom:18px;}
.hdr .brand{font-size:13px;letter-spacing:0;text-transform:uppercase;color:#C7ECE9;font-weight:700;}
.hdr h1{margin-top:4px;} .hdr .meta{text-align:right;font-size:11px;line-height:1.7;}
.hdr .meta b{color:#fff;} .hdr .meta span{color:#9aa9ac;}
.plan__h{font-size:11px;font-weight:700;letter-spacing:0;color:var(--accent-ink);margin-top:10px;}
.plan p{margin:2px 0 8px;}
.callout{background:var(--accent);color:#fff;border-radius:var(--r);padding:14px 18px;margin-bottom:var(--gap);}
.callout b{color:#fff;}
.callout--high{background:var(--alert);}
.callout--caution{background:#765100;}
.clinical-review--high{border-left:4px solid var(--alert);padding-left:14px;}
.disclaimer{font-size:10px;color:var(--muted);border-top:1px solid var(--hairline);padding-top:12px;margin-top:20px;}
.footnote{font-size:10px;color:var(--muted);margin-top:6px;}
p.lead{margin:0 0 12px;}
@media (max-width:640px){
body{font-size:14px;}.wrap{padding:10px;}.hdr{display:block;padding:18px 16px;}.hdr .meta{text-align:left;margin-top:14px;}
.kpi-row{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;}.kpi{padding:12px;}.kpi__val{font-size:30px;}
.card{padding:14px;}.section-title{margin-top:22px;}th,td{padding:7px 8px;min-width:92px;}.small{font-size:12px;}
.zone-chart{overflow-x:auto;-webkit-overflow-scrolling:touch;}.zone-chart svg{min-width:620px;}
}
@media (max-width:380px){.kpi-row{grid-template-columns:1fr;}}
@page{size:A4;margin:13mm;}
@media print{html,body{background:#fff;}.wrap{max-width:none;padding:0;}
.card{box-shadow:none;} *{-webkit-print-color-adjust:exact;print-color-adjust:exact;}
.card,svg,table{break-inside:avoid;} .page-break{break-before:page;}}
"""


def generate_cpet_client_report(
    metrics: dict[str, Any],
    *,
    athlete_name: str = "Athlete",
    test_date: str = "",
    modality: str | None = None,
    protocol: str | None = None,
    client_context: str = "general",
    qc_verdict: str | None = None,
    org_name: str = "Performance Lab",
    device: str | None = None,
    tester: str | None = None,
) -> str:
    """Return a complete, self-contained HTML CPET report for the client."""
    summary = build_cpet_coach_summary(metrics, client_context=client_context, modality=modality)
    has_power = _num(metrics.get("vt1_power_w")) is not None and _num(metrics.get("vt2_power_w")) is not None
    fitness = summary.get("fitness_classification") or {}
    zones = summary.get("training_zones") or {}
    chart = zones.get("chart") or {}
    z2 = zones.get("zone2") or {}
    prescriptions_suppressed = bool(summary.get("prescriptions_suppressed"))
    anchor_order_invalid = zones.get("suppression_reason") == "anchor_order"

    age = _num(metrics.get("age_years"))
    sex = metrics.get("sex")
    weight = _num(metrics.get("weight_kg"))
    height = _num(metrics.get("height_cm"))
    demo = " · ".join(x for x in [f"{round(age)} yr" if age else "", str(sex).capitalize() if sex else "",
                                  f"{_r1(weight)} kg" if weight else "", f"{_r0(height)} cm" if height else ""] if x)

    # ── S1 header
    header = (
        '<header class="hdr"><div><div class="brand">' + _esc(org_name) + '</div>'
        '<h1>Metabolic Performance Profile</h1>'
        '<div class="small" style="color:#cfe3e2;margin-top:4px;">Cardiopulmonary Exercise Test (CPET)</div></div>'
        '<div class="meta">'
        f'<span>Athlete</span> <b>{_esc(athlete_name)}</b><br>'
        + (f'<span>Profile</span> <b>{_esc(demo)}</b><br>' if demo else '')
        + f'<span>Test date</span> <b>{_esc(test_date or "—")}</b><br>'
        f'<span>Modality</span> <b>{_esc(modality or "—")}</b><br>'
        + (f'<span>Protocol</span> <b>{_esc(protocol)}</b><br>' if protocol else '')
        + (f'<span>Analyzer</span> <b>{_esc(device)}</b><br>' if device else '')
        + (f'<span>Tester</span> <b>{_esc(tester)}</b>' if tester else '')
        + '</div></header>'
    )

    # ── S3 headline + KPI hero
    headline = summary.get("result_headline") or {}
    headline_level = str(headline.get("Level") or "").lower()
    headline_tone = (
        " callout--high" if headline_level == "high"
        else (" callout--caution" if headline_level == "caution" else "")
    )
    hero = (
        f'<section class="callout{headline_tone}" aria-labelledby="result-headline">'
        '<h2 class="verdict" id="result-headline" style="color:#fff">'
        + _esc(headline.get("Headline", ""))
        + '</h2><div style="font-size:12px;color:#fff">'
        + _esc(headline.get("Meaning", ""))
        + (f' <b>Next:</b> {_esc(headline.get("Next step", ""))}' if headline.get("Next step") else "")
        + '</div></section>'
        + _kpi_tiles(metrics, summary, has_power)
    )
    clinical_review = _clinical_review_section(summary)

    # ── S4 mini zone bar
    zone_bar = _zone_bar_svg(chart, z2, has_power)
    s4 = ('<h2 class="section-title">Your training zones at a glance</h2><div class="card"><div class="zone-chart">'
          + zone_bar + '</div>'
          + '<p class="small" style="margin-top:8px">Zone 2 (endurance) is the shaded band topping out at VT1/LT1 — '
            'your ~2 mmol lactate line. Work the top of it; the FatMax marker is its floor, not its target.</p></div>'
          + '<div class="page-break"></div>') if zone_bar and not prescriptions_suppressed else ''

    # ── S5 fitness vs norms
    bullet = _percentile_bullet_svg(fitness)
    s5 = ''
    if bullet:
        caveat = (fitness.get("caveats") or [""])[0]
        s5 = ('<div class="section-title">Aerobic fitness vs your peers</div><div class="card">'
              f'<p class="lead">Your aerobic engine measured against people like you: <b>{_esc(fitness.get("category",""))}</b>, '
              f'{_esc(fitness.get("percentile_label",""))} for {_esc(fitness.get("reference_group",""))} '
              f'({_esc(fitness.get("modality_used",""))} norms).</p>' + bullet
              + f'<p class="footnote">Reference: {_esc(_norm_citation(fitness))}.'
              + (f' {_esc(caveat)}' if caveat else '') + '</p></div>')

    # ── S6 thresholds ladder
    s6 = ('<div class="section-title">Your thresholds</div><div class="card">'
          '<p class="lead">Your two thresholds split training into zones that actually mean something. '
          'VT1/LT1 is the top of easy; VT2/LT2 is your sustainable red-line.</p>'
          '<div class="table-wrap">' + _threshold_ladder(metrics, has_power) + '</div>'
          '<p class="footnote">&dagger; Thresholds were identified automatically from your gas-exchange and ventilation '
          'curves and labelled against the ~2 / 4 mmol lactate equivalents (no blood drawn unless noted). '
          'Auto-detection is a good estimate, not exact — a threshold is a zone, not a line.</p></div>') \
        if not anchor_order_invalid else ""

    # ── S7 zone table
    z2_line = z2.get("power") if (has_power and z2.get("power")) else z2.get("hr", "")
    s7 = ('<h2 class="section-title">Your individualized zones</h2>'
          + (f'<div class="callout">Zone 2 target: <b>{_esc(z2_line)}</b> — aim ~{_esc(z2.get("target_hr",""))}, '
             f'cap at {_esc(z2.get("ceiling_hr",""))} bpm (LT1 / ~2 mmol). FatMax {_esc(z2.get("fatmax_floor",""))} '
             'is the floor, not the target.</div>' if z2.get("target_hr") else '')
          + '<div class="card"><div class="table-wrap">' + _zone_table(summary, has_power) + '</div>'
          + (f'<p class="body" style="margin-top:10px">{_esc(summary.get("training_narrative",""))}</p>' if summary.get("training_narrative") else '')
          + '</div><div class="page-break"></div>') if zones.get("has_zones") and not prescriptions_suppressed else ""

    # ── S8 metabolic
    metab = summary.get("metabolic_profile")
    s8 = ''
    if metab:
        s8 = ('<div class="section-title">Your fuel system</div><div class="card">'
              '<div class="kpi-row">'
              + _tile("Max fat oxidation", _r2(_num(metab.get("mfo_g_min"))), "g/min", "", _chip(metab.get("mfo_class", ""), "good"))
              + _tile("FatMax heart rate", _r0(_num(metab.get("fatmax_hr"))), "bpm", "peak fat-burning intensity")
              + '</div>'
              + (
                  f'<p class="body" style="margin-top:10px">{_esc(summary.get("metabolic_narrative", ""))}</p>'
                  if summary.get("metabolic_narrative") and not prescriptions_suppressed else ""
              )
              + '</div>')

    # ── S9 limiter / efficiency
    limiter_profile = summary.get("limiter_profile") or {}
    limiter = limiter_profile.get("Limiter") or limiter_profile.get("Archetype", "not fully classified")
    why = limiter_profile.get("Program emphasis", "")
    slope = _num(metrics.get("ve_vco2_slope"))
    br = _num(metrics.get("breathing_reserve_pct"))
    s9 = ('<div class="section-title">Your primary limiter</div><div class="card">'
          f'<p class="lead">Putting it together, your primary limiter is <b>{_esc(limiter)}</b> — {_esc(why)}.</p>'
          '<div class="table-wrap"><table><tbody>'
          + (f'<tr><td>Limiter</td><td class="num">{_esc(limiter_profile.get("Limiter", ""))}</td></tr>' if limiter_profile else '')
          + (f'<tr><td>Evidence</td><td class="num">{_esc(limiter_profile.get("Evidence", ""))}</td></tr>' if limiter_profile else '')
          + (f'<tr><td>Ventilatory efficiency (VE/VCO2 slope)</td><td class="num">{_r1(slope)} · {_esc(_arena_label(slope))}</td></tr>' if slope is not None else '')
          + (f'<tr><td>Breathing reserve</td><td class="num">{_r0(br)}%</td></tr>' if br is not None else '')
          + (f'<tr><td>O2 pulse (stroke-volume proxy)</td><td class="num">{_r1(_num(metrics.get("o2_pulse_ml_beat")))} mL/beat</td></tr>' if metrics.get("o2_pulse_ml_beat") else '')
          + (f'<tr><td>Peak RER (effort)</td><td class="num">{_r2(_num(metrics.get("peak_rer")))}</td></tr>' if metrics.get("peak_rer") else '')
          + '</tbody></table></div></div>')

    # ── S10 action plan
    s10 = (
        '<h2 class="section-title">Your training plan</h2><div class="card">'
        + _action_plan(metrics, summary, has_power)
        + '</div><div class="page-break"></div>'
    ) if not prescriptions_suppressed else ""

    s_retest = ''
    if summary.get("retest_targets"):
        s_retest = (
            '<div class="section-title">What should improve on retest</div><div class="card">'
            + _service_rows_table(summary.get("retest_targets", []), ["Priority", "Metric", "Current", "Target", "Why it matters"])
            + '</div>'
        )

    # ── S11 methodology + disclaimer
    qc = f'<p class="footnote">&Dagger; Plot quality was screened automatically ({_esc(qc_verdict)}) and reviewed by your physiologist.</p>' if qc_verdict else ''
    glossary = (
        '<p class="small"><b>Glossary.</b> VO2peak — the highest oxygen uptake reached (engine size). '
        'VT1/LT1 — aerobic (first) threshold, ~2 mmol lactate, top of easy. VT2/LT2 — anaerobic (second) threshold, '
        '~4 mmol, sustainable red-line. RER — respiratory exchange ratio (effort/fuel marker). VE/VCO2 slope — breathing '
        'efficiency. O2 pulse — oxygen per heartbeat (stroke-volume proxy). FatMax / MFO — the intensity and rate of peak '
        'fat burning.</p>')
    methodology = (
        '<div class="section-title">Methodology &amp; disclaimer</div><div class="card">'
        f'<p class="small">Test: {_esc(modality or "—")}{(" · " + _esc(protocol)) if protocol else ""}'
        f'{(" · " + _esc(device)) if device else ""}. Thresholds identified from the V-slope and ventilatory-equivalent '
        'methods; aerobic fitness classified against FRIEND / ACSM age-sex percentile norms.</p>'
        + glossary + qc
        + '<div class="disclaimer">This report is a coaching and performance-assessment tool, not a medical document. '
        'It is not a clinical cardiopulmonary exercise test, diagnosis, or medical advice, and does not replace evaluation '
        'by a physician. It measures performance variables, not cardiac or pulmonary health. If you experienced chest pain, '
        'unusual breathlessness, dizziness, or an irregular heartbeat during testing — or have a known heart, lung, or '
        'metabolic condition — consult a qualified physician before continuing training. Always seek medical clearance '
        'before starting or significantly changing an exercise program.</div></div>')

    effort = _effort_badge(metrics)
    body = (
        header + '<main>' + hero + clinical_review + effort + s4 + s5 + s6 + s7 + s8 + s9
        + s10 + s_retest + methodology + '</main>'
    )

    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f'<title>CPET Report — {_esc(athlete_name)}</title><style>{_CSS}</style></head>'
        f'<body><div class="wrap">{body}</div></body></html>'
    )
