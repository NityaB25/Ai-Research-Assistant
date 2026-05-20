"""
PDF Processing Service
- Extracts text page-by-page using PyMuPDF (fitz)
- Splits text into overlapping chunks
- Returns chunks with metadata (page number, char offset)
"""
import fitz  # PyMuPDF
from typing import List, Dict, Any
from config import CHUNK_SIZE, CHUNK_OVERLAP,MIN_CHUNK_SIZE
import re


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


def split_into_sentences(text: str) -> List[str]:
    """
    Lightweight sentence splitter.
    """

    text = re.sub(r"\s+", " ", text).strip()

    sentences = re.split(
        r'(?<=[.!?])\s+(?=[A-Z])',
        text
    )

    return [s.strip() for s in sentences if s.strip()]


def chunk_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sentence-aware semantic chunking with overlap.
    """

    chunks = []
    chunk_id = 0

    for page_info in pages:
        page_num = page_info["page"]
        text = page_info["text"]

        sentences = split_into_sentences(text)

        current_chunk = []
        current_length = 0
        char_start = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            # If adding sentence exceeds chunk size,
            # finalize current chunk
            if (
                current_length + sentence_length > CHUNK_SIZE
                and current_length >= MIN_CHUNK_SIZE
            ):

                chunk_text = " ".join(current_chunk).strip()

                if chunk_text:
                    chunks.append({
                        "chunk_id": chunk_id,
                        "page": page_num,
                        "text": chunk_text,
                        "char_start": char_start,
                    })

                    chunk_id += 1

                # Build overlap using last sentences
                overlap_sentences = []
                overlap_length = 0

                for s in reversed(current_chunk):
                    overlap_sentences.insert(0, s)
                    overlap_length += len(s)

                    if overlap_length >= CHUNK_OVERLAP:
                        break

                current_chunk = overlap_sentences
                current_length = overlap_length

                char_start += max(
                    len(chunk_text) - overlap_length,
                    0
                )

            current_chunk.append(sentence)
            current_length += sentence_length

        # Final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk).strip()

            if chunk_text:
                chunks.append({
                    "chunk_id": chunk_id,
                    "page": page_num,
                    "text": chunk_text,
                    "char_start": char_start,
                })

                chunk_id += 1

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
