from app.ai.heuristic import HeuristicProvider


def test_classify_hardware():
    result = HeuristicProvider().classify("Monitor flickering", "My external monitor keeps flickering and turning off")
    assert result.category == "hardware"
    assert result.priority in ("low", "medium", "high", "critical")
    assert result.summary
    assert result.suggested_fix


def test_classify_network_critical():
    result = HeuristicProvider().classify(
        "VPN down", "The VPN is completely down and no one can connect to the internal network - emergency"
    )
    assert result.category == "network"
    assert result.priority in ("high", "critical")
    assert result.confidence > 0.5


def test_classify_access():
    result = HeuristicProvider().classify(
        "Password reset", "I cannot log in, my password is not working and MFA code no longer accepted"
    )
    assert result.category == "access"


def test_classify_unknown_category():
    result = HeuristicProvider().classify("Random", "Just a general question about office snacks and coffee machines")
    assert result.category in ("hardware", "software", "network", "access", "other")


def test_embed_is_deterministic_and_normalized():
    from app.core.config import settings

    provider = HeuristicProvider()
    vec1 = provider.embed("laptop battery drains fast")
    vec2 = provider.embed("laptop battery drains fast")
    assert vec1 == vec2
    norm = sum(x * x for x in vec1) ** 0.5
    assert abs(norm - 1.0) < 1e-6
    assert len(vec1) == settings.embedding_dim


def test_similarity_semantics():
    provider = HeuristicProvider()
    same = provider.cosine_similarity(
        provider.embed("printer offline cannot print"),
        provider.embed("printer offline cannot print"),
    )
    diff = provider.cosine_similarity(
        provider.embed("printer offline cannot print"),
        provider.embed("rainbow unicorns and machine learning"),
    )
    assert same > 0.9
    assert diff < same
