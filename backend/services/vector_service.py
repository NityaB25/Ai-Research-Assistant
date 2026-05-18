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
from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL, TOP_K_RESULTS, VECTOR_DIR

# Load model once at module level (cached after first load)
_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


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


def retrieve(query: str, base_path: str, top_k: int = TOP_K_RESULTS) -> List[Dict[str, Any]]:
    """
    Semantic search: embed query → search FAISS → return top_k chunks with scores.

    Returns list of dicts:
        { chunk_id, page, text, char_start, score }
    """
    model = get_model()
    index, metadata = load_index(base_path)

    query_vec = model.encode([query], show_progress_bar=False)
    query_vec = np.array(query_vec, dtype=np.float32)
    faiss.normalize_L2(query_vec)

    scores, indices = index.search(query_vec, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:          # FAISS returns -1 for not-found slots
            continue
        chunk = metadata[idx].copy()
        chunk["score"] = float(score)
        results.append(chunk)

    # Sort by score descending (already sorted but be explicit)
    results.sort(key=lambda x: x["score"], reverse=True)
    return results
