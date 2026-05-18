"""
PDF Processing Service
- Extracts text page-by-page using PyMuPDF (fitz)
- Splits text into overlapping chunks
- Returns chunks with metadata (page number, char offset)
"""
import fitz  # PyMuPDF
from typing import List, Dict, Any
from config import CHUNK_SIZE, CHUNK_OVERLAP


def extract_pages(file_path: str) -> List[Dict[str, Any]]:
    """Extract text from each page of a PDF."""
    doc = fitz.open(file_path)
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()
        if text:
            pages.append({
                "page": page_num + 1,   # 1-indexed
                "text": text,
            })
    doc.close()
    return pages


def chunk_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Split page texts into overlapping chunks.
    Each chunk carries:
        - chunk_id  : sequential id
        - page      : source page number
        - text      : chunk content
        - char_start: start offset within page text
    """
    chunks = []
    chunk_id = 0

    for page_info in pages:
        page_num = page_info["page"]
        text = page_info["text"]
        start = 0

        while start < len(text):
            end = start + CHUNK_SIZE
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "chunk_id": chunk_id,
                    "page": page_num,
                    "text": chunk_text,
                    "char_start": start,
                })
                chunk_id += 1

            if end >= len(text):
                break
            start = end - CHUNK_OVERLAP   # slide with overlap

    return chunks


def process_pdf(file_path: str) -> Dict[str, Any]:
    """
    Full pipeline: PDF → pages → chunks.
    Returns dict with page_count, chunk_count, chunks list.
    """
    pages = extract_pages(file_path)
    chunks = chunk_pages(pages)
    return {
        "page_count": len(pages),
        "chunk_count": len(chunks),
        "chunks": chunks,
    }
