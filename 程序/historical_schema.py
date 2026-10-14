"""Stage 11 历史审核报告结构和枚举。"""

VERIFICATION_STATUS = {"verified", "supported", "plausible", "dramatized", "disputed", "unverified", "contradicted"}
EVIDENCE_LEVELS = {"A", "B", "C", "D", "E"}
SEVERITIES = {"info", "warning", "error", "critical"}
GATES = {"passed", "review_required", "blocked", "not_applicable"}
CATEGORIES = {"PERSON", "EVENT", "DATE", "LOCATION", "ORGANIZATION", "RANK", "COSTUME", "WEAPON", "PROP", "ARCHITECTURE", "TRANSPORT", "LANGUAGE", "SOCIAL", "MILITARY", "TECHNOLOGY", "GEOGRAPHY", "CUSTOM", "OTHER"}


def empty_historical_report(project: dict) -> dict:
    return {
        "schema_version": "1.0",
        "project": project["project_name"],
        "project_id": project["project_id"],
        "historical_relevance": "none",
        "historical_score": 100,
        "historical_gate": "not_applicable",
        "scores": {"person_score": 100, "event_score": 100, "date_score": 100, "location_score": 100, "costume_score": 100, "weapon_score": 100, "language_score": 100, "material_culture_score": 100},
        "claims": [],
        "issues": [],
        "sources": [],
        "source_conflicts": [],
        "dramatizations": [],
        "production_deviations": [],
        "requires_external_verification": [],
    }
