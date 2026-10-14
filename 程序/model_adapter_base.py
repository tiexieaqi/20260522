"""模型适配器的最小公共接口，供 Stage 06—09 复用。"""

from abc import ABC, abstractmethod


class ModelAdapter(ABC):
    model_name = ""

    @abstractmethod
    def build_prompt(self, shot: dict, context: dict) -> str:
        """将一个模型无关镜头转换为模型提示词。"""

    @abstractmethod
    def assess_risk(self, shot: dict) -> tuple[str, list[str]]:
        """返回模型风险等级和原因。"""
