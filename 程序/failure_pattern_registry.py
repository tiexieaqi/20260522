"""通用 AI 视频生成失败模式，不绑定具体项目。"""

FAILURE_PATTERNS = {
    "F001": {"name": "枪械状态误生成", "risk_type": "PHYSICS_STATE_CONFLICT"},
    "F002": {"name": "角色串台词", "risk_type": "DIALOGUE_SPEAKER_SWAP"},
    "F003": {"name": "人物双武器", "risk_type": "WEAPON_DUPLICATION_RISK"},
    "F004": {"name": "群体复制", "risk_type": "GROUP_CLONE_RISK"},
    "F005": {"name": "机械移动", "risk_type": "MECHANICAL_MOVEMENT_RISK"},
    "F006": {"name": "字幕乱码", "risk_type": "TEXT_ARTIFACT_RISK"},
}
