"""Stage 05 标准分镜的结构约定。"""

SHOT_SIZES = {"extreme_wide", "wide", "medium_wide", "medium", "medium_close", "close", "extreme_close"}
MOVEMENTS = {"locked", "slow_push", "slow_pull", "pan", "tilt", "tracking", "handheld", "arc", "follow"}
COMPLEXITIES = {"low", "medium", "high"}
DIALOGUE_TYPES = {"character_dialogue", "voiceover", "none"}


def storyboard_document(project_id: str, project_name: str, scenes: list[dict], total_duration: float, warning: bool = False, continuity_timeline: list[dict] | None = None) -> dict:
    return {
        "schema_version": "1.0",
        "project_id": project_id,
        "project_name": project_name,
        "total_duration_seconds": total_duration,
        "duration_warning": warning,
        "continuity_timeline": continuity_timeline or [],
        "scenes": scenes,
    }
