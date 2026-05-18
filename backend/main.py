from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_tables
from routers.auth_router import router as auth_router
from routers.documents_router import router as docs_router
from routers.chat_router import router as chat_router

app = FastAPI(
    title="AI Research Assistant API",
    description="RAG-powered document Q&A with SentenceTransformers + FAISS + OpenRouter LLM",
    version="1.0.0",
)

# CORS - allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create DB tables on startup
@app.on_event("startup")
def startup():
    create_tables()
    print("✅ Database tables created")
    print("✅ AI Research Assistant API is running")


# Mount routers
app.include_router(auth_router)
app.include_router(docs_router)
app.include_router(chat_router)


@app.get("/")
def root():
    return {
        "message": "AI Research Assistant API",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
