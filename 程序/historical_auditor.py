"""证据保守的历史真实性审核逻辑。"""

import re

from historical_schema import empty_historical_report


def historical_relevance(text: str) -> str:
    if not text.strip(): return "none"
    if re.search(r"(现代|当代|202[0-9]|手机|互联网)", text) and not re.search(r"(抗战|战争|战役|年代|历史|民国|红军|部队)", text): return "none"
    if re.search(r"(真实历史人物|真实战役|真实事件|历史人物|战役|战斗|193[0-9]|194[0-9]|民国|抗战|红军|解放战争)", text): return "high"
    if re.search(r"(年代|旧时代|历史背景|部队|军队)", text): return "medium"
    return "low"


def _category(claim: str) -> str:
    mapping = [("WEAPON", "武器|步枪|枪|炮|弹药|型号"), ("COSTUME", "服装|军装|帽|鞋|徽章|领章"), ("ARCHITECTURE", "建筑|桥|房屋|战壕|门窗"), ("LANGUAGE", "称谓|同志|长官|原话|台词|词"), ("DATE", r"\d{4}年|日期|月|日"), ("LOCATION", "地点|河|山|桥|城市|道路"), ("MILITARY", "番号|连|排|班|营|团|军|纵队|编制"), ("PERSON", "人物|某人|将军|战士"), ("PROP", "道具|信件|饭盒|水壶|粮袋")]
    for name, pattern in mapping:
        if re.search(pattern, claim): return name
    return "OTHER"


def extract_claims(script: str, project_rules: str, assets_md: str, storyboard: dict) -> list[dict]:
    lines = [line.strip() for line in script.splitlines() if line.strip()]
    explicit = [line.split("HIST:", 1)[1].strip() for line in lines if "HIST:" in line]
    if not explicit:
        explicit = [line for line in lines if re.search(r"(19\d{2}|历史|战役|军队|武器|军装|桥)", line)][:8]
    claims = []
    shot_ids = [shot["shot_id"] for scene in storyboard["scenes"] for shot in scene["shots"]]
    for index, claim_text in enumerate(explicit, 1):
        claims.append({"claim_id": f"HIST-{index:03d}", "claim": claim_text, "category": _category(claim_text), "era": (re.search(r"(?:18|19|20)\d{2}", claim_text).group(0) if re.search(r"(?:18|19|20)\d{2}", claim_text) else "待确认"), "date_if_known": "待确认", "location_if_known": "待确认", "related_assets": [], "related_shots": shot_ids[:1], "source_origin": "原始剧本（explicit）"})
    weapon_mentions = re.findall(r"(?:莫辛纳甘|中正式|三八式|步枪|机枪)[A-Za-z0-9一二三四五六七八九十-]*", assets_md)
    for mention in weapon_mentions:
        if not any(mention in claim["claim"] for claim in claims):
            claims.append({"claim_id": f"HIST-{len(claims)+1:03d}", "claim": mention, "category": "WEAPON", "era": "待确认", "date_if_known": "待确认", "location_if_known": "待确认", "related_assets": [], "related_shots": [], "source_origin": "资产库（inferred）"})
    if not claims and historical_relevance(script) != "none":
        claims.append({"claim_id": "HIST-001", "claim": "项目包含历史时代或历史题材设定，需核验具体史实。", "category": "OTHER", "era": "待确认", "date_if_known": "待确认", "location_if_known": "待确认", "related_assets": [], "related_shots": shot_ids[:1], "source_origin": "原始剧本（inferred）"})
    return claims


def audit_historical(project: dict, script: str, project_rules: str, assets_md: str, storyboard: dict, source_provider) -> dict:
    report = empty_historical_report(project)
    # 以原始剧本为主，避免规则模板中的“历史真实性”章节标题把现代项目误判为历史题材。
    relevance = historical_relevance(script)
    report["historical_relevance"] = relevance
    if relevance == "none":
        report["historical_gate"] = "not_applicable"
        return report
    claims = extract_claims(script, project_rules, assets_md, storyboard)
    report["claims"] = claims
    for claim in claims:
        dramatized = any(term in claim["claim"] for term in ("虚构", "合成人物", "艺术加工", "影视化对白", "压缩时间"))
        result = {"status": "dramatized", "sources": [], "conflicting_sources": []} if dramatized else source_provider.verify_claim(claim["claim"], {"project": project["project_name"], "claim": claim})
        sources = result.get("sources", [])
        for source in sources:
            if source.get("mock"): source["source_type"] = source.get("source_type", "unknown")
            report["sources"].append(source)
        status = result.get("status", "unverified")
        severity = "critical" if status == "contradicted" else "error" if status == "disputed" else "warning" if status in {"unverified", "plausible"} else "info"
        issue = {"issue_id": f"HIST-{len(report['issues'])+1:03d}", "category": claim["category"], "severity": severity, "verification_status": status, "claim": claim["claim"], "era": claim["era"], "related_shots": claim["related_shots"], "related_assets": claim["related_assets"], "evidence": "；".join(source.get("title", "") for source in sources) or "无可用史料来源", "evidence_level": min((source.get("evidence_level", "E") for source in sources), default="E"), "source_refs": [source["source_id"] for source in sources], "conflicting_sources": [source["source_id"] for source in result.get("conflicting_sources", [])], "historical_expected": "需要可靠史料支持后确认", "project_current": claim["claim"], "dramatization_type": "", "production_deviation": False, "suggested_fix_stage": "Stage 01 / 02" if claim["category"] in {"PERSON", "EVENT", "DATE", "LANGUAGE"} else "Stage 03" if claim["category"] in {"WEAPON", "COSTUME", "PROP", "ARCHITECTURE"} else "Stage 05", "suggested_fix": "补充可靠史料或标注艺术加工；不要伪造来源。", "requires_external_verification": status in {"unverified", "plausible", "disputed"}}
        report["issues"].append(issue)
        if status == "dramatized":
            report["dramatizations"].append({"claim_id": claim["claim_id"], "dramatization_type": "invented_dialogue" if "对白" in claim["claim"] else "composite_character" if "人物" in claim["claim"] else "compressed_timeline", "severity": "acceptable"})
        if issue["requires_external_verification"]: report["requires_external_verification"].append(claim["claim_id"])
    if "禁止logo" in project_rules or "禁止文字" in project_rules or "禁止徽章" in project_rules:
        report["production_deviations"].append({"type": "production_constraint", "description": "项目为生成稳定性设置了文字、logo或标志限制，不直接判为史实错误。", "source": "项目专属规则"})
    report["historical_gate"] = "blocked" if any(i["severity"] == "critical" for i in report["issues"]) else "review_required" if any(i["severity"] == "error" for i in report["issues"]) else "passed"
    deduction = sum(20 if i["severity"] == "critical" else 12 if i["severity"] == "error" else 4 if i["severity"] == "warning" else 0 for i in report["issues"])
    report["historical_score"] = max(0, 100 - deduction)
    return report
