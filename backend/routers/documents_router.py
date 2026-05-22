import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    BackgroundTasks,
)
from fastapi.responses import Response
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from database import (
    get_db,
    Document,
    User,
)
from auth import get_current_user

from services.pdf_service import process_pdf
from services.vector_service import build_index

from services.storage_service import (
    upload_document,
    download_document,
    delete_document as delete_document_storage,
    delete_vector_file,
)

from config import (
    UPLOAD_DIR,
    SECRET_KEY,
    ALGORITHM,
)

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)

ALLOWED_TYPES = {
    "application/pdf",
    "application/x-pdf",
}

MAX_FILE_SIZE = 50 * 1024 * 1024   # 50MB


# ─────────────────────────────────────────────────────────────
# Background Processing
# ─────────────────────────────────────────────────────────────

def _process_document_bg(
    document_id: int,
    file_path: str,
):
    """
    Background task:
    PDF → chunking → embeddings → FAISS
    """

    from database import SessionLocal

    db = SessionLocal()

    try:
        doc = db.query(Document).filter(
            Document.id == document_id
        ).first()

        if not doc:
            return

        # Extract + chunk PDF
        result = process_pdf(file_path)

        # Build vector index
        base_path = build_index(
            document_id,
            result["chunks"],
        )

        # Update DB
        doc.page_count = result["page_count"]
        doc.chunk_count = result["chunk_count"]
        doc.vector_path = base_path
        doc.status = "ready"

        db.commit()

    except Exception as e:
        db.rollback()

        doc = db.query(Document).filter(
            Document.id == document_id
        ).first()

        if doc:
            doc.status = "error"
            doc.error_msg = str(e)

            db.commit()

    finally:
        # Remove temporary local PDF
        try:
            Path(file_path).unlink(
                missing_ok=True
            )
        except:
            pass

        db.close()


# ─────────────────────────────────────────────────────────────
# Upload Document
# ─────────────────────────────────────────────────────────────

@router.post("/upload", status_code=201)
async def upload_document_route(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # Validate type
    if (
        file.content_type not in ALLOWED_TYPES
        and not file.filename.endswith(".pdf")
    ):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted",
        )

    # Read content
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large (max 50MB)",
        )

    # Generate unique filename
    stored_name = f"{uuid.uuid4().hex}.pdf"

    # Upload to Supabase Storage
    upload_document(
        content,
        stored_name,
    )

    # Save temporary local copy for processing
    local_temp_path = UPLOAD_DIR / stored_name

    with open(local_temp_path, "wb") as f:
        f.write(content)

    # Create DB record
    doc = Document(
        filename=stored_name,
        original_name=file.filename,
        file_path=stored_name,
        status="processing",
        owner_id=current_user.id,
    )

    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Background processing
    background_tasks.add_task(
        _process_document_bg,
        doc.id,
        str(local_temp_path),
    )

    return {
        "id": doc.id,
        "original_name": doc.original_name,
        "status": doc.status,
        "uploaded_at": doc.uploaded_at.isoformat(),
    }


# ─────────────────────────────────────────────────────────────
# List Documents
# ─────────────────────────────────────────────────────────────

@router.get("/")
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    docs = (
        db.query(Document)
        .filter(Document.owner_id == current_user.id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )

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


# ─────────────────────────────────────────────────────────────
# Document Status
# ─────────────────────────────────────────────────────────────

@router.get("/{doc_id}/status")
def document_status(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.owner_id == current_user.id,
    ).first()

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    return {
        "id": doc.id,
        "status": doc.status,
        "page_count": doc.page_count,
        "chunk_count": doc.chunk_count,
        "error_msg": doc.error_msg,
    }


# ─────────────────────────────────────────────────────────────
# Serve PDF
# ─────────────────────────────────────────────────────────────

@router.get("/{doc_id}/file")
def get_document_file(
    doc_id: int,
    token: str,
    db: Session = Depends(get_db),
):

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = int(payload.get("sub"))

    except (JWTError, TypeError, ValueError):

        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )

    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.owner_id == user_id,
    ).first()

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    pdf_bytes = download_document(
        doc.file_path
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "inline"
        },
    )


# ─────────────────────────────────────────────────────────────
# Delete Document
# ─────────────────────────────────────────────────────────────

@router.delete("/{doc_id}", status_code=204)
def delete_document_route(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.owner_id == current_user.id,
    ).first()

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    # Delete PDF from storage
    delete_document_storage(
        doc.file_path
    )

    # Delete vectors from storage
    if doc.vector_path:

        vector_name = Path(
            doc.vector_path
        ).name

        delete_vector_file(
            f"{vector_name}.faiss"
        )

        delete_vector_file(
            f"{vector_name}.pkl"
        )

    # Delete DB row
    db.delete(doc)
    db.commit()

    return Response(status_code=204)