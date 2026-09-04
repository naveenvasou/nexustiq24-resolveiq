"""
Knowledge base management, embedding generation, and semantic retrieval for ResolveIQ.
Uses google-genai (gemini-embedding-001) with numpy vector search and local caching.
"""
import json
import math
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from resolveiq.config import ARTICLES_DIR, EMBEDDINGS_CACHE_PATH, settings


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric tokens."""
    return re.findall(r"\b[a-zA-Z0-9_\-\$]+\b", text.lower())


def compute_bm25_features(articles: List[Dict[str, Any]], vocabulary: List[str]) -> np.ndarray:
    """Compute normalized BM25/TF-IDF feature vectors for offline fallback."""
    N = len(articles)
    df = {term: 0 for term in vocabulary}
    doc_tokens_list = []

    for art in articles:
        tokens = tokenize(art["searchable_text"])
        doc_tokens_list.append(tokens)
        unique_tokens = set(tokens)
        for t in unique_tokens:
            if t in df:
                df[t] += 1

    idf = {term: math.log((N - df[term] + 0.5) / (df[term] + 0.5) + 1.0) for term in vocabulary}
    avgdl = sum(len(toks) for toks in doc_tokens_list) / max(N, 1)

    k1 = 1.5
    b = 0.75
    matrix = np.zeros((N, len(vocabulary)), dtype=np.float32)

    for i, tokens in enumerate(doc_tokens_list):
        doc_len = len(tokens)
        tf = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        for j, term in enumerate(vocabulary):
            freq = tf.get(term, 0)
            if freq > 0:
                score = idf[term] * (freq * (k1 + 1.0)) / (freq + k1 * (1.0 - b + b * (doc_len / avgdl)))
                matrix[i, j] = score

    # Normalize vectors
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class KnowledgeBase:
    """Knowledge base holding support articles with vector search capabilities."""

    def __init__(self, articles_dir: Path = ARTICLES_DIR, cache_path: Path = EMBEDDINGS_CACHE_PATH):
        self.articles_dir = articles_dir
        self.cache_path = cache_path
        self.articles: Dict[str, Dict[str, Any]] = {}
        self.article_list: List[Dict[str, Any]] = []
        self.article_ids: List[str] = []
        self.vectors: Optional[np.ndarray] = None
        self.vocabulary: List[str] = []
        self.embedding_dimension: int = 768
        self._genai_client = None

        self.load_articles()
        self.init_embeddings()

    def _get_client(self):
        """Lazy initialization of google-genai Client."""
        if self._genai_client is None:
            api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
            if api_key:
                try:
                    from google import genai
                    self._genai_client = genai.Client(api_key=api_key)
                except Exception as e:
                    print(f"Warning: Failed to initialize genai Client: {e}")
        return self._genai_client

    def load_articles(self) -> None:
        """Load all support articles from data/articles/."""
        self.articles.clear()
        self.article_list.clear()

        if not self.articles_dir.exists():
            return

        for filepath in sorted(self.articles_dir.glob("*.json")):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    art_id = data.get("id")
                    if art_id:
                        # Build searchable composite text
                        sec_texts = " ".join([f"{s.get('heading', '')}: {s.get('text', '')}" for s in data.get("sections", [])])
                        keywords = " ".join(data.get("keywords", []))
                        searchable = f"{data.get('title', '')} {data.get('summary', '')} {keywords} {sec_texts}"
                        data["searchable_text"] = searchable
                        self.articles[art_id] = data
                        self.article_list.append(data)
            except Exception as e:
                print(f"Error loading article {filepath}: {e}")

        self.article_ids = [a["id"] for a in self.article_list]

    def init_embeddings(self) -> None:
        """Load precomputed embeddings from cache or initialize indexing."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    self.article_ids = cache_data.get("article_ids", self.article_ids)
                    self.vocabulary = cache_data.get("vocabulary", [])
                    raw_vecs = cache_data.get("vectors", [])
                    if raw_vecs:
                        self.vectors = np.array(raw_vecs, dtype=np.float32)
                        return
            except Exception as e:
                print(f"Failed loading embeddings cache: {e}. Recomputing...")

        # Build vocabulary from articles for feature index
        all_words = set()
        for art in self.article_list:
            all_words.update(tokenize(art["searchable_text"]))
        self.vocabulary = sorted(list(all_words))

        # Check if live Gemini embedding is possible, otherwise use deterministic semantic feature matrix
        client = self._get_client()
        if client:
            try:
                live_vecs = []
                for art in self.article_list:
                    res = client.models.embed_content(
                        model=settings.embedding_model,
                        contents=art["searchable_text"][:2000]
                    )
                    if hasattr(res, "embeddings") and res.embeddings:
                        live_vecs.append(res.embeddings[0].values)
                if len(live_vecs) == len(self.article_list):
                    matrix = np.array(live_vecs, dtype=np.float32)
                    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
                    norms[norms == 0] = 1.0
                    self.vectors = matrix / norms
                    self.save_cache()
                    return
            except Exception as e:
                print(f"Live embedding failed: {e}. Using deterministic semantic index.")

        # Deterministic feature matrix
        self.vectors = compute_bm25_features(self.article_list, self.vocabulary)
        self.save_cache()

    def save_cache(self) -> None:
        """Save indexed vectors and vocabulary to JSON cache."""
        if self.vectors is None:
            return
        cache_data = {
            "model": settings.embedding_model,
            "article_ids": self.article_ids,
            "vocabulary": self.vocabulary,
            "vectors": self.vectors.tolist()
        }
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a query using gemini-embedding-001 if available, else feature projection."""
        client = self._get_client()
        if client and self.vectors is not None and self.vectors.shape[1] > len(self.vocabulary):
            try:
                res = client.models.embed_content(
                    model=settings.embedding_model,
                    contents=query
                )
                if hasattr(res, "embeddings") and res.embeddings:
                    vec = np.array(res.embeddings[0].values, dtype=np.float32)
                    norm = np.linalg.norm(vec)
                    return vec / (norm if norm > 0 else 1.0)
            except Exception as e:
                print(f"Live query embedding error: {e}")

        # Fallback to vocabulary projection
        q_tokens = tokenize(query)
        q_vec = np.zeros((len(self.vocabulary),), dtype=np.float32)
        for t in q_tokens:
            if t in self.vocabulary:
                idx = self.vocabulary.index(t)
                q_vec[idx] += 1.0
        norm = np.linalg.norm(q_vec)
        return q_vec / (norm if norm > 0 else 1.0)

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve top matching articles using cosine similarity over embeddings."""
        if not self.article_list or self.vectors is None:
            return []

        q_vec = self.embed_query(query)
        # Cosine similarity (both are unit normalized)
        scores = np.dot(self.vectors, q_vec)

        # Boost score if exact keywords or ID match
        q_lower = query.lower()
        for idx, art in enumerate(self.article_list):
            if art["id"].lower() in q_lower:
                scores[idx] += 0.5
            for kw in art.get("keywords", []):
                if kw in q_lower:
                    scores[idx] += 0.08

        ranked_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in ranked_indices:
            art = self.article_list[idx]
            raw_score = float(scores[idx])
            # Normalize confidence score for display (0.0 to 1.0)
            confidence = min(max(raw_score, 0.0), 1.0)
            if raw_score > 1.0:
                confidence = 0.98

            # Find best matching section
            best_section = None
            best_sec_score = -1
            q_terms = set(tokenize(query))
            for sec in art.get("sections", []):
                sec_terms = set(tokenize(sec.get("heading", "") + " " + sec.get("text", "")))
                overlap = len(q_terms.intersection(sec_terms))
                if overlap > best_sec_score:
                    best_sec_score = overlap
                    best_section = sec

            results.append({
                "article_id": art["id"],
                "title": art["title"],
                "category": art["category"],
                "summary": art["summary"],
                "score": round(confidence, 4),
                "best_section": best_section or (art["sections"][0] if art.get("sections") else None),
                "sections": art.get("sections", [])
            })

        return results

    def get_article(self, article_id: str) -> Optional[Dict[str, Any]]:
        """Fetch article by exact ID."""
        return self.articles.get(article_id)

    def list_all_articles(self) -> List[Dict[str, Any]]:
        """Return full catalog of articles."""
        return list(self.articles.values())


knowledge_base = KnowledgeBase()
