"""通用阶段执行器：状态、输出验证、失败日志和不覆盖保护。"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from file_utils import atomic_text_write, ensure_directory, json_read, json_write, write_utf8


class StageRunner:
    def __init__(self, project_dir: Path, stage_number: int, output_name: str, stage_name: str):
        self.project_dir = project_dir
        self.stage_number = str(stage_number)
        self.output_path = project_dir / output_name
        self.stage_name = stage_name

    def _state(self, status: str, message: str) -> None:
        path = self.project_dir / "workflow_state.json"
        state = json_read(path)
        state["stages"][self.stage_number]["status"] = status
        state["stages"][self.stage_number]["message"] = message
        state["stages"][self.stage_number]["updated_at"] = datetime.now(timezone.utc).isoformat()
        state["current_stage"] = int(self.stage_number)
        state["project_status"] = "processing" if status == "processing" else status
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        json_write(path, state)

    def run(self, operation: Callable[[], str], validator: Callable[[str], None]) -> str:
        self._state("processing", f"正在处理 {self.stage_name}")
        try:
            result = operation()
            validator(result)
            atomic_text_write(self.output_path, result.rstrip() + "\n")
            self._state("completed", f"{self.stage_name}已完成")
            return result
        except Exception as error:
            self._state("failed", str(error))
            log_dir = ensure_directory(self.project_dir / "logs")
            write_utf8(
                log_dir / f"stage{int(self.stage_number):02d}_error.log",
                f"{datetime.now(timezone.utc).isoformat()}\n{type(error).__name__}: {error}\n",
            )
            raise
