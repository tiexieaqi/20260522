"""Stage 09：从 storyboard.json 平行生成即梦 2.5 双提示词。"""

import json
from pathlib import Path

from ai_provider import AIProvider
from file_utils import atomic_json_write, read_utf8
from jimeng25_adapter import JIMENG25_CINEMATIC_BUDGET, JIMENG25_STABLE_BUDGET
from jimeng25_validator import validate_jimeng25_plan
from model_stage_base import ensure_inputs_unchanged, load_model_stage_context, model_plan_schema, read_model_sources
from stage_base import StageRunner


RULE_NAMES = ["00_系统总控规则.md", "04_资产库总规则.md", "05_人物资产规则.md", "06_场景资产规则.md", "07_道具资产规则.md", "08_分镜导演规则.md", "12_即梦2.5规则.md", "13_历史真实性审核规则.md", "14_项目规则隔离规则.md"]
TEMPLATE_NAMES = ["08_即梦2.5提示词模板.md"]
REPORT_NAME = "09_即梦2.5提示词.md"
JSON_NAME = "jimeng25_prompts.json"
INDEX_NAME = "model_prompt_index.json"
PLAN_SCHEMA = model_plan_schema("jimeng-2.5")


def build_stage09_prompt(context, rules: str, template: str) -> str:
    return f"""你是 AI影视助手 Stage 09 即梦 2.5 适配模块。

唯一母版是 storyboard.json。不得读取即梦 2.0 或任何 Seedance Prompt 作为内容母版；不得改变剧情、镜头、资产、对白、speaker、首尾状态或镜头数量。返回统一 ModelPrompt JSON，model=jimeng-2.5，project_id={context.project['project_id']}。

每个镜头必须包含 source_shot_id、duration_seconds、asset_refs、prompt、adapter_profile=jimeng-2.5、stable_prompt、cinematic_prompt、recommended_prompt_mode、recommendation_reason、cinematic_features、cinematic_budget、action_beats、performance_beats、dialogue_timing、end_frame_anchor、dialogue、start_state、end_state、forbidden、risk(level/reasons)、jimeng25_risk、risk_reasons、jimeng25_prompt_budget、model_duration_status、source_rules。stable 只保留核心事实；cinematic 只能增强景深、表演、光线、材质和真实运动质感，不能增加动作、人物、道具、爆炸、台词或改变空间。高风险推荐 stable，并说明原因。若规则没有专属参数，保持保守表达。提示词分别不超过 stable_budget={JIMENG25_STABLE_BUDGET} 和 cinematic_budget={JIMENG25_CINEMATIC_BUDGET}。

项目 ID：{context.project['project_id']}
项目名称：{context.project['project_name']}
===== 原始剧本 =====\n{read_utf8(context.original)}
===== 项目规则 =====\n{read_utf8(context.project_rules)}
===== 资产库 =====\n{read_utf8(context.assets_md)}
===== 资产生成提示词 =====\n{read_utf8(context.asset_prompts_md)}
===== 标准分镜（唯一母版） =====\n{read_utf8(context.storyboard_md)}
===== storyboard.json =====\n{json.dumps(context.storyboard, ensure_ascii=False, indent=2)}
===== assets.json =====\n{json.dumps(context.registry, ensure_ascii=False, indent=2)}
===== 即梦 2.5规则 =====\n{rules}
===== 即梦 2.5模板 =====\n{template}
"""


def render_markdown(context, plan: dict) -> str:
    lines = ["# 即梦 2.5 视频提示词", "", f"项目：{context.project['project_name']}", "", "说明：直接从 Stage 05 storyboard.json 平行适配，不回写其他模型结果。", ""]
    for shot_id, item in plan["shots"].items():
        action_lines = [f"- {b['order']}｜{b['action']}｜约{b['duration_hint']}秒" for b in item["action_beats"]]
        performance_lines = [f"- {x}" for x in item["performance_beats"]] or ["无"]
        lines += [f"## {shot_id}｜{item['duration_seconds']}秒", "", "【推荐模式】", item["recommended_prompt_mode"], "", "【风险】", f"{item['jimeng25_risk']}：{'、'.join(item['risk_reasons']) or '无'}", "", "【强制禁止】", "、".join(item["forbidden"]), "", "【本段引用资产】", "、".join(item["asset_refs"]) or "无", "", "【开始状态】", json.dumps(item["start_state"], ensure_ascii=False), "", "【动作时间线】", *action_lines, "", "【人物表演】", *performance_lines, "", "【对白 / 口型】"]
        lines += [json.dumps(d, ensure_ascii=False) for d in item["dialogue"]] or ["无"]
        lines += ["", "【结束状态】", json.dumps(item["end_state"], ensure_ascii=False), "", "【连续性】", "、".join(item.get("source_rules", [])) or "无", "", "### 稳定版提示词", item["stable_prompt"], "", "### 电影增强版提示词", item["cinematic_prompt"], "", "【电影增强项】", "、".join(item["cinematic_features"]) or "无", ""]
    return "\n".join(lines) + "\n"


def build_model_prompt_index(context, plan: dict) -> dict:
    return {"schema_version": "1.0", "project_id": context.project["project_id"], "project_name": context.project["project_name"], "shots": {shot_id: {"source_shot_id": shot_id, "seedance20": "seedance20_prompts.json#" + shot_id, "seedance25": "seedance25_prompts.json#" + shot_id, "jimeng20": "jimeng20_prompts.json#" + shot_id, "jimeng25": "jimeng25_prompts.json#" + shot_id} for shot_id in plan["shots"]}}


def run_stage09(project_dir: Path, provider: AIProvider) -> str:
    context = load_model_stage_context(project_dir)
    rules = read_model_sources("新版规则库", RULE_NAMES)
    template = read_model_sources("15_模板库", TEMPLATE_NAMES)
    prompt = build_stage09_prompt(context, rules, template)

    def operation() -> str:
        plan = json.loads(provider.complete(prompt, schema=PLAN_SCHEMA))
        if plan.get("project_id") != context.project["project_id"]:
            raise ValueError("即梦 2.5 输出项目 ID 不一致。")
        validate_jimeng25_plan(plan, context.storyboard, context.registry, context.asset_prompts)
        ensure_inputs_unchanged(context)
        markdown = render_markdown(context, plan)
        atomic_json_write(project_dir / JSON_NAME, plan)
        atomic_json_write(project_dir / INDEX_NAME, build_model_prompt_index(context, plan))
        return markdown

    runner = StageRunner(project_dir, 9, REPORT_NAME, "Stage 09 即梦 2.5 提示词")
    return runner.run(operation, lambda text: text.startswith("# 即梦 2.5 视频提示词") and "## " in text)
