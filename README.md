# AI Research Assistant

A full-stack RAG application to chat with research papers.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | FastAPI + Python |
| Embeddings | `all-MiniLM-L6-v2` via SentenceTransformers |
| Vector DB | FAISS (IndexFlatIP — cosine similarity) |
| LLM | `meta-llama/llama-3.3-8b-instruct:free` via OpenRouter |
| PDF | PyMuPDF (fitz) |
| Auth | JWT + bcrypt via passlib |
| Database | SQLite via SQLAlchemy |

## RAG Pipeline

```
User Uploads PDF
      ↓
PyMuPDF → page-wise text extraction
      ↓
Chunking (800 chars, 100 overlap)
      ↓
SentenceTransformer embeddings (384-dim)
      ↓
FAISS IndexFlatIP (normalised → cosine similarity)
      ↓
User Query → embed → FAISS search → top-5 chunks
      ↓
Context + history → Llama 3.3 via OpenRouter
      ↓
Answer + page citations displayed in chat
```

## Project Structure

```
ai-research-assistant/
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── config.py                # Settings & paths
│   ├── database.py              # SQLAlchemy models
│   ├── auth.py                  # JWT helpers
│   ├── routers/
│   │   ├── auth_router.py       # /auth/signup, /auth/login
│   │   ├── documents_router.py  # /documents/upload, list, delete
│   │   └── chat_router.py       # /chat/sessions, /ask (RAG)
│   └── services/
│       ├── pdf_service.py       # PDF extraction + chunking
│       ├── vector_service.py    # FAISS build + retrieve
│       └── llm_service.py       # OpenRouter LLM call
├── frontend/
│   └── src/
│       ├── api/client.js        # Axios + API helpers
│       ├── context/AuthContext  # Global auth state
│       ├── pages/
│       │   ├── AuthPage.jsx     # Login / Signup
│       │   ├── Dashboard.jsx    # Document library + upload
│       │   └── ChatPage.jsx     # RAG chat interface
│       └── components/
│           └── ProtectedRoute   # Auth guard
├── uploads/                     # Stored PDFs (auto-created)
├── vectors/                     # FAISS indexes (auto-created)
└── research_assistant.db        # SQLite database (auto-created)
```

## Setup

### 1. Get an OpenRouter API Key
Sign up at https://openrouter.ai — free models available, no credit card needed.

### 2. Backend

```bash
cd backend

# Copy env file
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn main:app --reload --port 8000
```

The API docs will be at http://localhost:8000/docs

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | Your OpenRouter key | (required) |
| `SECRET_KEY` | JWT signing key | change-me-in-production |

## API Endpoints

```
POST /auth/signup        # Register
POST /auth/login         # Login → JWT token
GET  /auth/me            # Current user

POST /documents/upload   # Upload PDF (background processing)
GET  /documents/         # List your documents
GET  /documents/{id}/status  # Poll processing status
DELETE /documents/{id}   # Delete document + vectors

POST /chat/sessions      # Create chat session for a document
GET  /chat/sessions      # List your sessions
GET  /chat/sessions/{id} # Get session + messages
POST /chat/sessions/{id}/ask  # Ask a question (RAG)
DELETE /chat/sessions/{id}    # Delete session
```

## Notes

- SentenceTransformer model (`all-MiniLM-L6-v2`) is downloaded on first run (~90 MB, cached by HuggingFace)
- FAISS index is built per document after upload — polling the status endpoint until `"ready"`
- Top-5 chunks retrieved per query; configurable via `TOP_K_RESULTS` in `config.py`
- Conversation history (last 6 turns) is included in each LLM call for context continuity
