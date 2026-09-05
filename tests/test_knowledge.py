"""
Unit tests for Knowledge Base and Semantic Vector Retrieval.
"""
from resolveiq.knowledge import knowledge_base


def test_articles_loaded():
    articles = knowledge_base.list_all_articles()
    assert len(articles) == 8, f"Expected 8 articles, found {len(articles)}"
    for art in articles:
        assert art["id"].startswith("KB-"), f"Invalid article ID {art['id']}"
        assert len(art.get("sections", [])) >= 2, f"Article {art['id']} missing sections"
        assert art.get("title"), f"Article {art['id']} missing title"


def test_semantic_search_outage():
    results = knowledge_base.search("broadband offline after outage was fixed", top_k=2)
    assert len(results) > 0
    top = results[0]
    assert top["article_id"] == "KB-NET-001"
    assert top["score"] > 0.1


def test_semantic_search_billing():
    results = knowledge_base.search("unexpected roaming charge on invoice from Switzerland", top_k=2)
    assert len(results) > 0
    top = results[0]
    assert top["article_id"] == "KB-BIL-003"


def test_semantic_search_cancellation():
    results = knowledge_base.search("contract termination cooling off early termination fee", top_k=2)
    assert len(results) > 0
    top = results[0]
    assert top["article_id"] == "KB-RET-008"
