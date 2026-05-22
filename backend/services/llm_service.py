"""
LLM Service
- Sends retrieved chunks as context to OpenRouter (meta-llama/llama-3.3-8b-instruct:free)
- Returns streamed or full response with page citations
"""
import json
import httpx
from typing import List, Dict, Any
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, DEFAULT_LLM_MODEL
from typing import AsyncGenerator

SYSTEM_PROMPT = """You are an expert AI Research Assistant. Your job is to help users understand research papers and documents.

Rules:
1. Answer ONLY based on the provided context chunks from the document.
2. If the context does not contain enough information, say so clearly.
3. Always cite the page numbers when referencing information (e.g. "According to page 3...").
4. Be concise, accurate, and helpful.
5. Use markdown formatting for clarity (bullet points, bold, code blocks if needed).
6. When summarizing, cover the key points thoroughly.
7. For mathematical notation, ALWAYS use proper LaTeX formatting:
- Use $...$ for inline equations
- Use $$...$$ for block equations
- Never write raw latex without math delimiters

"""

SUMMARY_PROMPT = """
You are a conversation memory summarizer.

Your task:
- Summarize the important discussion points from the conversation.
- Preserve technical details, user goals, decisions, and important context.
- Keep the summary concise but information-dense.
- Do NOT include filler conversation.
- The summary will be used as memory for future conversations.
"""


def build_context_block(retrieved_chunks: List[Dict[str, Any]]) -> str:
    """Format retrieved chunks into a readable context string for the LLM."""
    blocks = []
    for chunk in retrieved_chunks:
        blocks.append(
            f"[Page {chunk['page']} | Score: {chunk['score']:.2f}]\n{chunk['text']}"
        )
    return "\n\n---\n\n".join(blocks)


def build_messages(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    history: List[Dict[str, str]] | None = None,
    summary: str | None = None,
) -> List[Dict[str, str]]:
    """Build the messages array for the chat completion API."""

    context = build_context_block(retrieved_chunks)

    user_message = f"""Here are the most relevant excerpts from the document:

{context}

---

User Question: {query}

Please answer based on the excerpts above. Cite page numbers where relevant."""

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    # Add rolling memory summary
    if summary:
        messages.append({
            "role": "system",
            "content": f"""Conversation Memory Summary:

{summary}

Use this as background memory from earlier parts of the conversation.""",
        })

    # Add recent conversation history
    if history:
        for msg in history[-6:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

    # Final user query with retrieved context
    messages.append({
        "role": "user",
        "content": user_message,
    })

    return messages


async def generate_answer(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    history: List[Dict[str, str]] | None = None,
    summary: str | None = None,
    model: str = DEFAULT_LLM_MODEL,
) -> str:
    """Call OpenRouter and return the full answer text."""
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set. Add it to your .env file.")

    messages = build_messages(query, retrieved_chunks, history,summary)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",   # Required by OpenRouter
        "X-Title": "AI Research Assistant",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,       # Lower = more factual
        "max_tokens": 1024,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )
        try:
             response.raise_for_status()
        except httpx.HTTPStatusError as e:
            print("OPENROUTER ERROR:", e.response.text)

            if e.response.status_code == 429:
                return "OpenRouter free-tier rate limit reached. Please wait a minute and try again."

            return f"LLM API error: {e.response.status_code}"
        data = response.json()
      

    return data["choices"][0]["message"]["content"].strip()

async def stream_answer(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    history: List[Dict[str, str]] | None = None,
    summary: str | None = None,
    model: str = DEFAULT_LLM_MODEL,
) -> AsyncGenerator[str, None]:

    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set.")

    messages = build_messages(
        query,
        retrieved_chunks,
        history,
        summary,
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "AI Research Assistant",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1024,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=None) as client:

        async with client.stream(
            "POST",
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        ) as response:

            response.raise_for_status()

            async for line in response.aiter_lines():

                if not line:
                    continue

                if line.startswith("data: "):

                    data_str = line[len("data: "):]

                    if data_str == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)

                        delta = (
                            data["choices"][0]
                            .get("delta", {})
                            .get("content", "")
                        )

                        if delta:
                            yield delta

                    except Exception:
                        continue

async def summarize_conversation(
    messages: List[Dict[str, str]],
    existing_summary: str | None = None,
) -> str:
    """
    Compress older conversation history into a rolling summary.
    """

    convo_text = "\n".join(
        [f"{m['role'].upper()}: {m['content']}" for m in messages]
    )

    prompt = f"""
Existing Summary:
{existing_summary or "None"}

Conversation To Summarize:
{convo_text}

Create an updated rolling summary.
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "AI Research Assistant",
    }

    payload = {
        "model": DEFAULT_LLM_MODEL,
        "messages": [
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 512,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )

        response.raise_for_status()

        data = response.json()

    return data["choices"][0]["message"]["content"].strip()


async def should_rewrite_query(
    query: str,
    history: List[Dict[str, str]],
    summary: str | None = None,
) -> bool:
    """
    Determine whether the query depends on previous conversation context.
    """

    if not history and not summary:
        return False

    recent_history = "\n".join(
        [f"{m['role']}: {m['content']}" for m in history[-6:]]
    )

    prompt = f"""
Determine whether the user's latest query depends on previous conversation context.

Respond ONLY with:
YES
or
NO

Conversation Summary:
{summary or "None"}

Recent Conversation:
{recent_history}

Latest Query:
{query}
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "AI Research Assistant",
    }

    payload = {
        "model": DEFAULT_LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a query dependency classifier."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0,
        "max_tokens": 5,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )

        response.raise_for_status()

        data = response.json()

    result = data["choices"][0]["message"]["content"].strip().upper()

    return result == "YES"


async def rewrite_query(
    query: str,
    history: List[Dict[str, str]],
    summary: str | None = None,
) -> str:
    """
    Rewrite context-dependent queries into standalone queries.
    """

    recent_history = "\n".join(
        [f"{m['role']}: {m['content']}" for m in history[-6:]]
    )

    prompt = f"""
Rewrite the user's latest query into a standalone query.

Rules:
- Preserve the original meaning
- Do not add extra information
- Keep it concise
- Return ONLY the rewritten query

Conversation Summary:
{summary or "None"}

Recent Conversation:
{recent_history}

Latest Query:
{query}
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "AI Research Assistant",
    }

    payload = {
        "model": DEFAULT_LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a query rewriting assistant."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": 128,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )

        response.raise_for_status()

        data = response.json()

    return data["choices"][0]["message"]["content"].strip()

def extract_citations(retrieved_chunks: List[Dict[str, Any]]) -> List[Dict]:
    """Build a clean list of citations to attach to the message."""
    seen_pages = set()
    citations = []
    for chunk in retrieved_chunks:
        page = chunk["page"]
        if page not in seen_pages:
            seen_pages.add(page)
            citations.append({
                "page": page,
                "snippet": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                "score": round(chunk["score"], 3),
            })
    return citations
