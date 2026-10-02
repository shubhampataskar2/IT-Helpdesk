import json
import re

from openai import OpenAI

from app.ai.base import BaseAIProvider, TicketAnalysis
from app.ai.heuristic import CATEGORY_FIX, HeuristicProvider
from app.core.config import settings

SYSTEM_PROMPT = (
    "You are an IT helpdesk triage engine. Analyze the reported problem and reply with STRICT JSON "
    'matching this schema: {"category": "hardware|software|network|access|other", '
    '"priority": "low|medium|high|critical", "summary": "one or two sentence plain text summary", '
    '"suggested_fix": "concise plain text troubleshooting suggestion"}. '
    "Base priority on business impact and severity."
)


class OpenAIProvider(BaseAIProvider):
    kind = "openai"

    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key)
        self._fallback = HeuristicProvider()

    def classify(self, title: str, description: str) -> TicketAnalysis:
        text = f"{title}\n\n{description}"
        try:
            resp = self.client.chat.completions.create(
                model=settings.openai_model,
                temperature=0.1,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            return self._parse(data, title, description)
        except Exception:  # noqa: BLE001 - fall back to heuristics on any failure
            return self._fallback.classify(title, description)

    def embed(self, text: str) -> list[float]:
        try:
            resp = self.client.embeddings.create(
                model=settings.embedding_model,
                input=text[:8000],
            )
            return resp.data[0].embedding
        except Exception:  # noqa: BLE001
            return self._fallback.embed(text)

    def _parse(self, data: dict, title: str, description: str) -> TicketAnalysis:
        categories = ("hardware", "software", "network", "access", "other")
        priorities = ("low", "medium", "high", "critical")

        category = str(data.get("category", "")).lower().strip()
        if category not in categories:
            category = "other"
        priority = str(data.get("priority", "")).lower().strip()
        if priority not in priorities:
            priority = "medium"

        summary = str(data.get("summary", "")).strip()
        if not summary:
            summary = re.sub(r"\s+", " ", description.strip())[:200]

        fix = str(data.get("suggested_fix", "")).strip()
        if not fix:
            fix = CATEGORY_FIX.get(category, CATEGORY_FIX["other"])

        return TicketAnalysis(
            category=category,
            priority=priority,
            summary=summary,
            suggested_fix=fix,
            confidence=0.95,
        )
