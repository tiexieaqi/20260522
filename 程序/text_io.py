"""统一、拒绝静默损坏的剧本文本读取。"""
from __future__ import annotations
import hashlib
from pathlib import Path

SUPPORTED_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030")

def read_script_text(path: Path) -> dict:
    raw = path.read_bytes()
    if b"\xef\xbf\xbd" in raw:
        raise ValueError("script_text_corrupted: 剧本文件包含 U+FFFD 替换字符。")
    text = None; encoding = None
    for candidate in SUPPORTED_ENCODINGS:
        try:
            text = raw.decode(candidate); encoding = candidate; break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("script_encoding_error: 剧本文件存在无法可靠解码的字符，请转换为 UTF-8 或 GB18030 后重试。")
    bad = text.count("\ufffd") + text.count("\x00")
    controls = sum(1 for c in text if ord(c) < 32 and c not in "\n\r\t")
    if bad or controls:
        raise ValueError("script_text_corrupted: 剧本文件存在无法可靠解码的字符，请转换为 UTF-8 或 GB18030 后重试。")
    return {"text": text, "encoding": encoding, "sha256": hashlib.sha256(raw).hexdigest()}
