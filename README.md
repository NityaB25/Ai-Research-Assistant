# AI Research Assistant

A full-stack production-ready Retrieval-Augmented Generation (RAG) platform for interacting with PDFs using semantic search, reranking, streaming LLM responses, persistent vector storage, and conversational memory.

---

# Live Architecture

```text
Frontend (Vercel)
        ↓
Backend API (Render)
        ↓
Supabase Postgres + Storage
        ↓
Remote Inference Server
(Local Laptop + Cloudflare Tunnel)
```

---

# Features

## Authentication

* JWT-based authentication
* Secure signup/login system
* Protected API routes
* Persistent user sessions

## PDF Processing

* Upload PDF documents
* Page-wise text extraction using PyMuPDF
* Semantic sentence-aware chunking
* Overlapping context chunks

## Retrieval-Augmented Generation (RAG)

* Semantic retrieval using FAISS
* Embedding generation via SentenceTransformers
* Cross-encoder reranking
* Context-aware answer generation
* Source citations with page references

## Conversational AI

* Streaming responses
* Multi-turn conversation memory
* Query rewriting for follow-up questions
* Automatic conversation summarization
* Context-aware retrieval

## Vector Search Pipeline

* Dense vector embeddings
* FAISS cosine similarity search
* Cross-encoder reranking
* Top-k semantic retrieval

## Persistence

* PostgreSQL database via Supabase
* Persistent vector storage
* Persistent PDF storage
* Stateless backend deployment

## Frontend Features

* Beautiful modern UI
* PDF viewer with page navigation
* Streaming chat interface
* Source highlighting
* Citation expansion
* Responsive layout

---

# Tech Stack

## Frontend

* React
* Vite
* Tailwind CSS
* Axios
* React Markdown
* React PDF
* Lucide React

## Backend

* FastAPI
* SQLAlchemy
* PostgreSQL
* JWT Authentication
* HTTPX
* FAISS

## AI / ML

* SentenceTransformers
* CrossEncoder reranking
* OpenRouter API
* Llama 3.3 8B

## Infrastructure

* Vercel
* Render
* Supabase
* Cloudflare Tunnel

---

# System Architecture

## 1. PDF Upload Flow

```text
User Uploads PDF
        ↓
FastAPI Backend
        ↓
PyMuPDF Text Extraction
        ↓
Sentence-aware Chunking
        ↓
Remote Embedding Server
        ↓
FAISS Index Creation
        ↓
Upload vectors to Supabase Storage
        ↓
Save metadata to PostgreSQL
```

---

## 2. Question Answering Flow

```text
User Question
        ↓
Conversation History Analysis
        ↓
Query Rewrite (if needed)
        ↓
FAISS Semantic Retrieval
        ↓
CrossEncoder Reranking
        ↓
Context Construction
        ↓
OpenRouter LLM Generation
        ↓
Streaming Response to Frontend
```

---

# Project Structure

```text
ai-research-assistant/
│
├── frontend/
│   ├── src/
│   ├── components/
│   ├── pages/
│   ├── api/
│   └── styles/
│
├── backend/
│   ├── routers/
│   ├── services/
│   ├── uploads/
│   ├── vectors/
│   ├── config.py
│   ├── database.py
│   └── main.py
│
├── inference_server/
│   ├── main.py
│   └── requirements.txt
│
└── README.md
```

---

# Retrieval Pipeline

## Embedding Model

```text
all-MiniLM-L6-v2
```

* Lightweight
* Fast inference
* 384-dimensional embeddings
* Good semantic retrieval performance

## Reranker Model

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

Used for:

* semantic reranking
* relevance refinement
* improved retrieval quality

---

# Query Rewriting System

The system automatically determines whether a user query depends on previous conversation context.

Example:

```text
User: Explain Fisher Discriminant Analysis.
User: What is its objective function?
```

The second query is rewritten into a standalone semantic query before retrieval.

---

# Conversation Memory

Long conversations are automatically summarized.

Benefits:

* reduced token usage
* persistent conversational context
* scalable chat history
* better long-session performance

---

# PDF Chunking Strategy

The system uses:

* sentence-aware chunking
* overlap-based context preservation
* semantic boundaries

Configuration:

```python
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
MIN_CHUNK_SIZE = 200
```

---

# Streaming Architecture

Streaming responses are implemented using:

* FastAPI StreamingResponse
* incremental token streaming
* OpenRouter streaming API
* frontend incremental rendering

---

# Database Schema

## Users

* authentication
* account management

## Documents

* PDF metadata
* vector references
* upload status

## Chat Sessions

* persistent conversations
* rolling summaries

## Chat Messages

* user/assistant messages
* citations
* timestamps

---

# Production Optimizations

## Why Remote Inference?

Render free tier has limited RAM.

Instead of loading transformers on Render:

* embeddings run on local inference server
* reranker runs remotely
* backend stays lightweight
* deployment remains stable

---

# Persistent Storage Design

## Supabase Storage

Used for:

* uploaded PDFs
* FAISS indices
* metadata pickle files

## Supabase PostgreSQL

Used for:

* users
* chat sessions
* document metadata
* messages

This makes the backend fully stateless.

---

# Environment Variables

## Backend

```env
SECRET_KEY=
OPENROUTER_API_KEY=
DATABASE_URL=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
INFERENCE_SERVER_URL=
```

## Frontend

```env
VITE_API_URL=
```

---

# Local Development

## Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Inference Server

```bash
cd inference_server
python -m venv venv
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001
```

---

## Cloudflare Tunnel

```bash
cloudflared tunnel --url http://localhost:8001
```

---

# Deployment

## Frontend Deployment

* Hosted on Vercel
* Automatic GitHub deployment

## Backend Deployment

* Hosted on Render
* Lightweight FastAPI deployment
* Uses Supabase persistence

## Database & Storage

* Supabase PostgreSQL
* Supabase Storage Buckets

---

# Key Engineering Challenges Solved

## 1. Render RAM Limits

Solved by:

* remote inference server
* lightweight backend architecture

## 2. Stateless Deployment

Solved using:

* Supabase Storage
* PostgreSQL persistence

## 3. Conversational Retrieval

Solved using:

* query rewriting
* rolling summaries
* contextual retrieval

## 4. Retrieval Quality

Solved using:

* semantic chunking
* cross-encoder reranking
* dense vector search

---

# Future Improvements

* Hybrid retrieval (BM25 + dense retrieval)
* OCR support for scanned PDFs
* Multi-document retrieval
* Citation highlighting inside PDFs
* Multi-query retrieval
* Agentic workflows
* Redis caching
* Docker deployment
* Kubernetes scaling
* SSE-based streaming architecture





---

# Author

Nitya Bhavsar

---


