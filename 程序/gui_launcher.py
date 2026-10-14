"""可靠启动 GUI：为 pythonw 提供异常日志和可读错误提示。"""
from __future__ import annotations

import os
import runpy
import sys
import traceback
from datetime import datetime
from pathlib import Path


_env_root = os.environ.get("AI_FILM_ROOT")
if _env_root:
    PROJECT_ROOT = Path(_env_root)
    PROGRAM_DIR = PROJECT_ROOT / "程序"
else:
    _cwd = Path.cwd()
    PROGRAM_DIR = _cwd if (_cwd / "gui_app.py").is_file() else Path(__file__).resolve().parent
    PROJECT_ROOT = PROGRAM_DIR.parent
LOG_DIR = PROJECT_ROOT / "logs"
ERROR_LOG = LOG_DIR / "gui_startup_error.log"
DEBUG_LOG = LOG_DIR / "gui_launcher_debug.log"


def _debug(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with DEBUG_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"[{datetime.now().isoformat(timespec='seconds')}] {message}\n")


def _write_error(error: BaseException) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    text = (
        f"[{datetime.now().isoformat(timespec='seconds')}] GUI 启动失败\n"
        f"项目根目录：{PROJECT_ROOT}\n"
        f"Python：{sys.executable}\n"
        f"工作目录：{Path.cwd()}\n\n"
        + "".join(traceback.format_exception(type(error), error, error.__traceback__))
    )
    ERROR_LOG.write_text(text, encoding="utf-8")


def main() -> None:
    _debug(f"launcher_enter pid={os.getpid()} python={sys.executable} file={__file__} cwd={Path.cwd()}")
    os.chdir(PROJECT_ROOT)
    sys.path.insert(0, str(PROGRAM_DIR))
    _debug(f"launcher_ready root={PROJECT_ROOT} cwd={Path.cwd()} target={PROGRAM_DIR / 'gui_app.py'}")
    runpy.run_path(str(PROGRAM_DIR / "gui_app.py"), run_name="__main__")


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        _debug(f"launcher_exception type={type(error).__name__} error={error!r}")
        _write_error(error)
        try:
            import tkinter.messagebox as messagebox

            messagebox.showerror(
                "AI影视助手启动失败",
                f"GUI 启动失败，详细错误已保存到：\n{ERROR_LOG}\n\n{error}",
            )
        except Exception:
            pass
        raise
