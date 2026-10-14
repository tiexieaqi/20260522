"""Stage 02：为当前项目生成隔离的项目专属规则。"""

from pathlib import Path

from ai_provider import AIProvider
from config import PROJECT_ROOT
from file_utils import json_read, read_utf8
from stage01_manager import _find_named_files
from stage_base import StageRunner


RULE_NAMES = ["00_系统总控规则.md", "14_项目规则隔离规则.md", "13_历史真实性审核规则.md"]
REPORT_NAME = "02_项目专属规则.md"
REQUIRED_HEADINGS = [
    "# 项目专属规则",
    "## 1. 项目身份",
    "## 2. 人物专属规则",
    "## 3. 场景专属规则",
    "## 4. 道具与武器专属规则",
    "## 5. 群体规则",
    "## 6. 连续性专属规则",
    "## 7. 视觉风格规则",
    "## 8. 历史专属限制",
    "## 9. AI生成风险",
    "## 10. 项目禁止事项",
]


def _read_rules() -> str:
    rule_dir = PROJECT_ROOT / "新版规则库"
    return "".join(f"\n===== {p.name} =====\n{read_utf8(p)}" for p in _find_named_files(rule_dir, RULE_NAMES))


def build_stage02_prompt(project_name: str, script_text: str, report_text: str, rules_text: str) -> str:
    return f"""你是 AI影视助手的 Stage 02 项目专属规则模块。

安全边界：只分析当前项目提供的原始剧本、Stage 01 报告和指定通用规则。只能输出当前项目专属规则，不得修改任何文件，不得读取其他项目，不得把项目细节写成通用规则。

请只返回 JSON：{{"project_rules_markdown":"完整 Markdown 文档"}}。
文档必须严格包含：
{chr(10).join(REQUIRED_HEADINGS)}

只写当前故事独有的设定：人物、时代、服装、场景、天气时间、武器、道具、群体、视觉风格、连续性、历史限制、禁止事项和 AI 风险。一般影视制作常识不要重复写入。没有依据的内容标记“待确认”。项目名称：{project_name}

===== 当前原始剧本 =====
{script_text}

===== 当前项目 Stage 01 报告 =====
{report_text}

===== 仅允许参考的通用规则 =====
{rules_text}
"""


def validate_project_rules(text: str) -> None:
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in text]
    if missing:
        raise ValueError("Stage 02 输出缺少章节：" + "、".join(missing))
    if "新版规则库" in text or "其他项目" in text:
        raise ValueError("项目专属规则不应输出规则库路径或其他项目内容。")


def run_stage02(project_dir: Path, provider: AIProvider) -> str:
    project = json_read(project_dir / "project.json")
    original = next(project_dir.glob("00_原始剧本.*"))
    report = project_dir / "01_剧本解析报告.md"
    if not report.is_file() or "等待 AI 处理" in read_utf8(report):
        raise ValueError("Stage 02 需要先完成 Stage 01 报告。")
    rules = _read_rules()
    prompt = build_stage02_prompt(project["project_name"], read_utf8(original), read_utf8(report), rules)
    runner = StageRunner(project_dir, 2, REPORT_NAME, "Stage 02 项目专属规则")
    return runner.run(lambda: provider.complete(prompt), validate_project_rules)
