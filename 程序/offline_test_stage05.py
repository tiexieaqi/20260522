"""Stage 05 离线测试：标准分镜、对白、连续性、模型无关和失败保护。"""

import json
import sys
import tempfile
from pathlib import Path

PROGRAM_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROGRAM_DIR))

from offline_test_stage04 import AssetProvider, PromptProvider, TextProvider
from project_manager import create_project
from stage01_manager import REQUIRED_HEADINGS as H1, run_stage01
from stage02_manager import REQUIRED_HEADINGS as H2, run_stage02
from stage03_manager import run_stage03
from stage04_manager import run_stage04
from stage05_manager import run_stage05


def prepare(root: Path) -> Path:
    source = root / "战争测试.txt"
    source.write_text("1935年雨夜，通信员林川在山间驿站传递信件，敌军搜山。", encoding="utf-8")
    project = create_project(source, projects_dir=root / "projects", input_func=lambda _: "1")
    run_stage01(project, TextProvider(H1))
    run_stage02(project, TextProvider(H2))
    run_stage03(project, AssetProvider())
    run_stage04(project, PromptProvider())
    return project


def _dialogue(speaker: str, text: str, seconds: float, kind: str = "character_dialogue") -> dict:
    return {
        "speaker": speaker,
        "speaker_asset_id": speaker if kind == "character_dialogue" else None,
        "dialogue": text,
        "dialogue_type": kind,
        "estimated_duration": seconds,
        "lip_sync_required": kind == "character_dialogue",
        "emotion": "克制而疲惫",
        "pause_before": 0.3,
        "pause_after": 0.5,
    }


def make_storyboard(project_id: str, invalid: bool = False) -> dict:
    if invalid:
        return {"schema_version": "1.0", "project_id": project_id, "project_name": "战争测试", "total_duration_seconds": 4, "duration_warning": False, "continuity_timeline": [], "scenes": [{"scene_id": "S01", "shots": [{"shot_id": "S01_SH01", "duration_seconds": 4, "assets": {"characters": ["CH-999-V01"], "location": "LOC-001-V01", "props": [], "weapons": [], "groups": [], "fx": []}, "camera": {"shot_size": "medium", "focal_length": "50mm", "movement": "locked"}, "blocking": {}, "action": [], "dialogue": [], "performance_direction": [], "movement_style": "natural_realistic", "start_state": {}, "end_state": {}, "action_complexity": "low", "continuity_notes": [], "forbidden": ["禁止字幕", "禁止logo", "禁止水印"]}]}]}

    common = {"characters": ["CH-001-V01"], "location": "LOC-001-V01", "props": ["PROP-001-V01"], "weapons": [], "groups": [], "fx": []}
    shots = [
        {"shot_id": "S01_SH01", "duration_seconds": 7, "story_goal": "传递信息并建立人物关系", "assets": common, "camera": {"shot_size": "medium", "focal_length": "50mm", "height": "视线高度", "angle": "平视", "position": "驿站门内", "movement": "locked"}, "blocking": {"CH-001": "画面左前，靠近桌边"}, "action": ["林川取出信件并停顿"], "dialogue": [_dialogue("CH-001", "班长，信到了。", 4.5)], "performance_direction": ["先看信，再抬眼确认对方反应"], "movement_style": "natural_realistic", "start_state": {"time": "雨夜", "position": "门边", "compatible_with_previous": True}, "end_state": {"time": "雨夜", "position": "桌边", "prop_state": "PROP-001-V01"}, "action_complexity": "low", "continuity_notes": ["保持右手持信"], "forbidden": ["禁止字幕", "禁止文字", "禁止logo", "禁止水印", "禁止乱码"]},
        {"shot_id": "S01_SH02", "duration_seconds": 6, "story_goal": "回应并加入后期旁白", "assets": {"characters": ["CH-001-V01", "CH-002-V01"], "location": "LOC-001-V01", "props": ["PROP-001-V01"], "weapons": [], "groups": [], "fx": []}, "camera": {"shot_size": "medium_close", "focal_length": "85mm", "height": "视线高度", "angle": "平视", "position": "桌边右侧", "movement": "slow_push"}, "blocking": {"CH-001": "画面左侧", "CH-002": "画面右侧"}, "action": ["赵伯接过信件并低头查看"], "dialogue": [_dialogue("CH-002", "先把门关上。", 3.5), _dialogue("旁白", "雨声掩住了远处的脚步。", 3.0, "voiceover")], "performance_direction": ["赵伯压低声音，林川回望门外"], "movement_style": "natural_realistic", "start_state": {"position": "桌边", "prop_state": "PROP-001-V01", "compatible_with_previous": True}, "end_state": {"position": "桌边", "prop_state": "PROP-001-V01", "time": "雨夜"}, "action_complexity": "medium", "continuity_notes": ["旁白不触发人物口型"], "forbidden": ["禁止字幕", "禁止文字", "禁止logo", "禁止水印", "禁止乱码"]},
        {"shot_id": "S02_SH01", "duration_seconds": 9, "story_goal": "敌军逼近，人物尝试操作冻住的步枪", "assets": {"characters": ["CH-001-V02"], "location": "LOC-001-V02", "props": ["PROP-001-V02"], "weapons": ["WPN-001-V01"], "groups": ["GRP-001-V01"], "fx": ["FX-001-V01"]}, "camera": {"shot_size": "medium_wide", "focal_length": "35mm", "height": "胸口高度", "angle": "低角度", "position": "山路掩体前", "movement": "tracking"}, "blocking": {"CH-001": "前景右侧", "GRP-001": "背景山路"}, "action": ["林川压低身体", "尝试拉动枪栓但枪栓完全没有移动"], "dialogue": [], "performance_direction": ["呼吸急促，肩膀因寒冷发抖"], "movement_style": "natural_realistic", "start_state": {"time": "雪夜", "position": "冻土后", "prop_state": "PROP-001-V02", "compatible_with_previous": True}, "end_state": {"time": "雪夜", "position": "掩体后", "weapon_state": "枪栓冻结", "injury": "轻微擦伤"}, "action_complexity": "high", "continuity_notes": ["枪栓冻结状态不可成功拉动", "空间结构保持不变"], "forbidden": ["禁止字幕", "禁止文字", "禁止logo", "禁止水印", "禁止乱码"]},
        {"shot_id": "S03_SH01", "duration_seconds": 4, "story_goal": "闪回中的信件记忆", "assets": {"characters": ["CH-001-V01"], "location": "LOC-001-V01", "props": ["PROP-001-V01"], "weapons": [], "groups": [], "fx": []}, "camera": {"shot_size": "close", "focal_length": "85mm", "height": "视线高度", "angle": "平视", "position": "回忆中的桌面", "movement": "slow_pull"}, "blocking": {"CH-001": "画面中央"}, "action": ["林川凝视信件"], "dialogue": [_dialogue("旁白", "那是他最后一次收到家书。", 3.0, "voiceover")], "performance_direction": ["眼神停留，画面人物保持闭口"], "movement_style": "natural_realistic", "start_state": {"time": "回忆", "compatible_with_previous": True}, "end_state": {"time": "回忆", "position": "桌边"}, "action_complexity": "low", "continuity_notes": ["这是明确闪回，允许版本回到 V01"], "forbidden": ["禁止字幕", "禁止文字", "禁止logo", "禁止水印", "禁止乱码"], "is_flashback": True},
    ]
    total = sum(item["duration_seconds"] for item in shots)
    timeline = [{"shot_id": item["shot_id"], "end_state": item["end_state"]} for item in shots]
    return {"schema_version": "1.0", "project_id": project_id, "project_name": "战争测试", "total_duration_seconds": total, "duration_warning": False, "continuity_timeline": timeline, "scenes": [{"scene_id": "S01", "story_function": "驿站传信", "shots": shots[:2]}, {"scene_id": "S02", "story_function": "雪夜追捕", "shots": [shots[2]]}, {"scene_id": "S03", "story_function": "回忆", "shots": [shots[3]]}]}


class StoryboardProvider:
    def __init__(self, invalid=False): self.invalid = invalid
    def complete(self, prompt, schema=None):
        project_id = prompt.split("项目 ID：", 1)[1].split("\n", 1)[0].strip()
        return json.dumps(make_storyboard(project_id, self.invalid), ensure_ascii=False)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ai影视助手_stage05_") as temp:
        root = Path(temp)
        project = prepare(root)
        before_inputs = {name: (project / name).read_bytes() for name in ("01_剧本解析报告.md", "02_项目专属规则.md", "03_资产库.md", "04_资产生成提示词.md", "assets.json", "asset_prompts.json")}
        run_stage05(project, StoryboardProvider())
        storyboard_bytes = (project / "storyboard.json").read_bytes()
        storyboard = json.loads(storyboard_bytes.decode("utf-8"))
        assert len(storyboard["scenes"]) == 3 and storyboard["total_duration_seconds"] == 26
        assert (project / "05_标准分镜.md").read_text(encoding="utf-8").startswith("# 标准分镜")
        assert storyboard["scenes"][0]["shots"][0]["dialogue"][0]["speaker_asset_id"] == "CH-001"
        assert storyboard["scenes"][0]["shots"][1]["dialogue"][1]["lip_sync_required"] is False
        assert storyboard["scenes"][1]["shots"][0]["action_complexity"] == "high"
        assert storyboard["scenes"][3 - 1]["shots"][0]["is_flashback"] is True
        assert all((project / name).read_bytes() == value for name, value in before_inputs.items())
        run_stage05(project, StoryboardProvider())
        assert storyboard_bytes == (project / "storyboard.json").read_bytes()
        report_before = (project / "05_标准分镜.md").read_bytes()
        try: run_stage05(project, StoryboardProvider(invalid=True))
        except Exception: pass
        else: raise AssertionError("非法标准分镜没有失败")
        assert report_before == (project / "05_标准分镜.md").read_bytes()
        assert storyboard_bytes == (project / "storyboard.json").read_bytes()
        state = json.loads((project / "workflow_state.json").read_text(encoding="utf-8"))
        assert state["stages"]["5"]["status"] == "failed"
        assert all((project / name).read_bytes() == value for name, value in before_inputs.items())
    print("offline_test_stage05：全部通过")
    return 0


if __name__ == "__main__": raise SystemExit(main())
