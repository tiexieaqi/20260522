"""运行环境检测：区分可联网本机和受限开发沙盒。"""

import os
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class EnvironmentStatus:
    python_available: bool
    codex_available: bool
    logged_in: bool
    restricted_network: bool
    reason: str


def check_codex_cli(executable: str = "codex") -> tuple[bool, str]:
    path = shutil.which(executable)
    if not path:
        return False, "找不到 codex CLI。"
    try:
        result = subprocess.run([executable, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10, shell=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, f"codex CLI 检测失败：{error}"
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "codex CLI 返回失败").strip()
    return True, (result.stdout or "已找到 codex CLI").strip()


def check_codex_login(executable: str = "codex") -> tuple[bool, str]:
    try:
        result = subprocess.run([executable, "login", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15, shell=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, f"登录状态检测失败：{error}"
    text = (result.stdout or result.stderr or "").strip()
    logged_in = result.returncode == 0 and "logged in" in text.lower()
    return logged_in, text or "未获得登录状态"


def detect_restricted_environment() -> tuple[bool, str]:
    markers = []
    if os.environ.get("CODEX_ENVIRONMENT_ID"):
        markers.append("CODEX_ENVIRONMENT_ID")
    if os.environ.get("CODEX_SANDBOX"):
        markers.append("CODEX_SANDBOX")
    if os.path.isdir("/run/codex-environment"):
        markers.append("/run/codex-environment")
    if markers:
        return True, "检测到开发沙盒标记：" + ", ".join(markers)
    return False, "未检测到已知沙盒标记；是否能联网需以实际调用为准。"


def inspect_environment(executable: str = "codex") -> EnvironmentStatus:
    cli_ok, cli_message = check_codex_cli(executable)
    login_ok, login_message = check_codex_login(executable) if cli_ok else (False, "未执行登录检测")
    restricted, reason = detect_restricted_environment()
    return EnvironmentStatus(True, cli_ok, login_ok, restricted, f"{reason}；CLI：{cli_message}；登录：{login_message}")
