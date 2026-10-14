"""史料来源接口。默认实现永远不联网、不伪造来源。"""

from abc import ABC, abstractmethod


class HistoricalSourceProvider(ABC):
    @abstractmethod
    def search(self, claim: str, context: dict) -> list[dict]:
        """返回带 source_id/source_type/evidence_level 的来源，无法查询时返回空列表。"""

    def verify_claim(self, claim: str, context: dict) -> dict:
        sources = self.search(claim, context)
        if not sources:
            return {"status": "unverified", "sources": [], "conflicting_sources": []}
        statuses = {item.get("status", "unverified") for item in sources}
        if len(statuses) > 1 or "disputed" in statuses:
            return {"status": "disputed", "sources": sources, "conflicting_sources": sources}
        return {"status": next(iter(statuses)), "sources": sources, "conflicting_sources": []}


class UnavailableHistoricalSourceProvider(HistoricalSourceProvider):
    def search(self, claim: str, context: dict) -> list[dict]:
        return []
