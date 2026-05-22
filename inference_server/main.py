from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import (
    SentenceTransformer,
    CrossEncoder,
)

app = FastAPI()

# Load models ONCE
embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

reranker_model = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)


# ── Request Schemas ─────────────────────

class EmbedRequest(BaseModel):
    texts: list[str]


class RerankRequest(BaseModel):
    query: str
    documents: list[str]


# ── Health ──────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Embeddings ──────────────────────────

@app.post("/embed")
def embed(req: EmbedRequest):

    embeddings = embedding_model.encode(
        req.texts,
        batch_size=32,
        show_progress_bar=False,
    )

    return {
        "embeddings": embeddings.tolist()
    }


# ── Reranking ───────────────────────────

@app.post("/rerank")
def rerank(req: RerankRequest):

    pairs = [
        [req.query, doc]
        for doc in req.documents
    ]

    scores = reranker_model.predict(
        pairs
    )

    return {
        "scores": scores.tolist()
    }