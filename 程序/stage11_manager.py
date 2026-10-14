"""Stage 11：历史真实性审核，只读上游并输出证据分级报告。"""

import json
from pathlib import Path

from continuity_auditor import shots_from_storyboard
from file_utils import atomic_json_write, read_utf8
from historical_auditor import audit_historical
from historical_source_provider import UnavailableHistoricalSourceProvider
from historical_validator import validate_historical_report
from model_stage_base import load_model_stage_context, read_model_sources
from stage_base import StageRunner


RULE_NAMES = ["00_系统总控规则.md", "01_剧本分析规则.md", "04_资产库总规则.md", "05_人物资产规则.md", "06_场景资产规则.md", "07_道具资产规则.md", "08_分镜导演规则.md", "13_历史真实性审核规则.md", "14_项目规则隔离规则.md"]
REPORT_NAME = "11_历史真实性审核报告.md"
JSON_NAME = "historical_report.json"
UPSTREAM = ("01_剧本解析报告.md", "02_项目专属规则.md", "03_资产库.md", "04_资产生成提示词.md", "05_标准分镜.md", "assets.json", "asset_prompts.json", "storyboard.json", "06_Seedance2.0提示词.md", "07_Seedance2.5提示词.md", "08_即梦2.0提示词.md", "09_即梦2.5提示词.md", "seedance20_prompts.json", "seedance25_prompts.json", "jimeng20_prompts.json", "jimeng25_prompts.json", "model_prompt_index.json", "10_连续性审核报告.md", "continuity_report.json")


def render_report(report: dict) -> str:
    lines = ["# 历史真实性审核报告", "", "## 一、审核结论", "", f"题材历史相关度：{report['historical_relevance']}", f"真实性评分：{report['historical_score']}", f"Gate：{report['historical_gate']}", ""]
    if report["historical_relevance"] == "none":
        lines += ["不适用：当前项目没有识别到历史题材或历史事实声明。", ""]
    lines += ["## 二、明确符合项", "", "当前离线环境不作未经来源支持的 verified 判断。", "", "## 三、需外部核验项", ""]
    lines += [f"- {claim_id}" for claim_id in report["requires_external_verification"]] or ["- 无"]
    lines += ["", "## 四、历史冲突项", ""]
    for issue in report["issues"]:
        lines += [f"### {issue['issue_id']}｜{issue['claim']}", "", f"分类：{issue['category']}", f"严重度：{issue['severity']}", f"验证状态：{issue['verification_status']}", f"涉及镜头：{'、'.join(issue['related_shots']) or '无'}", f"涉及资产：{'、'.join(issue['related_assets']) or '无'}", "", "【项目当前内容】", issue["project_current"], "", "【历史预期】", issue["historical_expected"], "", "【证据】", issue["evidence"], "", "【证据等级】", issue["evidence_level"], "", "【建议修复阶段】", issue["suggested_fix_stage"], "", "【建议修改】", issue["suggested_fix"], ""]
    for title in ("五、艺术加工项", "六、生产限制导致的历史偏差", "七、人物审核", "八、事件审核", "九、时间地点审核", "十、服装与装备", "十一、武器", "十二、建筑与生活道具", "十三、称谓与语言", "十四、军事制度", "十五、待人工确认", "十六、通过项"):
        lines += [f"## {title}", ""]
        if title == "六、生产限制导致的历史偏差": lines.append("；".join(item["description"] for item in report["production_deviations"]) or "无")
        elif title == "十五、待人工确认": lines.append("；".join(report["requires_external_verification"]) or "无")
        else: lines.append("按当前证据状态记录，未自动补充未经来源支持的结论。")
        lines.append("")
    return "\n".join(lines) + "\n"


def run_stage11(project_dir: Path, source_provider=None) -> str:
    context = load_model_stage_context(project_dir)
    original = context.original
    for name in UPSTREAM:
        if not (project_dir / name).is_file(): raise ValueError(f"Stage 11 缺少输入：{name}")
    provider = source_provider or UnavailableHistoricalSourceProvider()
    # 读取规则仅用于形成可追溯输入边界；不调用网络。
    read_model_sources("新版规则库", RULE_NAMES)
    before = {path: path.read_bytes() for path in [original] + [project_dir / name for name in UPSTREAM]}

    def operation() -> str:
        report = audit_historical(context.project, read_utf8(original), read_utf8(context.project_rules), read_utf8(context.assets_md), context.storyboard, provider)
        shot_ids = {shot["shot_id"] for shot in shots_from_storyboard(context.storyboard)}
        asset_ids = {asset_id for assets in context.registry["assets"].values() for asset_id in assets}
        validate_historical_report(report, shot_ids, asset_ids)
        if any(path.read_bytes() != content for path, content in before.items()): raise ValueError("Stage 11 修改了上游文件。")
        markdown = render_report(report)
        atomic_json_write(project_dir / JSON_NAME, report)
        return markdown

    runner = StageRunner(project_dir, 11, REPORT_NAME, "Stage 11 历史真实性审核")
    return runner.run(operation, lambda text: text.startswith("# 历史真实性审核报告") and "历史真实性评分" in text or text.startswith("# 历史真实性审核报告") and "真实性评分" in text)
