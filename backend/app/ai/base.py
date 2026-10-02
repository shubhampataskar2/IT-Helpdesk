from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TicketAnalysis:
    category: str
    priority: str
    summary: str
    suggested_fix: str
    confidence: float


class BaseAIProvider(ABC):
    @property
    @abstractmethod
    def kind(self) -> str:
        """Identifier: 'openai' or 'heuristic'."""

    @abstractmethod
    def classify(self, title: str, description: str) -> TicketAnalysis:
        """Return category, priority, summary and suggested fix for a ticket."""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Return an embedding vector for free-text."""

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)
