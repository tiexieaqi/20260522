"""ASCII/Junction entry point for the AI影视助手 GUI."""
from __future__ import annotations

import runpy
import sys
import traceback
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
PROGRAM_DIR = PROJECT_ROOT / "程序"
LOG_DIR = PROJECT_ROOT / "logs"
ERROR_LOG = LOG_DIR / "launcher_error.log"


def main() -> None:
    sys.path.insert(0, str(PROGRAM_DIR))
    runpy.run_path(str(PROGRAM_DIR / "gui_v2_app.py"), run_name="__main__")


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        ERROR_LOG.write_text(
            f"[{datetime.now().isoformat(timespec='seconds')}] GUI 启动失败\n"
            f"Python: {sys.executable}\n"
            f"项目入口: {PROJECT_ROOT}\n"
            f"目标程序: {PROGRAM_DIR / 'gui_app.py'}\n\n"
            + "".join(traceback.format_exception(type(error), error, error.__traceback__)),
            encoding="utf-8",
        )
        raise
