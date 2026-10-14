"""视频模型适配阶段共用的输入读取、只读保护和 Schema。"""

from dataclasses import dataclass
from pathlib import Path

from asset_schema import validate_registry
from config import PROJECT_ROOT
from file_utils import json_read, read_utf8
from stage01_manager import _find_named_files


@dataclass
class ModelStageContext:
    project_dir: Path
    project: dict
    original: Path
    project_rules: Path
    assets_md: Path
    asset_prompts_md: Path
    storyboard_md: Path
    registry_path: Path
    asset_prompts_path: Path
    storyboard_path: Path
    registry: dict
    asset_prompts: dict
    storyboard: dict
    snapshot: dict[Path, bytes]


def load_model_stage_context(project_dir: Path, protected_extra: list[str] | None = None) -> ModelStageContext:
    project = json_read(project_dir / "project.json")
    original = next(project_dir.glob("00_原始剧本.*"))
    names = ["02_项目专属规则.md", "03_资产库.md", "04_资产生成提示词.md", "05_标准分镜.md", "assets.json", "asset_prompts.json", "storyboard.json"]
    paths = [project_dir / name for name in names]
    if any(not path.is_file() for path in paths) or "等待 AI 处理" in read_utf8(project_dir / "05_标准分镜.md"):
        raise ValueError("模型适配需要先完成 Stage 05。")
    registry = json_read(paths[4]); validate_registry(registry)
    asset_prompts = json_read(paths[5]); storyboard = json_read(paths[6])
    protected = paths + [original]
    for name in protected_extra or []:
        path = project_dir / name
        if path.is_file():
            protected.append(path)
    return ModelStageContext(project_dir, project, original, paths[0], paths[1], paths[2], paths[3], paths[4], paths[5], paths[6], registry, asset_prompts, storyboard, {path: path.read_bytes() for path in protected})


def read_model_sources(directory_name: str, names: list[str]) -> str:
    directory = PROJECT_ROOT / directory_name
    return "".join(f"\n===== {path.name} =====\n{read_utf8(path)}" for path in _find_named_files(directory, names))


def ensure_inputs_unchanged(context: ModelStageContext) -> None:
    if any(path.read_bytes() != content for path, content in context.snapshot.items()):
        raise ValueError("模型适配阶段修改了只读输入文件。")


def model_plan_schema(model: str) -> dict:
    return {"type": "object", "required": ["schema_version", "model", "project_id", "project_name", "shots"], "properties": {"schema_version": {"const": "1.0"}, "model": {"const": model}, "project_id": {"type": "string"}, "project_name": {"type": "string"}, "shots": {"type": "object"}}}


def flatten_asset_refs(shot: dict) -> list[str]:
    assets = shot.get("assets", {})
    refs = list(assets.get("characters", []))
    if assets.get("location"):
        refs.append(assets["location"])
    for key in ("props", "weapons", "groups", "fx"):
        refs.extend(assets.get(key, []))
    return refs
