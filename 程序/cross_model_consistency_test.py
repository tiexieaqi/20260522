"""四模型对照校验：只比较共同事实，不比较模型提示词文风。"""

import json
from pathlib import Path


def _shots(document: dict) -> dict:
    if "shots" in document and isinstance(document["shots"], dict):
        return document["shots"]
    return {shot["shot_id"]: shot for scene in document["scenes"] for shot in scene["shots"]}


def validate_project(project_dir: Path) -> None:
    storyboard = _shots(json.loads((project_dir / "storyboard.json").read_text(encoding="utf-8")))
    model_files = ("seedance20_prompts.json", "seedance25_prompts.json", "jimeng20_prompts.json", "jimeng25_prompts.json")
    models = [_shots(json.loads((project_dir / name).read_text(encoding="utf-8"))) for name in model_files]
    for model in models:
        if list(model) != list(storyboard):
            raise ValueError("四模型镜头顺序或覆盖范围不一致。")
        for shot_id, source in storyboard.items():
            item = model[shot_id]
            if item.get("source_shot_id") != shot_id or item.get("asset_refs") != _asset_refs(source) or item.get("dialogue") != source.get("dialogue", []) or item.get("start_state") != source.get("start_state") or item.get("end_state") != source.get("end_state"):
                raise ValueError(f"四模型共同事实不一致：{shot_id}")
    index_path = project_dir / "model_prompt_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if list(index.get("shots", {})) != list(storyboard):
        raise ValueError("model_prompt_index.json 覆盖范围不一致。")


def _asset_refs(shot: dict) -> list[str]:
    assets = shot.get("assets", {})
    refs = list(assets.get("characters", []))
    if assets.get("location"): refs.append(assets["location"])
    for key in ("props", "weapons", "groups", "fx"):
        refs.extend(assets.get(key, []))
    return refs


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("用法：python cross_model_consistency_test.py 项目目录")
    validate_project(Path(sys.argv[1]))
    print("cross_model_consistency_test：通过")
