"""Stage 04：为 Stage 03 已锁定资产生成图片提示词。"""

import json
from pathlib import Path

from ai_provider import AIProvider
from asset_schema import ASSET_CATEGORIES, validate_registry
from config import PROJECT_ROOT
from file_utils import atomic_json_write, json_read, read_utf8
from stage01_manager import _find_named_files
from stage_base import StageRunner


RULE_NAMES = ["00_系统总控规则.md", "04_资产库总规则.md", "05_人物资产规则.md", "06_场景资产规则.md", "07_道具资产规则.md", "13_历史真实性审核规则.md", "14_项目规则隔离规则.md"]
TEMPLATE_NAMES = ["03_资产库生成模板.md"]
REPORT_NAME = "04_资产生成提示词.md"
PROMPTS_NAME = "asset_prompts.json"
PROMPT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["prompts"],
    "properties": {"prompts": {"type": "array", "items": {"type": "object", "required": ["asset_id", "version", "prompt", "negative", "locked_fields", "source_assets"], "properties": {"asset_id": {"type": "string"}, "version": {"type": "string"}, "prompt": {"type": "string"}, "negative": {"type": "array", "items": {"type": "string"}}, "locked_fields": {"type": "array", "items": {"type": "string"}}, "source_assets": {"type": "array", "items": {"type": "string"}}}}}},
}


def _read_sources(directory: Path, names: list[str]) -> str:
    return "".join(f"\n===== {path.name} =====\n{read_utf8(path)}" for path in _find_named_files(directory, names))


def _expected_prompts(registry: dict) -> dict[str, dict]:
    expected = {}
    for category in ASSET_CATEGORIES:
        for asset_id, asset in registry["assets"][category].items():
            for version in asset["versions"]:
                key = version["version"]
                expected[key] = {"asset_id": asset_id, "version": key, "asset": asset, "category": category}
    return expected


def build_stage04_prompt(project_name: str, script: str, report: str, project_rules: str, asset_markdown: str, registry: dict, rules: str, template: str) -> str:
    return f"""你是 AI影视助手的 Stage 04 资产生成提示词模块。

安全边界：只能为下方 assets.json 中已经存在的正式资产和版本生成提示词。不得创建资产、修改 ID、添加版本、改变锁定字段、读取其他项目或修改文件。只返回 JSON：{{"prompts":[...]}}。

每个资产版本必须有一条记录。asset_id 和 version 必须来自 assets.json。提示词面向真人影视生成，区分锁定项和可变化项；V02/V03 必须写明保持 V01 基础资产不变，只改变已定义状态。negative 至少包含无字幕、无文字、无 logo、无水印、无 UI、无二维码、无乱码。武器型号待确认时不得擅自指定型号。群体提示词必须强调脸型、身高、姿势和装备差异，禁止机械复制。场景版本必须保持空间结构。每条记录在 source_assets 中引用正式 asset_id。

项目：{project_name}
===== 原始剧本 =====
{script}
===== Stage 01 =====
{report}
===== Stage 02 =====
{project_rules}
===== Stage 03 可读资产库 =====
{asset_markdown}
===== Stage 03 权威 assets.json =====
{json.dumps(registry, ensure_ascii=False, indent=2)}
===== 规则 =====
{rules}
===== 模板 =====
{template}
"""


def validate_prompt_plan(plan: dict, registry: dict) -> dict[str, dict]:
    if not isinstance(plan, dict) or not isinstance(plan.get("prompts"), list):
        raise ValueError("Stage 04 AI 输出缺少 prompts 列表。")
    expected = _expected_prompts(registry)
    actual = {}
    for item in plan["prompts"]:
        if not isinstance(item, dict):
            raise ValueError("Stage 04 提示词记录不是对象。")
        asset_id, version = item.get("asset_id"), item.get("version")
        if version not in expected or expected[version]["asset_id"] != asset_id:
            raise ValueError(f"发现未知资产或版本：{asset_id} {version}")
        if version in actual:
            raise ValueError(f"提示词重复：{version}")
        prompt = item.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip() or asset_id not in prompt:
            raise ValueError(f"提示词为空或没有引用资产 ID：{version}")
        if asset_id not in item.get("source_assets", []):
            raise ValueError(f"source_assets 没有引用资产：{version}")
        negative = item.get("negative")
        if not isinstance(negative, list) or not all(isinstance(x, str) for x in negative):
            raise ValueError(f"negative 字段无效：{version}")
        negative_text = " ".join(negative).casefold()
        if not all(term.casefold() in negative_text for term in ("字幕", "文字", "logo", "水印", "ui", "二维码", "乱码")):
            raise ValueError(f"提示词缺少基础禁止项：{version}")
        locked = expected[version]["asset"].get("locked_fields", [])
        if item.get("locked_fields") != locked:
            raise ValueError(f"锁定字段被改变：{version}")
        if version != f"{asset_id}-V01" and "保持" not in prompt:
            raise ValueError(f"状态版本没有声明保持基础资产：{version}")
        actual[version] = item
    missing = sorted(set(expected) - set(actual))
    if missing:
        raise ValueError("资产版本缺少提示词：" + "、".join(missing))
    return actual


def render_markdown(project_name: str, prompts: dict[str, dict], registry: dict) -> str:
    labels = {"CH": "人物", "LOC": "场景", "PROP": "道具", "WPN": "武器", "GRP": "群体", "FX": "特殊效果"}
    lines = ["# 资产生成提示词", "", f"项目：{project_name}", "", "说明：只引用 Stage 03 已锁定的资产 ID 和版本。", ""]
    for category in ASSET_CATEGORIES:
        lines += [f"## {category}｜{labels[category]}", ""]
        for asset_id, asset in registry["assets"][category].items():
            for version in asset["versions"]:
                version_id = version["version"]
                item = prompts[version_id]
                lines += [f"### {version_id}｜{asset['canonical_name']}", "", "【用途】", f"{labels[category]}资产生成", "", "【提示词】", item["prompt"], "", "【锁定项】", "、".join(item["locked_fields"]) or "待确认", "", "【允许变化】", "、".join(asset.get("mutable_fields", [])) or "待确认", "", "【强制禁止】", "、".join(item["negative"]), ""]
    lines += ["## 缺失或待确认信息", "", "无。所有 Stage 03 资产版本均已覆盖。"]
    return "\n".join(lines) + "\n"


def run_stage04(project_dir: Path, provider: AIProvider) -> str:
    project = json_read(project_dir / "project.json")
    original = next(project_dir.glob("00_原始剧本.*"))
    stage01, stage02 = project_dir / "01_剧本解析报告.md", project_dir / "02_项目专属规则.md"
    asset_markdown, registry_path = project_dir / "03_资产库.md", project_dir / "assets.json"
    if any("等待 AI 处理" in read_utf8(path) for path in (stage01, stage02, asset_markdown)):
        raise ValueError("Stage 04 需要先完成 Stage 01、Stage 02 和 Stage 03。")
    registry = json_read(registry_path)
    validate_registry(registry)
    before_assets = registry_path.read_bytes()
    rules = _read_sources(PROJECT_ROOT / "新版规则库", RULE_NAMES)
    template = _read_sources(PROJECT_ROOT / "15_模板库", TEMPLATE_NAMES)
    prompt = build_stage04_prompt(project["project_name"], read_utf8(original), read_utf8(stage01), read_utf8(stage02), read_utf8(asset_markdown), registry, rules, template)

    def operation() -> str:
        plan = json.loads(provider.complete(prompt, schema=PROMPT_SCHEMA))
        prompts = validate_prompt_plan(plan, registry)
        output = {"schema_version": "1.0", "project_id": project["project_id"], "project_name": project["project_name"], "prompts": prompts}
        markdown = render_markdown(project["project_name"], prompts, registry)
        if not markdown.startswith("# 资产生成提示词") or "## 缺失或待确认信息" not in markdown:
            raise ValueError("Stage 04 Markdown 输出无效。")
        atomic_json_write(project_dir / PROMPTS_NAME, output)
        if registry_path.read_bytes() != before_assets:
            raise ValueError("Stage 04 不得修改 assets.json。")
        return markdown

    runner = StageRunner(project_dir, 4, REPORT_NAME, "Stage 04 资产生成提示词")
    return runner.run(operation, lambda text: text.startswith("# 资产生成提示词") and "## 缺失或待确认信息" in text)
