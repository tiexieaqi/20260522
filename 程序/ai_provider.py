"""统一 AI Provider 接口。当前只提供 Codex CLI 实现。"""

from abc import ABC, abstractmethod


class AIProviderError(RuntimeError):
    """AI Provider 调用失败。"""


class AIProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str, schema: dict | None = None) -> str:
        """接收提示词并返回模型的最终文本或结构化 JSON 文本。"""
        raise NotImplementedError
