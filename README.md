# AI Research Assistant

A conversational Retrieval-Augmented Generation (RAG) research assistant built with FastAPI, React, FAISS, and modern retrieval techniques.

This project allows users to upload PDFs, ask contextual questions about documents, receive grounded answers with citations, and interact with the document in a conversational manner.

---

# Features

## Conversational RAG
- Multi-turn chat over PDFs
- Context-aware follow-up questions
- Conversation memory summarization
- Query rewriting for ambiguous references

Example:

```text
User: Explain Gibbs Sampling
User: What are its limitations?
```

The system rewrites the second query internally into:

```text
What are the limitations of Gibbs Sampling?
```

before retrieval.

---

## Semantic Retrieval Pipeline

### Sentence-Aware Chunking
Instead of naive fixed-character chunking, the system uses sentence-aware overlapping semantic chunks.

Benefits:
- Better retrieval quality
- Cleaner context boundaries
- Improved reranking accuracy
- More coherent answers

---

### Dense Vector Retrieval (FAISS)

Documents are embedded using:

```text
all-MiniLM-L6-v2
```

and indexed using:

```text
FAISS IndexFlatIP
```

This enables fast semantic similarity search across document chunks.

---

### Cross-Encoder Reranking

Initial semantic retrieval candidates are reranked using:

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

Pipeline:

```text
Query
  ↓
FAISS retrieves top 15 chunks
  ↓
Cross-encoder reranks chunks
  ↓
Top 5 most relevant chunks selected
```

Benefits:
- Better retrieval precision
- Reduced noisy chunks
- Stronger contextual grounding
- Improved follow-up question handling

---

## Streaming Responses

Answers stream token-by-token in real time using:

```text
FastAPI StreamingResponse
```

and OpenRouter streaming APIs.

This provides:
- Faster perceived response time
- Improved UX
- ChatGPT-like interaction

---

## Source Grounding & Citations

Every answer is grounded in retrieved document chunks.

Features:
- Page citations
- Expandable source cards
- PDF preview pane
- Clickable source navigation
- Active page highlighting

Users can inspect the exact retrieved passages used to generate answers.

---

## Conversation Memory Summarization

Long conversations are compressed into rolling summaries.

Benefits:
- Prevents context window overflow
- Preserves long-term memory
- Maintains conversational continuity
- Reduces token usage

---

# Architecture

```text
PDF Upload
    ↓
Text Extraction (PyMuPDF)
    ↓
Sentence-Aware Chunking
    ↓
Embeddings (MiniLM)
    ↓
FAISS Vector Index
    ↓

User Query
    ↓
Conversation History + Summary
    ↓
Conditional Query Rewriting
    ↓
FAISS Retrieval
    ↓
Cross-Encoder Reranking
    ↓
Context Construction
    ↓
LLM Generation (Streaming)
    ↓
Grounded Answer + Citations
```

---

# Tech Stack

## Backend
- FastAPI
- SQLAlchemy
- SQLite
- FAISS
- SentenceTransformers
- PyMuPDF
- OpenRouter API
- httpx

## Frontend
- React
- Vite
- TailwindCSS
- React Router
- React Markdown
- React PDF
- Lucide Icons

---

# Project Structure

```text
backend/
├── routers/
│   ├── auth_router.py
│   ├── chat_router.py
│   └── document_router.py
│
├── services/
│   ├── llm_service.py
│   ├── pdf_service.py
│   └── vector_service.py
│
├── uploads/
├── vectors/
├── database.py
├── config.py
└── main.py

frontend/
├── src/
│   ├── pages/
│   ├── components/
│   ├── api/
│   ├── context/
│   └── styles/
```

---

# Retrieval Pipeline Details

## 1. Query Rewriting

The system determines whether a query depends on prior conversational context.

If needed, it rewrites the query into a standalone semantic query.

Example:

```text
Original Query:
"Is it caused by the ergodic property?"

Rewritten Query:
"Is the Markov property caused by the ergodic property?"
```

This significantly improves retrieval quality for follow-up questions.

---

## 2. Dense Retrieval

Chunks are embedded using:

```text
all-MiniLM-L6-v2
```

Retrieval uses cosine similarity over normalized vectors.

---

## 3. Reranking

Retrieved chunks are reranked using a cross-encoder.

Unlike embedding similarity, the reranker jointly processes:

```text
(query, chunk)
```

allowing deeper semantic relevance scoring.

---

# Frontend Features

## Interactive PDF Viewer
- Side-by-side PDF + chat layout
- Page scrolling
- Citation-linked navigation
- Active page highlighting

---

## Real-Time Streaming UI
- Token streaming
- Smooth incremental rendering
- Live markdown rendering
- Responsive conversational experience

---

# Authentication

The application uses JWT authentication.

Features:
- Signup/Login
- Protected routes
- Persistent sessions
- Automatic logout on token expiration

---

# Installation

## Clone Repository

```bash
git clone <repo-url>
cd ai-research-assistant
```

---

# Backend Setup

```bash
cd backend
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### Linux / Mac

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.env`:

```env
OPENROUTER_API_KEY=your_api_key
SECRET_KEY=your_secret_key
```

Run backend:

```bash
uvicorn main:app --reload
```

---

# Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

---

# API Endpoints

## Authentication

```text
POST /auth/signup
POST /auth/login
GET  /auth/me
```

---

## Documents

```text
POST   /documents/upload
GET    /documents/
GET    /documents/{id}/status
DELETE /documents/{id}
```

---

## Chat

```text
POST /chat/sessions
GET  /chat/sessions
GET  /chat/sessions/{id}
POST /chat/sessions/{id}/ask
POST /chat/sessions/{id}/ask-stream
```

---

# Example Workflow

1. Upload a PDF
2. System extracts and chunks text
3. Embeddings are generated
4. FAISS index is built
5. User asks questions
6. Retrieval + reranking selects relevant chunks
7. LLM generates grounded response
8. Citations link back to document pages

---

# Why This Project Is Different

Most basic RAG projects only implement:

```text
PDF → Embeddings → LLM
```

This project additionally includes:

- Conversational retrieval
- Query rewriting
- Sentence-aware chunking
- Cross-encoder reranking
- Streaming responses
- Rolling conversation memory
- Interactive PDF navigation
- Grounded citations

making it significantly closer to production-grade RAG systems.

---

# Future Improvements

Potential future upgrades:

- Hybrid Retrieval (BM25 + Vector Search)
- Multi-query retrieval
- Query decomposition
- Semantic caching
- Parent-child retrieval
- OCR support
- Multi-document chat
- Highlight exact citation spans
- Cloud deployment

---




---

# Author

Nitya Bhavsar

Built as an advanced conversational RAG research assistant project using modern retrieval and LLM engineering techniques.