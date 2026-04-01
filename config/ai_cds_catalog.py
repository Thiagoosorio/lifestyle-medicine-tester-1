"""Evidence-backed EMR benchmarks and AI clinical decision support patterns.

All entries should link to primary sources (institution pages, journals, regulators).
"""

from __future__ import annotations


INSTITUTION_EMR_BENCHMARKS = [
    {
        "institution": "Mass General Brigham (Harvard-affiliated)",
        "emr_platform": "Epic (enterprise eCare)",
        "what_they_built": "System-wide integrated EHR workflows for quality and preventive care gap identification.",
        "source_title": "Cardiovascular Informatics Program (BWH) and MGB integrated healthcare system",
        "source_type": "Institution page",
        "year": 2024,
        "link": "https://www.brighamandwomens.org/heart-and-vascular-center/programs/cardiovascular-informatics-program",
    },
    {
        "institution": "Mayo Clinic",
        "emr_platform": "Epic (single integrated EHR/RCM strategy)",
        "what_they_built": "Enterprise unification on one EHR foundation to accelerate care coordination and innovation.",
        "source_title": "Mayo Clinic selects Epic as strategic partner",
        "source_type": "Institution news",
        "year": 2015,
        "link": "https://newsnetwork.mayoclinic.org/discussion/mayo-clinic-selects-epic-as-strategic-partner-for-electronic-health-record-and-revenue-cycle-managem/",
    },
    {
        "institution": "Johns Hopkins Medicine",
        "emr_platform": "Epic (single integrated enterprise EMR)",
        "what_they_built": "Unified EMR across hospitals and affiliates to support consistent workflows and decision support.",
        "source_title": "Epic at Johns Hopkins",
        "source_type": "Institution page",
        "year": 2026,
        "link": "https://www.hopkinsmedicine.org/epic",
    },
    {
        "institution": "UCSF Health",
        "emr_platform": "APeX (Epic-powered)",
        "what_they_built": "Epic-based health IT portfolio and cross-department dashboards for care coordination.",
        "source_title": "UCSF Health IT Portfolio (APeX) and Epic dashboard collaboration",
        "source_type": "Institution page",
        "year": 2024,
        "link": "https://it.ucsf.edu/health-it-portfolio",
    },
    {
        "institution": "Cleveland Clinic",
        "emr_platform": "Epic (MyPractice Community / MyChart ecosystem)",
        "what_they_built": "Shared Epic-based ambulatory and patient-portal workflows across the enterprise.",
        "source_title": "MyPractice Community electronic health record system",
        "source_type": "Institution page",
        "year": 2026,
        "link": "https://my.clevelandclinic.org/online-services/mypractice.aspx",
    },
]


AI_CDS_USE_CASES = [
    {
        "use_case": "Sepsis early-warning in live EHR workflow",
        "institution_examples": "Johns Hopkins / multi-site health systems",
        "impact_summary": "Prospective multi-site deployment linked with faster evaluation and lower mortality risk in sepsis care.",
        "evidence_level": "Q1 cohort implementation",
        "study_type": "Prospective multi-site cohort",
        "citation": "Prospective, multi-site study of TREWS sepsis early warning",
        "year": 2022,
        "pmid": "35864252",
        "doi": "10.1038/s41591-022-01894-0",
        "link": "https://pubmed.ncbi.nlm.nih.gov/35864252/",
        "app_pattern": "Use AI/rule triage to detect acute deterioration and trigger closed-loop escalation pathways.",
        "status_in_app": "Partially present (critical-lab escalation + priority list).",
    },
    {
        "use_case": "AI-enabled low ejection fraction (EF) detection from ECG",
        "institution_examples": "Mayo Clinic",
        "impact_summary": "Pragmatic cluster-randomized trial showed higher low-EF diagnosis when AI-CDS result was surfaced to clinicians.",
        "evidence_level": "Pragmatic cluster RCT",
        "study_type": "Cluster-randomized trial",
        "citation": "AI-Enhanced ECG Identification of Low EF",
        "year": 2021,
        "pmid": None,
        "doi": "10.1111/1475-6773.13757",
        "link": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8441328/",
        "app_pattern": "Add AI/risk trigger layer that suggests confirmatory testing when cardiometabolic risk stack is elevated.",
        "status_in_app": "Not yet implemented.",
    },
    {
        "use_case": "Virtual scribe / ambient documentation for EHR burden reduction",
        "institution_examples": "Mass General Hospital + Brigham and Women's Hospital",
        "impact_summary": "Cohort data from 2 academic centers showed reduced total EHR time, note time, and after-hours charting.",
        "evidence_level": "Q1 cohort implementation",
        "study_type": "Cohort study",
        "citation": "Virtual Scribes and Physician Time Spent on Electronic Health Records",
        "year": 2024,
        "pmid": "38787556",
        "doi": "10.1001/jamanetworkopen.2024.13140",
        "link": "https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2819249",
        "app_pattern": "Use AI to draft visit summaries, clinician prep notes, and structured follow-up instructions.",
        "status_in_app": "Partially present (AI Coach + summary pages), can be upgraded.",
    },
    {
        "use_case": "Safe governance for AI-enabled CDS",
        "institution_examples": "FDA, AHRQ, NICE, WHO",
        "impact_summary": "National/international frameworks define evidence, transparency, safety, and monitoring requirements.",
        "evidence_level": "Guideline / policy",
        "study_type": "Regulatory and standards guidance",
        "citation": "Clinical Decision Support Software (FDA); NICE ESF; WHO AI ethics guidance",
        "year": 2026,
        "pmid": None,
        "doi": None,
        "link": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software",
        "app_pattern": "Require human review, auditable rationale, and post-deployment monitoring for every AI recommendation.",
        "status_in_app": "Partially present (disclaimers + evidence trace), can be formalized.",
    },
]
