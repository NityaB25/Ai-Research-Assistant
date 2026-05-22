"""
Vector Store Service
- Generates embeddings remotely
- Builds and persists FAISS indexes
- Uses Supabase Storage for persistence
"""

import pickle
from pathlib import Path
from typing import List, Dict, Any, Tuple

import faiss
import httpx
import numpy as np

from config import (
    VECTOR_DIR,
    INITIAL_RETRIEVAL_K,
    FINAL_RERANK_K,
    INFERENCE_SERVER_URL,
)

from services.storage_service import (
    upload_vector_file,
    download_vector_file,
)

# ─────────────────────────────────────────────────────────────
# HTTP Client Config
# ─────────────────────────────────────────────────────────────

HTTP_TIMEOUT = httpx.Timeout(
    120.0,
    connect=30.0,
)


# ─────────────────────────────────────────────────────────────
# Build Index
# ─────────────────────────────────────────────────────────────

def build_index(
    document_id: int,
    chunks: List[Dict[str, Any]],
) -> str:
    """
    Generate embeddings and build FAISS index.
    """

    texts = [c["text"] for c in chunks]

    # Remote embeddings
    response = httpx.post(
        f"{INFERENCE_SERVER_URL}/embed",
        json={"texts": texts},
        timeout=HTTP_TIMEOUT,
    )

    response.raise_for_status()

    embeddings = response.json()["embeddings"]

    embeddings = np.array(
        embeddings,
        dtype=np.float32,
    )

    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings)

    dim = embeddings.shape[1]

    index = faiss.IndexFlatIP(dim)

    index.add(embeddings)

    # Local temp paths
    base_path = str(
        VECTOR_DIR / str(document_id)
    )

    faiss_path = base_path + ".faiss"
    pkl_path = base_path + ".pkl"

    # Save FAISS locally
    faiss.write_index(
        index,
        faiss_path,
    )

    # Upload FAISS to Supabase
    upload_vector_file(
        faiss_path,
        f"{document_id}.faiss",
    )

    # Metadata
    metadata = [
        {
            "chunk_id": c["chunk_id"],
            "page": c["page"],
            "text": c["text"],
            "char_start": c.get(
                "char_start",
                0,
            ),
        }
        for c in chunks
    ]

    # Save PKL locally
    with open(pkl_path, "wb") as f:
        pickle.dump(metadata, f)

    # Upload PKL to Supabase
    upload_vector_file(
        pkl_path,
        f"{document_id}.pkl",
    )

    # Cleanup local temp files
    Path(faiss_path).unlink(
        missing_ok=True
    )

    Path(pkl_path).unlink(
        missing_ok=True
    )

    return base_path


# ─────────────────────────────────────────────────────────────
# Load Index
# ─────────────────────────────────────────────────────────────

def load_index(
    base_path: str,
) -> Tuple[faiss.Index, List[Dict]]:
    """
    Load FAISS index and metadata.
    Downloads only if not cached locally.
    """

    faiss_path = base_path + ".faiss"
    pkl_path = base_path + ".pkl"

    # Download FAISS if missing
    if not Path(faiss_path).exists():

        download_vector_file(
            Path(base_path).name + ".faiss",
            faiss_path,
        )

    # Download PKL if missing
    if not Path(pkl_path).exists():

        download_vector_file(
            Path(base_path).name + ".pkl",
            pkl_path,
        )

    # Load FAISS
    index = faiss.read_index(
        faiss_path
    )

    # Load metadata
    with open(pkl_path, "rb") as f:
        metadata = pickle.load(f)

    return index, metadata


# ─────────────────────────────────────────────────────────────
# Retrieval
# ─────────────────────────────────────────────────────────────

def retrieve(
    query: str,
    base_path: str,
    top_k: int = FINAL_RERANK_K,
) -> List[Dict[str, Any]]:
    """
    Retrieval pipeline:
    1. Dense retrieval
    2. Reranking
    3. Return top chunks
    """

    index, metadata = load_index(
        base_path
    )

    # ── Query embedding ─────────────────────

    response = httpx.post(
        f"{INFERENCE_SERVER_URL}/embed",
        json={"texts": [query]},
        timeout=HTTP_TIMEOUT,
    )

    response.raise_for_status()

    query_vec = response.json()[
        "embeddings"
    ]

    query_vec = np.array(
        query_vec,
        dtype=np.float32,
    )

    faiss.normalize_L2(query_vec)

    # ── Dense retrieval ─────────────────────

    scores, indices = index.search(
        query_vec,
        INITIAL_RETRIEVAL_K,
    )

    candidates = []

    for score, idx in zip(
        scores[0],
        indices[0],
    ):

        if idx < 0:
            continue

        chunk = metadata[idx].copy()

        chunk["score"] = float(score)

        candidates.append(chunk)

    if not candidates:
        return []

    # ── Reranking ───────────────────────────

    response = httpx.post(
        f"{INFERENCE_SERVER_URL}/rerank",
        json={
            "query": query,
            "documents": [
                chunk["text"]
                for chunk in candidates
            ],
        },
        timeout=HTTP_TIMEOUT,
    )

    response.raise_for_status()

    rerank_scores = response.json()[
        "scores"
    ]

    for chunk, rerank_score in zip(
        candidates,
        rerank_scores,
    ):
        chunk["rerank_score"] = float(
            rerank_score
        )

    # Sort by reranker score
    candidates.sort(
        key=lambda x: x["rerank_score"],
        reverse=True,
    )

    # Final top-k
    final_results = candidates[:top_k]

    return final_results