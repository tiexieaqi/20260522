"""Stage 10 连续性报告的结构约定。"""

SEVERITIES = {"info", "warning", "error", "critical"}
GATES = {"passed", "review_required", "blocked"}
CATEGORIES = {"character", "version", "costume", "injury", "prop", "weapon", "location", "temporal", "weather", "spatial", "state_link", "dialogue", "cross_model"}


def empty_report(project: dict) -> dict:
    return {
        "schema_version": "1.0",
        "project": project["project_name"],
        "project_id": project["project_id"],
        "continuity_score": 100,
        "gate": "passed",
        "scores": {"character_score": 100, "prop_score": 100, "weapon_score": 100, "location_score": 100, "temporal_score": 100, "cross_model_score": 100},
        "issues": [],
        "shot_links": {},
        "asset_timelines": {"characters": {}, "props": {}, "weapons": {}, "locations": {}},
        "injury_timeline": [],
        "prop_ownership_timeline": [],
        "weapon_timeline": [],
        "time_timeline": [],
        "continuity_chain": [],
        "cross_model": {"models": ["seedance20", "seedance25", "jimeng20", "jimeng25"], "consistent": True},
    }
