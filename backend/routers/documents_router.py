import uuid
import asyncio
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db, Document, User
from auth import get_current_user
from services.pdf_service import process_pdf
from services.vector_service import build_index
from config import UPLOAD_DIR
from fastapi.responses import FileResponse

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_TYPES = {"application/pdf", "application/x-pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024   # 50 MB


def _process_document_bg(document_id: int, file_path: str):
    """Background task: extract PDF → build FAISS index → update DB status."""
    from database import SessionLocal
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return

        # 1. Extract + chunk PDF
        result = process_pdf(file_path)

        # 2. Build FAISS index
        base_path = build_index(document_id, result["chunks"])

        # 3. Update document record
        doc.page_count = result["page_count"]
        doc.chunk_count = result["chunk_count"]
        doc.vector_path = base_path
        doc.status = "ready"
        db.commit()

    except Exception as e:
        db.rollback()
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = "error"
            doc.error_msg = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/upload", status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate file type
    if file.content_type not in ALLOWED_TYPES and not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 50 MB)")

    # Save to disk
    stored_name = f"{uuid.uuid4().hex}.pdf"
    file_path = UPLOAD_DIR / stored_name
    with open(file_path, "wb") as f:
        f.write(content)

    # Create DB record
    doc = Document(
        filename=stored_name,
        original_name=file.filename,
        file_path=str(file_path),
        status="processing",
        owner_id=current_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Process in background
    background_tasks.add_task(_process_document_bg, doc.id, str(file_path))

    return {
        "id": doc.id,
        "original_name": doc.original_name,
        "status": doc.status,
        "uploaded_at": doc.uploaded_at.isoformat(),
    }


@router.get("/")
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs = db.query(Document).filter(Document.owner_id == current_user.id).order_by(Document.uploaded_at.desc()).all()
    return [
        {
            "id": d.id,
            "original_name": d.original_name,
            "page_count": d.page_count,
            "chunk_count": d.chunk_count,
            "status": d.status,
            "error_msg": d.error_msg,
            "uploaded_at": d.uploaded_at.isoformat(),
        }
        for d in docs
    ]


@router.get("/{doc_id}/status")
def document_status(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.owner_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": doc.id,
        "status": doc.status,
        "page_count": doc.page_count,
        "chunk_count": doc.chunk_count,
        "error_msg": doc.error_msg,
    }

from jose import JWTError, jwt
from config import SECRET_KEY, ALGORITHM

@router.get("/{doc_id}/file")
def get_document_file(
    doc_id: int,
    token: str,
    db: Session = Depends(get_db),
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.owner_id == user_id,
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    path = Path(doc.file_path)

    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF file missing")

    response = FileResponse(
    path=str(path),
    media_type="application/pdf",
)

    response.headers["Content-Disposition"] = "inline"

    return response 



@router.delete("/{doc_id}", status_code=204)
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.owner_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove files from disk
    for suffix in ["", ".faiss", ".pkl"]:
        path = Path(doc.file_path if not suffix else (doc.vector_path or "") + suffix)
        if path.exists():
            path.unlink(missing_ok=True)

    db.delete(doc)
    db.commit()
