"""Stage 01：读取规则和模板，调用 Provider 生成剧本解析报告。"""

from pathlib import Path

from ai_provider import AIProvider, AIProviderError
from config import PROJECT_ROOT
from file_utils import json_read, read_utf8
from stage_base import StageRunner


RULE_NAMES = [
    "00_系统总控规则.md",
    "01_剧本分析规则.md",
    "13_历史真实性审核规则.md",
    "14_项目规则隔离规则.md",
]
TEMPLATE_NAMES = [
    "01_剧本输入模板.md",
    "02_历史人物分析模板.md",
]
REPORT_NAME = "01_剧本解析报告.md"
REQUIRED_HEADINGS = [
    "# 剧本解析报告",
    "## 1. 项目基本信息",
    "## 2. 故事核心",
    "## 3. 人物分析",
    "## 4. 场景分析",
    "## 5. 道具与资产线索",
    "## 6. 情绪曲线",
    "## 7. 制作难点",
    "## 8. 历史真实性风险",
    "## 9. AI生成风险",
    "## 10. 下一阶段建议",
]


def _find_named_files(directory: Path, names: list[str]) -> list[Path]:
    files = []
    for name in names:
        exact = directory / name
        if exact.is_file():
            files.append(exact)
            continue
        matches = sorted(directory.glob(f"*{name}"))
        if not matches:
            raise FileNotFoundError(f"找不到所需文件：{directory / name}")
        files.append(matches[0])
    return files


def _read_sources(directory: Path, names: list[str]) -> str:
    parts = []
    for path in _find_named_files(directory, names):
        parts.append(f"\n===== {path.name} =====\n{read_utf8(path)}")
    return "".join(parts)


def build_stage01_prompt(project_name: str, script_text: str, rules_text: str, templates_text: str) -> str:
    return f"""你是 AI影视助手的 Stage 01 剧本解析模块。

安全边界：你只能分析下方提供的剧本、规则和模板文本；不要修改任何文件，不要调用网络，不要生成 CH/LOC/PROP/WPN/GRP/FX 正式编号。

请只返回一个 JSON 对象，格式必须是：{{"report_markdown":"完整 Markdown 报告"}}。
report_markdown 必须严格包含以下标题，并使用中文：
{chr(10).join(REQUIRED_HEADINGS)}

报告要求：覆盖项目基本信息、故事核心、人物、场景、资产候选、情绪曲线、制作难点、历史真实性风险、AI生成风险和下一阶段建议。资产部分只列候选，不分配正式 ID。历史题材列出待核验内容，非历史题材明确写“不适用”。所有不确定内容标记“待确认”。

项目名称：{project_name}

===== 剧本 =====
{script_text}

===== 规则 =====
{rules_text}

===== 模板 =====
{templates_text}
"""


def validate_report(report: str) -> None:
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in report]
    if missing:
        raise ValueError("Stage 01 输出缺少章节：" + "、".join(missing))
    if "CH-001" in report or "LOC-001" in report or "PROP-001" in report:
        raise ValueError("Stage 01 不应分配正式资产编号。")


def run_stage01(project_dir: Path, provider: AIProvider) -> str:
    project = json_read(project_dir / "project.json")
    def operation() -> str:
        original = next(project_dir.glob("00_原始剧本.*"))
        rules_text = _read_sources(PROJECT_ROOT / "新版规则库", RULE_NAMES)
        templates_text = _read_sources(PROJECT_ROOT / "15_模板库", TEMPLATE_NAMES)
        prompt = build_stage01_prompt(
            project["project_name"],
            read_utf8(original),
            rules_text,
            templates_text,
        )
        return provider.complete(prompt)
    runner = StageRunner(project_dir, 1, REPORT_NAME, "Stage 01 剧本解析")
    return runner.run(operation, validate_report)
