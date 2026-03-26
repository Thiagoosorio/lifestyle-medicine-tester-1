"""Wearable-driven 5-domain wheel configuration.

Evidence-based metric selection and weighting for longevity medicine.

Weight tiers:
  1.5 = Gold standard — strong mortality/morbidity evidence
  1.2 = High value — established clinical predictor
  1.0 = Standard — useful physiological signal
  0.7 = Supporting — adds context but lower standalone value
  0.4 = Minor — informational, minimal scoring influence

References:
  - Resting HR & mortality: Cooney et al. (2010) Eur Heart J. PMID: 20348188
  - HRV & longevity: Tsuji et al. (1996) Circulation. PMID: 8598068
  - Steps & mortality: Paluch et al. (2022) Lancet Public Health. PMID: 35247352
  - Sleep efficiency: Buysse (2014) Sleep Med Rev. PMID: 24629826
  - Deep sleep & aging: Mander et al. (2017) Neuron. PMID: 28394322
  - SpO2 desaturation: Levy et al. (2015) Eur Respir J. PMID: 25395032
  - BP targets: Whelton et al. (2018) Hypertension. PMID: 29133356
  - CGM TIR: Battelino et al. (2019) Diabetes Care. PMID: 31177185
"""

WEARABLE_WHEEL_DOMAINS = {
    "heart_metabolism": {
        "name": "Heart & Metabolism",
        "short": "HM",
        "color": "#E53935",
        "icon": "heart_plus",
        "description": "Cardiovascular fitness, metabolic health, and daily activity.",
        "is_proxy": False,
    },
    "muscle_bones": {
        "name": "Muscle & Bones",
        "short": "MB",
        "color": "#8D6E63",
        "icon": "fitness_center",
        "description": "Movement volume and physical load (proxy from activity metrics).",
        "is_proxy": True,
    },
    "gut_digestion": {
        "name": "Gut & Digestion",
        "short": "GD",
        "color": "#43A047",
        "icon": "eco",
        "description": "Autonomic tone and inflammation signals linked to gut health (proxy).",
        "is_proxy": True,
    },
    "brain_health": {
        "name": "Brain Health",
        "short": "BH",
        "color": "#5C6BC0",
        "icon": "neurology",
        "description": "Sleep quality, architecture, and cognitive restoration.",
        "is_proxy": False,
    },
    "system_wide": {
        "name": "System Wide",
        "short": "SW",
        "color": "#00897B",
        "icon": "monitor_heart",
        "description": "Whole-system stress, oxygenation, and recovery physiology.",
        "is_proxy": False,
    },
}

DOMAIN_ORDER = [
    "heart_metabolism",
    "muscle_bones",
    "gut_digestion",
    "brain_health",
    "system_wide",
]


# ══════════════════════════════════════════════════════════════════════════
# METRIC SPECIFICATIONS
# ══════════════════════════════════════════════════════════════════════════
#
# Scoring modes:
#   higher_better  — linear 0-100 between min_value and max_value
#   lower_better   — inverted linear
#   target_band    — 100 inside optimal, decays to 0 at hard limits
#   binary         — 100 if value == healthy_value, else 0
#   goal_distance  — 100 at goal weight, drops 6 pts per 1% away
#
# "why" field: clinical rationale for inclusion and weight assignment.

WEARABLE_METRIC_SPECS = {

    # ── Heart & Metabolism ─────────────────────────────────────────────
    # 8 core metrics (removed: avg HR redundant with RHR, max HR is genetic/not health)

    "resting_heart_rate_bpm": {
        "label": "Resting Heart Rate",
        "unit": "bpm",
        "score_mode": "target_band",
        "hard_min": 38,
        "optimal_min": 45,
        "optimal_max": 65,
        "hard_max": 90,
        "domain": "heart_metabolism",
        "weight": 1.5,
        "why": "Strong independent predictor of cardiovascular mortality. Lower RHR reflects better autonomic tone and cardiac efficiency. Cooney et al. (2010) Eur Heart J.",
    },
    "heart_rate_variability_ms": {
        "label": "Heart Rate Variability (RMSSD)",
        "unit": "ms",
        "score_mode": "higher_better",
        "min_value": 15,
        "max_value": 100,
        "domain": "heart_metabolism",
        "weight": 1.5,
        "why": "Gold standard wearable biomarker for autonomic health. Low HRV predicts all-cause mortality, cardiac events, and poor stress resilience. Tsuji et al. (1996) Circulation.",
    },
    "steps_count": {
        "label": "Daily Steps",
        "unit": "steps",
        "score_mode": "higher_better",
        "min_value": 2000,
        "max_value": 10000,
        "domain": "heart_metabolism",
        "weight": 1.2,
        "why": "Dose-response with all-cause mortality plateaus near 8-10K steps/day. Most accessible physical activity metric. Paluch et al. (2022) Lancet Public Health.",
    },
    "respiratory_rate_bpm": {
        "label": "Respiratory Rate",
        "unit": "breaths/min",
        "score_mode": "target_band",
        "hard_min": 8,
        "optimal_min": 12,
        "optimal_max": 18,
        "hard_max": 25,
        "domain": "heart_metabolism",
        "weight": 1.0,
        "why": "Elevated respiratory rate is an early warning for infection, metabolic acidosis, and cardiopulmonary decompensation. Cretikos et al. (2008) Resuscitation.",
    },
    "arrhythmia_alert_afib": {
        "label": "AFib Alert",
        "unit": "flag",
        "score_mode": "binary",
        "healthy_value": 0,
        "domain": "heart_metabolism",
        "weight": 1.5,
        "why": "Atrial fibrillation carries 5x stroke risk. Early detection from wearables enables timely anticoagulation. Perez et al. (2019) NEJM.",
    },
    "kilojoule_expended": {
        "label": "Active Energy",
        "unit": "kJ",
        "score_mode": "higher_better",
        "min_value": 700,
        "max_value": 3000,
        "domain": "heart_metabolism",
        "weight": 0.4,
        "why": "Wrist-based calorie estimation is 20-40% inaccurate (Shcherbina 2017 J Pers Med). Only reliable from cycling power meters. Kept at minimal weight as directional activity signal.",
    },

    # Optional heart/metabolism metrics
    "systolic_bp_mmhg": {
        "label": "Systolic Blood Pressure",
        "unit": "mmHg",
        "score_mode": "target_band",
        "hard_min": 85,
        "optimal_min": 100,
        "optimal_max": 120,
        "hard_max": 180,
        "domain": "heart_metabolism",
        "weight": 1.5,
        "optional": True,
        "why": "Hypertension is the #1 modifiable CV risk factor globally. Systolic BP >130 doubles CV event risk. Whelton et al. (2018) ACC/AHA Guideline.",
    },
    "diastolic_bp_mmhg": {
        "label": "Diastolic Blood Pressure",
        "unit": "mmHg",
        "score_mode": "target_band",
        "hard_min": 50,
        "optimal_min": 60,
        "optimal_max": 80,
        "hard_max": 110,
        "domain": "heart_metabolism",
        "weight": 1.0,
        "optional": True,
        "why": "Complements systolic BP. Isolated diastolic hypertension is rarer but still increases CV risk in younger adults.",
    },
    "cgm_avg_glucose_mgdl": {
        "label": "CGM Average Glucose",
        "unit": "mg/dL",
        "score_mode": "target_band",
        "hard_min": 65,
        "optimal_min": 80,
        "optimal_max": 100,
        "hard_max": 200,
        "domain": "heart_metabolism",
        "weight": 1.2,
        "optional": True,
        "why": "Continuous glucose monitoring reveals glycemic variability invisible to HbA1c. Average glucose >100 signals insulin resistance. Optimal <100 for longevity.",
    },
    "cgm_time_in_range_pct": {
        "label": "CGM Time In Range (70-180)",
        "unit": "%",
        "score_mode": "higher_better",
        "min_value": 50,
        "max_value": 95,
        "domain": "heart_metabolism",
        "weight": 1.2,
        "optional": True,
        "why": "TIR >70% is the consensus target (Battelino 2019). Each 10% drop in TIR associated with increased microvascular complications.",
    },
    "body_weight_kg": {
        "label": "Body Weight",
        "unit": "kg",
        "score_mode": "goal_distance",
        "domain": "heart_metabolism",
        "weight": 0.7,
        "optional": True,
        "why": "Weight trends matter more than absolute weight. Scored relative to user-set goal. Daily noise is high; scoring service applies smoothing.",
    },

    # ── System Wide ────────────────────────────────────────────────────
    # 5 metrics (removed: skin_temperature — absolute skin temp is environment-dependent
    # with low clinical utility; kept body_temp_deviation which detects actual illness)

    "overnight_spo2_avg_pct": {
        "label": "Overnight SpO2 Average",
        "unit": "%",
        "score_mode": "higher_better",
        "min_value": 90,
        "max_value": 99,
        "domain": "system_wide",
        "weight": 1.5,
        "why": "Nocturnal desaturation is the hallmark of obstructive sleep apnea (affects ~1 billion people). Average SpO2 <93% warrants sleep study referral. Levy et al. (2015) Eur Respir J.",
    },
    "overnight_spo2_nadir_pct": {
        "label": "Overnight SpO2 Nadir",
        "unit": "%",
        "score_mode": "higher_better",
        "min_value": 80,
        "max_value": 96,
        "domain": "system_wide",
        "weight": 1.2,
        "why": "Nadir <88% indicates significant desaturation events. Even brief drops carry CV risk through intermittent hypoxia and sympathetic activation.",
    },
    "body_temperature_deviation_c": {
        "label": "Body Temp Deviation",
        "unit": "\u00b0C",
        "score_mode": "lower_better",
        "min_value": 0.0,
        "max_value": 1.5,
        "transform": "abs",
        "domain": "system_wide",
        "weight": 1.0,
        "why": "Deviation from personal baseline detects infection, inflammation, or hormonal shifts. More clinically meaningful than absolute temperature which varies by environment.",
    },
    "recovery_score": {
        "label": "Recovery Score",
        "unit": "score",
        "score_mode": "higher_better",
        "min_value": 0,
        "max_value": 100,
        "domain": "system_wide",
        "weight": 0.7,
        "why": "Device-computed composite (HRV, RHR, sleep). Proprietary algorithm varies by manufacturer. Useful as trend but double-counts raw metrics already captured individually.",
    },
    "spo2_pct": {
        "label": "Daytime SpO2",
        "unit": "%",
        "score_mode": "higher_better",
        "min_value": 90,
        "max_value": 100,
        "domain": "system_wide",
        "weight": 0.7,
        "why": "Resting daytime SpO2 <94% is clinically significant. Lower weight because overnight SpO2 is more actionable for most wearable users.",
    },

    # ── Brain Health (Sleep) ───────────────────────────────────────────
    # 10 metrics (removed: baseline_sleep_needed, no_data_received,
    # sleep_needed_from_nap, sleep_needed_from_strain — device estimates
    # not direct measurements; naps — ambiguous clinical value;
    # light_sleep — it's the leftover stage; time_in_bed — overlaps efficiency)

    "sleep_efficiency_pct": {
        "label": "Sleep Efficiency",
        "unit": "%",
        "score_mode": "higher_better",
        "min_value": 70,
        "max_value": 98,
        "domain": "brain_health",
        "weight": 1.5,
        "why": "Gold standard sleep quality metric — time asleep / time in bed. Efficiency <85% is a diagnostic criterion for insomnia. Buysse (2014) Sleep Med Rev.",
    },
    "sleep_consistency_pct": {
        "label": "Sleep Consistency",
        "unit": "%",
        "score_mode": "higher_better",
        "min_value": 50,
        "max_value": 100,
        "domain": "brain_health",
        "weight": 1.2,
        "why": "Irregular sleep-wake timing (social jet lag) independently increases cardiometabolic risk. Regularity matters as much as duration. Huang et al. (2020) NPJ Digital Med.",
    },
    "total_slow_wave_sleep_time_min": {
        "label": "Deep Sleep (SWS)",
        "unit": "min",
        "score_mode": "target_band",
        "hard_min": 10,
        "optimal_min": 60,
        "optimal_max": 120,
        "hard_max": 200,
        "domain": "brain_health",
        "weight": 0.7,
        "why": "SWS is critical for physical recovery and glymphatic clearance (Mander 2017 Neuron). HOWEVER: consumer wearables have only ~60-70% stage classification accuracy vs polysomnography (Chinoy 2021 Sleep). Useful as trend, not diagnostic. Weight reduced for measurement uncertainty.",
    },
    "total_rem_sleep_time_min": {
        "label": "REM Sleep",
        "unit": "min",
        "score_mode": "target_band",
        "hard_min": 30,
        "optimal_min": 80,
        "optimal_max": 130,
        "hard_max": 200,
        "domain": "brain_health",
        "weight": 0.7,
        "why": "REM supports emotional regulation and memory (Leung 2021 JAMA Netw Open). Same measurement caveat as SWS — wearable stage detection is imprecise. Trend value only.",
    },
    "sleep_debt_hours": {
        "label": "Sleep Debt",
        "unit": "hours",
        "score_mode": "lower_better",
        "min_value": 0,
        "max_value": 8,
        "domain": "brain_health",
        "weight": 0.7,
        "why": "Device-computed estimate, not a direct measurement. The concept is valid (Van Dongen 2003 Sleep) but the calculation is proprietary and varies by device. Directional signal only.",
    },
    "sleep_disturbance_count": {
        "label": "Sleep Disturbances",
        "unit": "count",
        "score_mode": "lower_better",
        "min_value": 0,
        "max_value": 12,
        "domain": "brain_health",
        "weight": 1.0,
        "why": "Frequent awakenings fragment sleep architecture, reducing restorative value even when total duration is adequate. Common in sleep apnea and anxiety.",
    },
    "total_awake_time_min": {
        "label": "Wake After Sleep Onset",
        "unit": "min",
        "score_mode": "lower_better",
        "min_value": 0,
        "max_value": 90,
        "domain": "brain_health",
        "weight": 1.0,
        "why": "WASO >30 min is a diagnostic criterion for insomnia. High WASO reduces sleep efficiency and subjective sleep quality.",
    },
    "sleep_latency_min": {
        "label": "Sleep Latency",
        "unit": "min",
        "score_mode": "target_band",
        "hard_min": 0,
        "optimal_min": 5,
        "optimal_max": 20,
        "hard_max": 60,
        "domain": "brain_health",
        "weight": 0.7,
        "why": "Time to fall asleep — too short (<5 min) suggests sleep deprivation, too long (>30 min) suggests insomnia. Target 10-20 min indicates healthy sleep pressure.",
    },
    "sleep_cycle_count": {
        "label": "Sleep Cycles",
        "unit": "cycles",
        "score_mode": "target_band",
        "hard_min": 2,
        "optimal_min": 4,
        "optimal_max": 6,
        "hard_max": 7,
        "domain": "brain_health",
        "weight": 0.7,
        "why": "4-6 complete 90-min cycles indicate adequate sleep architecture progression through all stages. Fewer cycles = fragmented or insufficient sleep.",
    },
    "sleep_performance_pct": {
        "label": "Sleep Performance",
        "unit": "%",
        "score_mode": "higher_better",
        "min_value": 50,
        "max_value": 100,
        "domain": "brain_health",
        "weight": 0.4,
        "why": "Device-computed composite (Whoop-specific). Overlaps with efficiency and debt. Proprietary formula — minimal independent weight.",
    },
}


# ── Domain → Metric Mapping ──────────────────────────────────────────────

DIRECT_DOMAIN_METRICS = {
    "heart_metabolism": [
        "resting_heart_rate_bpm",
        "heart_rate_variability_ms",
        "steps_count",
        "respiratory_rate_bpm",
        "arrhythmia_alert_afib",
        "kilojoule_expended",
        "systolic_bp_mmhg",
        "diastolic_bp_mmhg",
        "cgm_avg_glucose_mgdl",
        "cgm_time_in_range_pct",
        "body_weight_kg",
    ],
    "system_wide": [
        "overnight_spo2_avg_pct",
        "overnight_spo2_nadir_pct",
        "body_temperature_deviation_c",
        "recovery_score",
        "spo2_pct",
    ],
    "brain_health": [
        "sleep_efficiency_pct",
        "sleep_consistency_pct",
        "total_slow_wave_sleep_time_min",
        "total_rem_sleep_time_min",
        "sleep_debt_hours",
        "sleep_disturbance_count",
        "total_awake_time_min",
        "sleep_latency_min",
        "sleep_cycle_count",
        "sleep_performance_pct",
    ],
}


# Proxy domains borrow metrics from other domains until dedicated sensors exist.
PROXY_DOMAIN_WEIGHTS = {
    "muscle_bones": {
        "steps_count": 0.45,
        "kilojoule_expended": 0.35,
        "recovery_score": 0.20,
    },
    "gut_digestion": {
        "sleep_efficiency_pct": 0.30,
        "respiratory_rate_bpm": 0.20,
        "heart_rate_variability_ms": 0.30,
        "body_temperature_deviation_c": 0.20,
    },
}


CSV_TEMPLATE_HEADER = [
    "metric_code",
    "value",
    "measured_at",
    "source",
]


KNOWN_WEARABLE_SOURCES = [
    "Whoop Band",
    "InBody H40 Home Scale",
    "CGM FreeStyle Libre",
    "Biobeat BPM",
    "Withings BPM Connect Pro",
    "Omron EVOLV",
    "Hilo Band (Aktiia)",
    "Oura Ring",
    "Garmin",
    "Apple Watch",
    "Fitbit",
    "manual",
    "csv_upload",
]
