"""Stage 06：将模型无关分镜适配为 Seedance 2.0 提示词。"""

import json
from pathlib import Path

from ai_provider import AIProvider
from file_utils import atomic_json_write, read_utf8
from model_adapter_base import ModelAdapter
from model_stage_base import ensure_inputs_unchanged, load_model_stage_context, model_plan_schema, read_model_sources
from seedance_prompt_validator import validate_seedance_plan
from stage_base import StageRunner


RULE_NAMES = ["00_系统总控规则.md", "04_资产库总规则.md", "05_人物资产规则.md", "06_场景资产规则.md", "07_道具资产规则.md", "08_分镜导演规则.md", "09_Seedance2.0规则.md", "13_历史真实性审核规则.md", "14_项目规则隔离规则.md"]
TEMPLATE_NAMES = ["05_Seedance2.0提示词模板.md"]
REPORT_NAME = "06_Seedance2.0提示词.md"
JSON_NAME = "seedance20_prompts.json"
PLAN_SCHEMA = model_plan_schema("seedance-2.0")


def _all_shots(storyboard: dict) -> dict[str, dict]:
    return {shot["shot_id"]: shot for scene in storyboard["scenes"] for shot in scene["shots"]}


def build_stage06_prompt(project: dict, script: str, project_rules: str, assets_md: str, asset_prompts_md: str, storyboard_md: str, registry: dict, asset_prompts: dict, storyboard: dict, rules: str, template: str) -> str:
    return f"""你是 AI影视助手 Stage 06 Seedance 2.0 适配模块。

只能把 storyboard.json 的每个镜头转换成 Seedance 2.0 提示词。不得改剧情、镜头编号、资产 ID、对白、首尾状态或增加删除镜头。必须返回 JSON，包含 schema_version=1.0、model=seedance-2.0、project_id={project['project_id']}、project_name 和 shots 对象。每个 shots[shot_id] 必须有 source_shot_id、duration_seconds、asset_refs、prompt、timeline、dialogue、start_state、end_state、forbidden、risk(level/reasons)、model_duration_status、source_rules。

提示词要线性表达动作时间顺序，引用资产 ID，保留自然动作、机位、对白和连续性。旁白只供后期配音参考，画面人物不开口。发现执行风险只能填写 warning 或 risk，不得回写 storyboard。不得在提示词中使用其他模型名称。每条提示词不超过 3000 字符。

项目 ID：{project['project_id']}
项目名称：{project['project_name']}
===== 原始剧本 =====
{script}
===== 项目规则 =====
{project_rules}
===== 资产库 =====
{assets_md}
===== 资产提示词 =====
{asset_prompts_md}
===== 标准分镜 =====
{storyboard_md}
===== storyboard.json =====
{json.dumps(storyboard, ensure_ascii=False, indent=2)}
===== assets.json =====
{json.dumps(registry, ensure_ascii=False, indent=2)}
===== asset_prompts.json =====
{json.dumps(asset_prompts, ensure_ascii=False, indent=2)}
===== 适配规则 =====
{rules}
===== 适配模板 =====
{template}
"""


def render_seedance_markdown(project: dict, plan: dict) -> str:
    lines = ["# Seedance 2.0 视频提示词", "", f"项目：{project['project_name']}", "", "说明：本文件逐镜头继承 Stage 05 标准分镜，不回写母版。", ""]
    for shot_id, item in plan["shots"].items():
        risk = item["risk"]
        lines += [f"## {shot_id}｜{item['duration_seconds']}秒", "", "【本段引用资产】", "、".join(item["asset_refs"]) or "无", "", "【开始状态】", json.dumps(item["start_state"], ensure_ascii=False), "", "【视频提示词】", item["prompt"], "", "【动作时间线】", *[f"- {line}" for line in item["timeline"]], "", "【对白 / 口型】"]
        if item["dialogue"]:
            for dialogue in item["dialogue"]:
                lines.append(json.dumps(dialogue, ensure_ascii=False))
        else:
            lines.append("无")
        lines += ["", "【结束状态】", json.dumps(item["end_state"], ensure_ascii=False), "", "【连续性】", "、".join(item.get("source_rules", [])), "", "【Seedance 2.0风险】", f"{risk['level']}：{'、'.join(risk['reasons']) or '无'}", "", "【模型时长状态】", item["model_duration_status"], "", "【强制禁止】", "、".join(item["forbidden"]), ""]
    return "\n".join(lines) + "\n"


def run_stage06(project_dir: Path, provider: AIProvider, adapter: ModelAdapter | None = None) -> str:
    context = load_model_stage_context(project_dir)
    project, registry, asset_prompts, storyboard = context.project, context.registry, context.asset_prompts, context.storyboard
    rules = read_model_sources("新版规则库", RULE_NAMES)
    template = read_model_sources("15_模板库", TEMPLATE_NAMES)
    prompt = build_stage06_prompt(project, read_utf8(context.original), read_utf8(context.project_rules), read_utf8(context.assets_md), read_utf8(context.asset_prompts_md), read_utf8(context.storyboard_md), registry, asset_prompts, storyboard, rules, template)

    def operation() -> str:
        plan = json.loads(provider.complete(prompt, schema=PLAN_SCHEMA))
        if plan.get("project_id") != project["project_id"]:
            raise ValueError("Seedance 2.0 输出项目 ID 不一致。")
        validate_seedance_plan(plan, storyboard, registry, asset_prompts)
        ensure_inputs_unchanged(context)
        markdown = render_seedance_markdown(project, plan)
        atomic_json_write(project_dir / JSON_NAME, plan)
        return markdown

    runner = StageRunner(project_dir, 6, REPORT_NAME, "Stage 06 Seedance 2.0 提示词")
    return runner.run(operation, lambda text: text.startswith("# Seedance 2.0 视频提示词") and "## " in text)
