"""通过官方 Codex CLI 的 `codex exec` 调用 ChatGPT 登录态。"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from ai_provider import AIProvider, AIProviderError


RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["report_markdown"],
    "properties": {
        "report_markdown": {"type": "string"},
    },
}


class CodexProvider(AIProvider):
    def __init__(self, timeout_seconds: int = 15, executable: str = "codex") -> None:
        self.timeout_seconds = timeout_seconds
        self.executable = executable

    @staticmethod
    def is_available(executable: str = "codex") -> bool:
        return shutil.which(executable) is not None

    def complete(self, prompt: str, schema: dict | None = None) -> str:
        with tempfile.TemporaryDirectory(prefix="ai影视助手_codex_") as temp_dir:
            temp_path = Path(temp_dir)
            schema_path = temp_path / "response_schema.json"
            output_path = temp_path / "last_message.json"
            active_schema = schema or RESPONSE_SCHEMA
            schema_path.write_text(
                json.dumps(active_schema, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            command = [
                self.executable,
                "exec",
                "--skip-git-repo-check",
                "--ephemeral",
                "--sandbox",
                "read-only",
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(output_path),
                "-",
            ]
            try:
                result = subprocess.run(
                    command,
                    input=prompt,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    capture_output=True,
                    timeout=self.timeout_seconds,
                    shell=False,
                )
            except FileNotFoundError as error:
                raise AIProviderError("找不到 codex 命令。请确认 Codex CLI 已安装。") from error
            except subprocess.TimeoutExpired as error:
                raise AIProviderError(
                    f"Codex CLI 调用超时（超过 {self.timeout_seconds} 秒）。"
                ) from error
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "没有返回错误详情").strip()
                if "403" in detail or "dns" in detail.lower() or "connect" in detail.lower():
                    detail = "网络无法连接 ChatGPT/Codex 服务（当前环境可能受限）；" + detail
                raise AIProviderError(
                    f"Codex CLI 退出码为 {result.returncode}：{detail[-2000:]}"
                )
            if not output_path.is_file():
                raise AIProviderError("Codex CLI 没有生成最终输出文件。")
            raw = output_path.read_text(encoding="utf-8", errors="replace").strip()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as error:
                raise AIProviderError("Codex CLI 返回内容不是合法 JSON。") from error
            if schema is not None:
                return raw
            report = data.get("report_markdown") if isinstance(data, dict) else None
            if not isinstance(report, str) or not report.strip():
                raise AIProviderError("Codex CLI 返回 JSON 缺少 report_markdown。")
            return report.strip()
