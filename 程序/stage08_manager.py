"""Stage 08：从 storyboard.json 平行生成即梦 2.0 提示词。"""

import json
from pathlib import Path

from ai_provider import AIProvider
from file_utils import atomic_json_write, read_utf8
from jimeng20_validator import validate_jimeng20_plan
from model_stage_base import ensure_inputs_unchanged, load_model_stage_context, model_plan_schema, read_model_sources
from stage_base import StageRunner


RULE_NAMES = ["00_系统总控规则.md", "04_资产库总规则.md", "05_人物资产规则.md", "06_场景资产规则.md", "07_道具资产规则.md", "08_分镜导演规则.md", "11_即梦2.0规则.md", "13_历史真实性审核规则.md", "14_项目规则隔离规则.md"]
TEMPLATE_NAMES = ["07_即梦2.0提示词模板.md"]
REPORT_NAME = "08_即梦2.0提示词.md"
JSON_NAME = "jimeng20_prompts.json"
PLAN_SCHEMA = model_plan_schema("jimeng-2.0")


def build_stage08_prompt(context, rules: str, template: str) -> str:
    return f"""你是 AI影视助手 Stage 08 即梦 2.0 适配模块。

必须直接从 storyboard.json 生成，即梦 2.0 与 Seedance 适配平行。不得读取或改写任何 Seedance Prompt 作为内容母版。不得改变剧情、镜头编号、资产、对白、speaker、首尾状态、摄影意图或镜头数量。返回统一 ModelPrompt JSON，model=jimeng-2.0，project_id={context.project['project_id']}。

每个镜头必须包含 source_shot_id、duration_seconds、asset_refs、prompt、adapter_profile=jimeng-2.0、standard_prompt、stable_prompt、prompt_mode、end_frame_anchor、dialogue、start_state、end_state、forbidden、risk(level/reasons)、jimeng20_risk、risk_reasons、jimeng20_prompt_budget、model_duration_status、source_rules、warnings。高风险使用 stable_short 并标记 JIMENG20_ADAPTATION_WARNING。对白逐字继承，旁白不得生成口型。物理状态必须使用结果约束式描述。若对白总时长超过镜头时长，保留对白并标记 DIALOGUE_DURATION_WARNING。提示词短、清楚、直接，不增加动作。

项目 ID：{context.project['project_id']}
项目名称：{context.project['project_name']}
===== 原始剧本 =====\n{read_utf8(context.original)}
===== 项目规则 =====\n{read_utf8(context.project_rules)}
===== 资产库 =====\n{read_utf8(context.assets_md)}
===== 资产生成提示词 =====\n{read_utf8(context.asset_prompts_md)}
===== 标准分镜（唯一母版） =====\n{read_utf8(context.storyboard_md)}
===== storyboard.json =====\n{json.dumps(context.storyboard, ensure_ascii=False, indent=2)}
===== 资产登记 =====\n{json.dumps(context.registry, ensure_ascii=False, indent=2)}
===== 即梦 2.0规则 =====\n{rules}
===== 即梦 2.0模板 =====\n{template}
"""


def render_markdown(context, plan: dict) -> str:
    lines = ["# 即梦 2.0 视频提示词", "", f"项目：{context.project['project_name']}", "", "说明：直接从 Stage 05 storyboard.json 平行适配。", ""]
    for shot_id, item in plan["shots"].items():
        lines += [f"## {shot_id}｜{item['duration_seconds']}秒", "", "【强制禁止】", "、".join(item["forbidden"]), "", "【本段引用资产】", "、".join(item["asset_refs"]) or "无", "", "【开始状态】", json.dumps(item["start_state"], ensure_ascii=False), "", "【景别 / 焦段 / 机位 / 运镜】", item["standard_prompt"], "", "【稳定版短提示词】", item["stable_prompt"], "", "【对白 / 口型】"]
        lines += [json.dumps(x, ensure_ascii=False) for x in item["dialogue"]] or ["无"]
        lines += ["", "【结束状态】", json.dumps(item["end_state"], ensure_ascii=False), "", "【尾帧锚点】", json.dumps(item["end_frame_anchor"], ensure_ascii=False), "", "【连续性要求】", "、".join(item.get("source_rules", [])) or "无", "", "【即梦 2.0风险】", f"{item['jimeng20_risk']}：{'、'.join(item['risk_reasons']) or '无'}", "", "【模式】", item["prompt_mode"], "", "【警告】", "、".join(item.get("warnings", [])) or "无", ""]
    return "\n".join(lines) + "\n"


def run_stage08(project_dir: Path, provider: AIProvider) -> str:
    context = load_model_stage_context(project_dir)
    rules = read_model_sources("新版规则库", RULE_NAMES)
    template = read_model_sources("15_模板库", TEMPLATE_NAMES)
    prompt = build_stage08_prompt(context, rules, template)

    def operation() -> str:
        plan = json.loads(provider.complete(prompt, schema=PLAN_SCHEMA))
        if plan.get("project_id") != context.project["project_id"]:
            raise ValueError("即梦 2.0 输出项目 ID 不一致。")
        validate_jimeng20_plan(plan, context.storyboard, context.registry, context.asset_prompts)
        ensure_inputs_unchanged(context)
        markdown = render_markdown(context, plan)
        atomic_json_write(project_dir / JSON_NAME, plan)
        return markdown

    runner = StageRunner(project_dir, 8, REPORT_NAME, "Stage 08 即梦 2.0 提示词")
    return runner.run(operation, lambda text: text.startswith("# 即梦 2.0 视频提示词") and "## " in text)
