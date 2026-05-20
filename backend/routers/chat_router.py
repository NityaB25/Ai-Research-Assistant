import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db, Document, ChatSession, ChatMessage, User
from auth import get_current_user
from services.vector_service import retrieve
from services.llm_service import generate_answer, extract_citations, summarize_conversation,should_rewrite_query,rewrite_query

router = APIRouter(prefix="/chat", tags=["chat"])


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    document_id: int
    title: str | None = None


class AskRequest(BaseModel):
    question: str
    top_k: int = 5


# ── Session management ───────────────────────────────────────────────────────

@router.post("/sessions", status_code=201)
def create_session(
    req: CreateSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(
        Document.id == req.document_id,
        Document.owner_id == current_user.id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "ready":
        raise HTTPException(status_code=400, detail=f"Document not ready (status: {doc.status})")

    session = ChatSession(
        title=req.title or f"Chat about {doc.original_name}",
        owner_id=current_user.id,
        document_id=req.document_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_dict(session)


@router.get("/sessions")
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.owner_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    return [_session_dict(s) for s in sessions]


@router.get("/sessions/{session_id}")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_session_or_404(session_id, current_user.id, db)
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return {
        **_session_dict(session),
        "messages": [_message_dict(m) for m in messages],
    }


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_session_or_404(session_id, current_user.id, db)
    db.delete(session)
    db.commit()


# ── RAG Q&A ──────────────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/ask")
async def ask(
    session_id: int,
    req: AskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_session_or_404(session_id, current_user.id, db)
    doc = db.query(Document).filter(Document.id == session.document_id).first()

    if not doc or doc.status != "ready":
        raise HTTPException(status_code=400, detail="Document not ready")

    if not doc.vector_path:
        raise HTTPException(status_code=400, detail="Vector index not found")

    # 1. Build conversation history
    history_msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )

    history = [
        {"role": m.role, "content": m.content}
        for m in history_msgs
    ]

    # 2. Rolling summarization after long conversations
    if len(history) > 12:
        old_messages = history[:-6]

        updated_summary = await summarize_conversation(
            old_messages,
            session.summary or "",
        )

        session.summary = updated_summary
        db.commit()

        # Keep only recent messages active
        history = history[-6:]

    # 3. Decide whether query rewrite is needed
    final_query = req.question

    rewrite_needed = await should_rewrite_query(
        req.question,
        history,
        session.summary,
    )

    if rewrite_needed:
        final_query = await rewrite_query(
            req.question,
            history,
            session.summary,
        )

    print("Original Query:", req.question)
    print("Final Query:", final_query)

    # 4. Retrieve relevant chunks via FAISS
    retrieved = retrieve(
        final_query,
        doc.vector_path,
        top_k=req.top_k,
    )

    if not retrieved:
        raise HTTPException(status_code=500, detail="No relevant chunks found")

    # 5. Generate answer via LLM
    answer = await generate_answer(
        req.question,
        retrieved,
        history,
        session.summary,
    )

    # 6. Extract citations
    citations = extract_citations(retrieved)

    # 7. Save user message
    user_msg = ChatMessage(
        role="user",
        content=req.question,
        session_id=session_id,
    )
    db.add(user_msg)

    # 8. Save assistant message
    assistant_msg = ChatMessage(
        role="assistant",
        content=answer,
        sources=json.dumps(citations),
        session_id=session_id,
    )

    db.add(assistant_msg)

    db.commit()
    db.refresh(assistant_msg)

    return {
        "answer": answer,
        "citations": citations,
        "retrieved_chunks": [
            {
                "page": c["page"],
                "score": c["score"],
                "snippet": c["text"][:300],
            }
            for c in retrieved
        ],
        "message_id": assistant_msg.id,
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_session_or_404(session_id: int, user_id: int, db: Session) -> ChatSession:
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.owner_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def _session_dict(s: ChatSession) -> dict:
    return {
        "id": s.id,
        "title": s.title,
        "document_id": s.document_id,
        "created_at": s.created_at.isoformat(),
    }


def _message_dict(m: ChatMessage) -> dict:
    return {
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "sources": json.loads(m.sources) if m.sources else [],
        "created_at": m.created_at.isoformat(),
    }