from app.ai.base import BaseAIProvider
from app.ai.heuristic import HeuristicProvider
from app.core.config import settings

_provider: BaseAIProvider | None = None


def get_ai_provider() -> BaseAIProvider:
    global _provider
    if _provider is None:
        if settings.ai_provider == "openai" and settings.openai_api_key:
            from app.ai.openai_provider import OpenAIProvider

            _provider = OpenAIProvider()
        else:
            _provider = HeuristicProvider()
    return _provider
