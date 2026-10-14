"""文件读写和路径辅助函数。"""

import re
from pathlib import Path


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_utf8(path: Path, content: str) -> None:
    ensure_directory(path.parent)
    path.write_text(content, encoding="utf-8", newline="\n")


def read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def safe_project_name(name: str) -> str:
    """将文件名转换成适合 Windows 和其他系统的目录名。"""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip().rstrip(".")
    return cleaned or "未命名项目"


def json_write(path: Path, data: dict) -> None:
    import json

    ensure_directory(path.parent)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def json_read(path: Path) -> dict:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json_write(path: Path, data: dict) -> None:
    """以临时文件加原子替换方式写入 JSON。"""
    import json
    import os
    import tempfile

    ensure_directory(path.parent)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def atomic_text_write(path: Path, content: str) -> None:
    """以临时文件加原子替换方式写入 UTF-8 文本。"""
    import os
    import tempfile

    ensure_directory(path.parent)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
