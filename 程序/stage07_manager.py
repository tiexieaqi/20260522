"""Stage 07：从 Stage 05 母版直接生成 Seedance 2.5 提示词。"""

import json
from pathlib import Path

from ai_provider import AIProvider
from file_utils import atomic_json_write, json_read, read_utf8
from model_prompt_validator import validate_model_plan
from model_stage_base import ensure_inputs_unchanged, load_model_stage_context, model_plan_schema, read_model_sources
from seedance25_adapter import ADAPTATION_STRATEGIES, MODEL_PROMPT_BUDGET
from stage_base import StageRunner


RULE_NAMES = ["00_系统总控规则.md", "04_资产库总规则.md", "05_人物资产规则.md", "06_场景资产规则.md", "07_道具资产规则.md", "08_分镜导演规则.md", "10_Seedance2.5规则.md", "13_历史真实性审核规则.md", "14_项目规则隔离规则.md"]
TEMPLATE_NAMES = ["06_Seedance2.5提示词模板.md"]
REPORT_NAME = "07_Seedance2.5提示词.md"
JSON_NAME = "seedance25_prompts.json"
PLAN_SCHEMA = model_plan_schema("seedance-2.5")


def build_stage07_prompt(context, rules: str, template: str) -> str:
    return f"""你是 AI影视助手 Stage 07 Seedance 2.5 适配模块。

只能直接从 storyboard.json 生成 Seedance 2.5 提示词。不得使用 Seedance 2.0 输出作为母版，不得改写剧情、编号、资产、对白、speaker、首尾状态、摄影意图或镜头数量。返回统一 ModelPrompt JSON：schema_version=1.0、model=seedance-2.5、project_id={context.project['project_id']}、project_name、shots。

每个镜头必须包含 source_shot_id、duration_seconds、asset_refs、prompt、timeline、dialogue、start_state、end_state、forbidden、risk、model_duration_status、source_rules，并增加 action_beats、performance_timing、dialogue_timing、adaptation_strategy、adapter_profile=seedance-2.5、adaptation_features、model_prompt_budget={MODEL_PROMPT_BUDGET}、model_rule_gap。action_beats 使用准备→核心→反应的顺序；高复杂度镜头只能调整表达次序并给 warning，不能改变母版。规则未提供专属参数语法，model_rule_gap 必须记录 MODEL_RULE_GAP。每条提示词不超过预算。

项目 ID：{context.project['project_id']}
项目名称：{context.project['project_name']}
===== 原始剧本 =====
{read_utf8(context.original)}
===== 项目专属规则 =====
{read_utf8(context.project_rules)}
===== 资产库 =====
{read_utf8(context.assets_md)}
===== 资产提示词 =====
{read_utf8(context.asset_prompts_md)}
===== 标准分镜 =====
{read_utf8(context.storyboard_md)}
===== storyboard.json（唯一母版） =====
{json.dumps(context.storyboard, ensure_ascii=False, indent=2)}
===== assets.json =====
{json.dumps(context.registry, ensure_ascii=False, indent=2)}
===== asset_prompts.json =====
{json.dumps(context.asset_prompts, ensure_ascii=False, indent=2)}
===== Seedance 2.5规则 =====
{rules}
===== Seedance 2.5模板 =====
{template}
"""


def validate_seedance25(plan: dict, context) -> None:
    required = ("timeline", "action_beats", "performance_timing", "dialogue_timing", "adaptation_strategy", "adapter_profile", "adaptation_features", "model_prompt_budget", "model_rule_gap")
    validate_model_plan(plan, context.storyboard, context.registry, context.asset_prompts, model="seedance-2.5", prompt_budget=MODEL_PROMPT_BUDGET, required_shot_fields=required)
    source_shots = {shot["shot_id"]: shot for scene in context.storyboard["scenes"] for shot in scene["shots"]}
    for shot_id, item in plan["shots"].items():
        source = source_shots[shot_id]
        if item["adapter_profile"] != "seedance-2.5" or item["adaptation_strategy"] not in ADAPTATION_STRATEGIES:
            raise ValueError(f"Seedance 2.5 适配配置无效：{shot_id}")
        if item["model_prompt_budget"] != MODEL_PROMPT_BUDGET:
            raise ValueError(f"模型 Prompt 预算不一致：{shot_id}")
        beats = item["action_beats"]
        if not isinstance(beats, list) or not beats or [beat.get("order") for beat in beats] != list(range(1, len(beats) + 1)):
            raise ValueError(f"action_beats 顺序无效：{shot_id}")
        source_actions = source.get("action", []) or ["保持开始状态，完成剧情目标"]
        if len(beats) != len(source_actions) or any(action not in beat.get("action", "") for action, beat in zip(source_actions, beats)):
            raise ValueError(f"action_beats 改变了标准分镜动作：{shot_id}")
        if not isinstance(item["performance_timing"], list) or len(item["performance_timing"]) > min(3, len(source.get("performance_direction", []))):
            raise ValueError(f"performance_timing 超出标准分镜表演指导：{shot_id}")
        timing = item["dialogue_timing"]
        expected_timing = [{"speaker_asset_id": d.get("speaker_asset_id"), "dialogue_type": d["dialogue_type"], "estimated_duration": d["estimated_duration"], "pause_before": d["pause_before"], "pause_after": d["pause_after"]} for d in source.get("dialogue", [])]
        if timing != expected_timing:
            raise ValueError(f"dialogue_timing 改变了原对白节奏：{shot_id}")
        if item["model_rule_gap"] != "MODEL_RULE_GAP":
            raise ValueError(f"模型规则缺口未标记：{shot_id}")
    seedance20_path = context.project_dir / "seedance20_prompts.json"
    if seedance20_path.is_file():
        source20 = json_read(seedance20_path).get("shots", {})
        if any(source20.get(shot_id, {}).get("source_shot_id") != item["source_shot_id"] for shot_id, item in plan["shots"].items()):
            raise ValueError("Seedance 2.0 与 2.5 的 source_shot_id 不一致。")


def render_markdown(context, plan: dict) -> str:
    lines = ["# Seedance 2.5 视频提示词", "", f"项目：{context.project['project_name']}", "", "说明：直接从 Stage 05 母版平行适配，不读取 Seedance 2.0 提示词作为内容输入。", ""]
    for shot_id, item in plan["shots"].items():
        lines += [f"## {shot_id}｜{item['duration_seconds']}秒", "", "【本段引用资产】", "、".join(item["asset_refs"]) or "无", "", "【开始状态】", json.dumps(item["start_state"], ensure_ascii=False), "", "【镜头设计 / 视频提示词】", item["prompt"], "", "【动作时间线】"]
        lines += [f"- {beat['order']}｜{beat['action']}｜约{beat['duration_hint']}秒" for beat in item["action_beats"]]
        performance_lines = [f"- {x.get('direction', '')}｜{x.get('timing', '')}" for x in item["performance_timing"]] or ["无"]
        lines += ["", "【人物表演】", *performance_lines, "", "【对白 / 口型】"]
        dialogue_lines = [json.dumps(x, ensure_ascii=False) for x in item["dialogue"]] or ["无"]
        lines += dialogue_lines
        lines += ["", "【结束状态】", json.dumps(item["end_state"], ensure_ascii=False), "", "【连续性要求】", "、".join(item["source_rules"]) or "无", "", "【Seedance 2.5风险】", f"{item['risk']['level']}：{'、'.join(item['risk']['reasons']) or '无'}", "", "【适配策略】", item["adaptation_strategy"], "", "【规则缺口】", item["model_rule_gap"], "", "【强制禁止】", "、".join(item["forbidden"]), ""]
    return "\n".join(lines) + "\n"


def run_stage07(project_dir: Path, provider: AIProvider) -> str:
    context = load_model_stage_context(project_dir, protected_extra=["06_Seedance2.0提示词.md", "seedance20_prompts.json"])
    rules = read_model_sources("新版规则库", RULE_NAMES)
    template = read_model_sources("15_模板库", TEMPLATE_NAMES)
    prompt = build_stage07_prompt(context, rules, template)

    def operation() -> str:
        plan = json.loads(provider.complete(prompt, schema=PLAN_SCHEMA))
        if plan.get("project_id") != context.project["project_id"]:
            raise ValueError("Seedance 2.5 输出项目 ID 不一致。")
        validate_seedance25(plan, context)
        ensure_inputs_unchanged(context)
        markdown = render_markdown(context, plan)
        atomic_json_write(project_dir / JSON_NAME, plan)
        return markdown

    runner = StageRunner(project_dir, 7, REPORT_NAME, "Stage 07 Seedance 2.5 提示词")
    return runner.run(operation, lambda text: text.startswith("# Seedance 2.5 视频提示词") and "## " in text)
