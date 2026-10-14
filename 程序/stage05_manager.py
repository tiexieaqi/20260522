"""Stage 05：生成模型无关的标准分镜。"""

import json
from pathlib import Path

from ai_provider import AIProvider
from asset_schema import validate_registry
from config import PROJECT_ROOT
from file_utils import atomic_json_write, json_read, read_utf8
from stage01_manager import _find_named_files
from stage_base import StageRunner
from storyboard_validator import validate_storyboard


RULE_NAMES = ["00_系统总控规则.md", "04_资产库总规则.md", "05_人物资产规则.md", "06_场景资产规则.md", "07_道具资产规则.md", "08_分镜导演规则.md", "13_历史真实性审核规则.md", "14_项目规则隔离规则.md"]
TEMPLATE_NAMES = ["04_分镜生成模板.md"]
REPORT_NAME = "05_标准分镜.md"
STORYBOARD_NAME = "storyboard.json"
STORYBOARD_SCHEMA = {"type": "object", "required": ["schema_version", "project_id", "project_name", "total_duration_seconds", "duration_warning", "continuity_timeline", "scenes"], "properties": {"schema_version": {"const": "1.0"}, "project_id": {"type": "string"}, "project_name": {"type": "string"}, "total_duration_seconds": {"type": "number"}, "duration_warning": {"type": "boolean"}, "continuity_timeline": {"type": "array"}, "scenes": {"type": "array"}}}


def _read_sources(directory: Path, names: list[str]) -> str:
    return "".join(f"\n===== {p.name} =====\n{read_utf8(p)}" for p in _find_named_files(directory, names))


def build_stage05_prompt(project_id: str, project_name: str, script: str, report: str, project_rules: str, assets_md: str, asset_prompt_md: str, prompts_json: dict, registry: dict, rules: str, template: str) -> str:
    return f"""你是 AI影视助手 Stage 05 标准分镜模块。

只生成模型无关的标准分镜 JSON，不要写 Seedance 或即梦专用表达。只能引用下方 assets.json 中正式存在的资产版本，不能创建、修改或猜测资产。每个镜头必须包含 shot_id、duration_seconds、story_goal、assets、camera、blocking、action、dialogue、performance_direction、movement_style、start_state、end_state、action_complexity、continuity_notes、forbidden。角色对白必须绑定 speaker_asset_id 并估算自然时长；旁白 dialogue_type=voiceover 且不得触发口型。所有镜头加入字幕/logo/水印禁止项。顶层必须提供 continuity_timeline，记录镜头结束时的人物、道具、场景、天气和时间状态。返回 {{"schema_version":"1.0","project_id":"...","project_name":"...","total_duration_seconds":0,"duration_warning":false,"continuity_timeline":[],"scenes":[]}}。

项目 ID：{project_id}
项目名称：{project_name}
===== 原始剧本 =====
{script}
===== 剧本解析 =====
{report}
===== 项目规则 =====
{project_rules}
===== 资产库 =====
{assets_md}
===== 资产生成提示词 =====
{asset_prompt_md}
===== 资产提示词登记 =====
{json.dumps(prompts_json, ensure_ascii=False, indent=2)}
===== 权威 assets.json =====
{json.dumps(registry, ensure_ascii=False, indent=2)}
===== 分镜规则 =====
{rules}
===== 分镜模板 =====
{template}
"""


def _render_markdown(project: dict, storyboard: dict) -> str:
    lines = ["# 标准分镜", "", f"项目：{project['project_name']}", f"预计成片时长：{storyboard['total_duration_seconds']}秒", ""]
    if storyboard.get("duration_warning"):
        lines += ["DURATION_WARNING：预计时长与目标时长存在差异。", ""]
    for scene in storyboard["scenes"]:
        lines += [f"# {scene['scene_id']}｜{scene.get('story_function', '剧情段')}", ""]
        for shot in scene["shots"]:
            camera = shot["camera"]
            assets = shot["assets"]
            lines += [f"## {shot['shot_id']}｜{shot['duration_seconds']}秒", "", "【剧情功能】", shot.get("story_goal", ""), "", "【本镜头资产】", f"人物：{'、'.join(assets.get('characters', [])) or '无'}", f"场景：{assets.get('location', '无')}", f"道具：{'、'.join(assets.get('props', [])) or '无'}", f"武器：{'、'.join(assets.get('weapons', [])) or '无'}", f"群体：{'、'.join(assets.get('groups', [])) or '无'}", f"效果：{'、'.join(assets.get('fx', [])) or '无'}", "", "【景别 / 焦段 / 机位】", f"{camera['shot_size']} / {camera['focal_length']} / {camera.get('height', '')} / {camera.get('angle', '')} / {camera.get('position', '')}", "", "【运镜】", camera["movement"], "", "【开始状态】", json.dumps(shot["start_state"], ensure_ascii=False), "", "【人物动作】", *[f"- {x}" for x in shot.get("action", [])], "", "【表演指导】", *[f"- {x}" for x in shot.get("performance_direction", [])], "", "【对白】"]
            if shot.get("dialogue"):
                for dialogue in shot["dialogue"]:
                    speaker = dialogue.get("speaker_asset_id") or "后期旁白"
                    lines.append(f"{speaker}（{dialogue['dialogue_type']}，约{dialogue['estimated_duration']}秒）：{dialogue.get('dialogue', '')}")
            else:
                lines.append("无")
            lines += ["", "【结束状态】", json.dumps(shot["end_state"], ensure_ascii=False), "", "【连续性】", "、".join(shot.get("continuity_notes", [])) or "无", "", "【强制禁止】", "、".join(shot["forbidden"]), ""]
    lines += ["## 连续性时间线", ""]
    for item in storyboard.get("continuity_timeline", []):
        lines.append(f"- {json.dumps(item, ensure_ascii=False)}")
    return "\n".join(lines) + "\n"


def run_stage05(project_dir: Path, provider: AIProvider) -> str:
    project = json_read(project_dir / "project.json")
    original = next(project_dir.glob("00_原始剧本.*"))
    inputs = [project_dir / name for name in ("01_剧本解析报告.md", "02_项目专属规则.md", "03_资产库.md", "04_资产生成提示词.md", "asset_prompts.json")]
    registry_path = project_dir / "assets.json"
    if any(not path.is_file() for path in inputs + [registry_path]) or any("等待 AI 处理" in read_utf8(path) for path in inputs[:3]):
        raise ValueError("Stage 05 需要先完成 Stage 01—04。")
    registry = json_read(registry_path); validate_registry(registry)
    prompts_json = json_read(inputs[4]); before = {path: path.read_bytes() for path in inputs + [registry_path]}
    rules = _read_sources(PROJECT_ROOT / "新版规则库", RULE_NAMES); template = _read_sources(PROJECT_ROOT / "15_模板库", TEMPLATE_NAMES)
    prompt = build_stage05_prompt(project["project_id"], project["project_name"], read_utf8(original), read_utf8(inputs[0]), read_utf8(inputs[1]), read_utf8(inputs[2]), read_utf8(inputs[3]), prompts_json, registry, rules, template)

    def operation() -> str:
        storyboard = json.loads(provider.complete(prompt, schema=STORYBOARD_SCHEMA))
        validate_storyboard(storyboard, registry)
        if storyboard.get("project_id") != project["project_id"]:
            raise ValueError("storyboard project_id 与当前项目不一致。")
        markdown = _render_markdown(project, storyboard)
        if any(path.read_bytes() != content for path, content in before.items()):
            raise ValueError("Stage 05 修改了只读输入文件。")
        atomic_json_write(project_dir / STORYBOARD_NAME, storyboard)
        return markdown

    runner = StageRunner(project_dir, 5, REPORT_NAME, "Stage 05 标准分镜")
    return runner.run(operation, lambda text: text.startswith("# 标准分镜") and "预计成片时长" in text)
