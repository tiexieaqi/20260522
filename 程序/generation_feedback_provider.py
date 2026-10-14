"""真实生成反馈的可插拔接口；当前不连接任何平台。"""

from abc import ABC, abstractmethod


class GenerationFeedbackProvider(ABC):
    @abstractmethod
    def record(self, project_id: str, feedback: dict) -> None:
        pass


class OfflineGenerationFeedbackProvider(GenerationFeedbackProvider):
    def record(self, project_id: str, feedback: dict) -> None:
        return None
