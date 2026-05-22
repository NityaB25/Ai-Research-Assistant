from supabase import create_client
from config import (
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
)

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
)

DOCUMENT_BUCKET = "documents"
VECTOR_BUCKET = "vectors"


def upload_document(
    file_bytes: bytes,
    filename: str,
):
    supabase.storage.from_(DOCUMENT_BUCKET).upload(
        path=filename,
        file=file_bytes,
        file_options={
            "content-type": "application/pdf"
        },
    )

    return filename


def download_document(filename: str):
    return supabase.storage.from_(
        DOCUMENT_BUCKET
    ).download(filename)


def delete_document(filename: str):
    supabase.storage.from_(
        DOCUMENT_BUCKET
    ).remove([filename])


def upload_vector_file(
    local_path: str,
    storage_name: str,
):
    with open(local_path, "rb") as f:
        supabase.storage.from_(VECTOR_BUCKET).upload(
            path=storage_name,
            file=f.read(),
        )


def download_vector_file(
    storage_name: str,
    local_path: str,
):
    data = supabase.storage.from_(
        VECTOR_BUCKET
    ).download(storage_name)

    with open(local_path, "wb") as f:
        f.write(data)


def delete_vector_file(storage_name: str):
    supabase.storage.from_(
        VECTOR_BUCKET
    ).remove([storage_name])