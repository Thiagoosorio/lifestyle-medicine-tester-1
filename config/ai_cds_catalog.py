"""Evidence-backed EMR benchmarks and lifestyle-focused AI CDS patterns.

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
        "use_case": "LLM-based physical activity coaching with wearable context",
        "institution_examples": "Stanford HCI (research prototype)",
        "impact_summary": "Open prototype combines motivational interviewing with wearable context for personalized physical activity planning.",
        "evidence_level": "Peer-reviewed conference system",
        "study_type": "Human-computer interaction research",
        "citation": "GPTCoach: Towards LLM-Based Physical Activity Coaching (CHI 2025)",
        "year": 2025,
        "pmid": None,
        "doi": None,
        "link": "https://github.com/StanfordHCI/GPTCoach-CHI2025",
        "app_pattern": "Use motivational interviewing prompts + stage-of-change aware plan builder.",
        "status_in_app": "Partially present (AI Coach), can be upgraded with wearable context memory.",
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


LIFESTYLE_EVIDENCE_BASE = [
    {
        "topic": "Physical activity dose-response and prevention",
        "evidence": "WHO 2020 physical activity guideline update",
        "source_type": "Guideline",
        "year": 2020,
        "pmid": "33239350",
        "doi": "10.1136/bjsports-2020-102955",
        "link": "https://pubmed.ncbi.nlm.nih.gov/33239350/",
    },
    {
        "topic": "Mediterranean diet for primary CVD prevention",
        "evidence": "PREDIMED trial (reanalysis)",
        "source_type": "Randomized trial",
        "year": 2018,
        "pmid": "29897866",
        "doi": "10.1056/NEJMoa1800389",
        "link": "https://pubmed.ncbi.nlm.nih.gov/29897866/",
    },
    {
        "topic": "Prediabetes/T2D prevention with lifestyle change",
        "evidence": "Diabetes Prevention Program (lifestyle vs metformin)",
        "source_type": "Randomized trial",
        "year": 2002,
        "pmid": "11832527",
        "doi": "10.1056/NEJMoa012512",
        "link": "https://pubmed.ncbi.nlm.nih.gov/11832527/",
    },
    {
        "topic": "Blood pressure management with non-pharmacologic interventions",
        "evidence": "ACC/AHA hypertension guideline",
        "source_type": "Guideline",
        "year": 2017,
        "pmid": "29133356",
        "doi": "10.1161/HYP.0000000000000065",
        "link": "https://pubmed.ncbi.nlm.nih.gov/29133356/",
    },
    {
        "topic": "Primary prevention lifestyle and risk-factor control",
        "evidence": "ACC/AHA guideline on primary prevention of CVD",
        "source_type": "Guideline",
        "year": 2019,
        "pmid": "30879355",
        "doi": "10.1161/CIR.0000000000000678",
        "link": "https://pubmed.ncbi.nlm.nih.gov/30879355/",
    },
    {
        "topic": "NAFLD/MASLD lifestyle-first management",
        "evidence": "AASLD practice guidance",
        "source_type": "Guideline",
        "year": 2023,
        "pmid": "36727674",
        "doi": "10.1002/hep.32772",
        "link": "https://pubmed.ncbi.nlm.nih.gov/36727674/",
    },
]


GITHUB_LIFESTYLE_PATTERNS = [
    {
        "name": "HL7 CDS Hooks Specification",
        "repo": "https://github.com/HL7/cds-hooks",
        "why_relevant": "Standard way to deliver in-workflow recommendation cards in EHR contexts.",
        "adopt_next": "Use CDS card structure for your intervention recommendation cards.",
    },
    {
        "name": "CDS Hooks Sandbox",
        "repo": "https://github.com/cds-hooks/sandbox",
        "why_relevant": "Test harness for patient-view and order-select decision support workflows.",
        "adopt_next": "Mirror card UX patterns for explainable recommendations.",
    },
    {
        "name": "AHRQ CDS Connect CQL Services",
        "repo": "https://github.com/AHRQ-CDS/AHRQ-CDS-Connect-CQL-SERVICES",
        "why_relevant": "Reference implementation for evidence logic to service endpoints (including CDS Hooks).",
        "adopt_next": "Represent lifestyle rules as explicit, auditable logic blocks.",
    },
    {
        "name": "SMART on FHIR CDS Example (QRISK/NICE)",
        "repo": "https://github.com/srdc/smart-on-fhir-cds",
        "why_relevant": "Shows FHIR + CDS integration with cardiovascular risk and guideline suggestions.",
        "adopt_next": "Adapt structure to map your organ/wearable domains into recommendation cards.",
    },
    {
        "name": "Stanford GPTCoach",
        "repo": "https://github.com/StanfordHCI/GPTCoach-CHI2025",
        "why_relevant": "Motivational interviewing + wearable-aware coaching prototype.",
        "adopt_next": "Improve AI Coach with stage-of-change + adherence barrier prompts.",
    },
    {
        "name": "BCIO (Behavior Change Intervention Ontology)",
        "repo": "https://github.com/HumanBehaviourChangeProject/ontologies",
        "why_relevant": "Structured intervention ontology for consistent recommendation language.",
        "adopt_next": "Tag each recommendation by behavior-change mechanism for auditability.",
    },
]
