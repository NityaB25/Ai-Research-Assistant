"""
Vector Store Service
- Generates embeddings using SentenceTransformers (all-MiniLM-L6-v2)
- Builds and persists a FAISS index per document
- Loads index for semantic retrieval at query time
"""
import pickle
import numpy as np
import faiss
from pathlib import Path
from typing import List, Dict, Any, Tuple
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import (
        SentenceTransformer,
        CrossEncoder,
    )
from config import (
    EMBEDDING_MODEL,
    VECTOR_DIR,
    INITIAL_RETRIEVAL_K,
    FINAL_RERANK_K,
    RERANKER_MODEL,
)

# Load model once at module level (cached after first load)
_model = None
_reranker = None


def get_model():
    global _model

    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(
            EMBEDDING_MODEL
        )

    return _model


def get_reranker():
    global _reranker

    if _reranker is None:
        from sentence_transformers import CrossEncoder

        _reranker = CrossEncoder(
            RERANKER_MODEL
        )

    return _reranker


# ── Index building ──────────────────────────────────────────────────────────

def build_index(document_id: int, chunks: List[Dict[str, Any]]) -> str:
    """
    Embed all chunks and save a FAISS flat L2 index + metadata pickle.

    Saved files:
        vectors/<doc_id>.faiss   – FAISS index
        vectors/<doc_id>.pkl     – chunk metadata list (text, page, char_start)

    Returns the base path string (without extension).
    """
    model = get_model()
    texts = [c["text"] for c in chunks]

    # Generate embeddings  (batch for speed)
    embeddings = model.encode(texts, batch_size=32, show_progress_bar=False)
    embeddings = np.array(embeddings, dtype=np.float32)

    # Normalise so inner-product == cosine similarity
    faiss.normalize_L2(embeddings)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)   # Inner Product on normalised vecs = cosine
    index.add(embeddings)

    base_path = str(VECTOR_DIR / str(document_id))
    faiss.write_index(index, base_path + ".faiss")

    # Store metadata alongside index
    metadata = [
        {
            "chunk_id": c["chunk_id"],
            "page": c["page"],
            "text": c["text"],
            "char_start": c.get("char_start", 0),
        }
        for c in chunks
    ]
    with open(base_path + ".pkl", "wb") as f:
        pickle.dump(metadata, f)

    return base_path


# ── Retrieval ───────────────────────────────────────────────────────────────

def load_index(base_path: str) -> Tuple[faiss.Index, List[Dict]]:
    """Load FAISS index and metadata from disk."""
    index = faiss.read_index(base_path + ".faiss")
    with open(base_path + ".pkl", "rb") as f:
        metadata = pickle.load(f)
    return index, metadata


def retrieve(
    query: str,
    base_path: str,
    top_k: int = FINAL_RERANK_K,
) -> List[Dict[str, Any]]:
    """
    Retrieval pipeline:
    1. FAISS semantic retrieval
    2. Cross-encoder reranking
    3. Return best chunks
    """

    model = get_model()
    reranker = get_reranker()

    index, metadata = load_index(base_path)

    # ── Step 1: Dense retrieval via FAISS ─────────────────────

    query_vec = model.encode([query], show_progress_bar=False)
    query_vec = np.array(query_vec, dtype=np.float32)

    faiss.normalize_L2(query_vec)

    scores, indices = index.search(query_vec, INITIAL_RETRIEVAL_K)

    candidates = []

    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue

        chunk = metadata[idx].copy()
        chunk["score"] = float(score)

        candidates.append(chunk)

    if not candidates:
        return []

    # ── Step 2: Cross-encoder reranking ─────────────────────

    pairs = [
        [query, chunk["text"]]
        for chunk in candidates
    ]

    rerank_scores = reranker.predict(pairs)

    for chunk, rerank_score in zip(candidates, rerank_scores):
        chunk["rerank_score"] = float(rerank_score)

    # Sort by reranker score
    candidates.sort(
        key=lambda x: x["rerank_score"],
        reverse=True,
    )

    # Keep best reranked chunks
    final_results = candidates[:top_k]

    

    return final_results