import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { chatAPI } from "../api/client";
import {
  ArrowLeft, Send, Loader2, BookOpen, FileText,
  ChevronDown, ChevronUp, Sparkles, User,
} from "lucide-react";

export default function ChatPage() {
  const { sessionId }           = useParams();
  const navigate                = useNavigate();
  const [session, setSession]   = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput]       = useState("");
  const [loading, setLoading]   = useState(true);
  const [asking, setAsking]     = useState(false);
  const [error, setError]       = useState("");
  const [expandedCitations, setExpandedCitations] = useState({});
  const bottomRef               = useRef();
  const textareaRef             = useRef();

  useEffect(() => {
    const load = async () => {
      try {
        const res = await chatAPI.getSession(sessionId);
        setSession(res.data);
        setMessages(res.data.messages || []);
      } catch {
        setError("Session not found");
      }
      setLoading(false);
    };
    load();
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, asking]);

  const handleSend = async () => {
    const q = input.trim();
    if (!q || asking) return;
    setInput("");
    setError("");
    setAsking(true);

    // Optimistic user message
    const optimisticUser = { id: Date.now(), role: "user", content: q, sources: [] };
    setMessages((prev) => [...prev, optimisticUser]);

    try {
      const res = await chatAPI.ask(sessionId, q);
      const { answer, citations } = res.data;
      const assistantMsg = {
        id: Date.now() + 1,
        role: "assistant",
        content: answer,
        sources: citations,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to get answer. Check your API key.");
      // Remove optimistic message on error
      setMessages((prev) => prev.filter((m) => m.id !== optimisticUser.id));
    } finally {
      setAsking(false);
      textareaRef.current?.focus();
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleCitations = (id) =>
    setExpandedCitations((prev) => ({ ...prev, [id]: !prev[id] }));

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center text-ink-400">
      <Loader2 className="w-6 h-6 animate-spin mr-3" /> Loading session...
    </div>
  );

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="glass border-b border-ink-700/50 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => navigate("/dashboard")}
            className="w-9 h-9 rounded-xl hover:bg-ink-700 flex items-center justify-center text-ink-300 hover:text-white transition-all">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-accent-500 to-accent-700 flex items-center justify-center shadow-md shadow-accent-500/25 flex-shrink-0">
            <BookOpen className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-white font-medium text-sm truncate">{session?.title || "Chat"}</p>
            <p className="text-ink-500 text-xs">Llama 3.3 8B · FAISS RAG</p>
          </div>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
          {messages.length === 0 && !asking && (
            <div className="text-center py-20 animate-fade-in">
              <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-accent-500/20 to-accent-700/20 border border-accent-500/20 flex items-center justify-center mb-4">
                <Sparkles className="w-8 h-8 text-accent-400" />
              </div>
              <h2 className="font-display text-2xl font-bold text-white mb-2">Ask anything</h2>
              <p className="text-ink-400 text-sm max-w-sm mx-auto">
                Ask questions about your document. The AI retrieves the most relevant passages and answers with page citations.
              </p>
              <div className="mt-6 flex flex-wrap gap-2 justify-center">
                {[
                  "Summarize this paper",
                  "What are the key findings?",
                  "Explain the methodology",
                  "What are the conclusions?",
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => { setInput(q); textareaRef.current?.focus(); }}
                    className="text-xs bg-ink-800 hover:bg-ink-700 border border-ink-600 hover:border-ink-500
                               text-ink-300 hover:text-white px-3 py-1.5 rounded-lg transition-all duration-200"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div key={msg.id || idx} className={`flex gap-3 animate-slide-up ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
              {/* Avatar */}
              <div className={`w-8 h-8 rounded-xl flex-shrink-0 flex items-center justify-center
                ${msg.role === "user"
                  ? "bg-accent-500/20 border border-accent-500/30"
                  : "bg-gradient-to-br from-accent-500 to-accent-700 shadow-md shadow-accent-500/25"}`}>
                {msg.role === "user"
                  ? <User className="w-4 h-4 text-accent-400" />
                  : <Sparkles className="w-4 h-4 text-white" />}
              </div>

              {/* Bubble */}
              <div className={`flex-1 max-w-[80%] ${msg.role === "user" ? "items-end" : "items-start"} flex flex-col gap-2`}>
                <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed
                  ${msg.role === "user"
                    ? "bg-accent-500/15 border border-accent-500/20 text-ink-100 rounded-tr-sm"
                    : "glass text-ink-100 rounded-tl-sm"}`}>
                  {msg.role === "user" ? (
                    <p>{msg.content}</p>
                  ) : (
                    <div className="prose-chat">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    </div>
                  )}
                </div>

                {/* Citations */}
                {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
                  <div className="w-full">
                    <button
                      onClick={() => toggleCitations(msg.id || idx)}
                      className="flex items-center gap-1.5 text-xs text-ink-400 hover:text-ink-200 transition-colors"
                    >
                      <FileText className="w-3.5 h-3.5" />
                      {msg.sources.length} source{msg.sources.length > 1 ? "s" : ""}
                      {expandedCitations[msg.id || idx]
                        ? <ChevronUp className="w-3.5 h-3.5" />
                        : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>

                    {expandedCitations[msg.id || idx] && (
                      <div className="mt-2 space-y-2 animate-fade-in">
                        {msg.sources.map((src, i) => (
                          <div key={i} className="bg-ink-900 border border-ink-700 rounded-xl p-3">
                            <div className="flex items-center gap-2 mb-1.5">
                              <span className="text-xs font-medium text-accent-400 bg-accent-500/10 border border-accent-500/20 px-2 py-0.5 rounded-full">
                                Page {src.page}
                              </span>
                              <span className="text-xs text-ink-500">score: {src.score}</span>
                            </div>
                            <p className="text-ink-400 text-xs leading-relaxed font-mono">{src.snippet}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Thinking indicator */}
          {asking && (
            <div className="flex gap-3 animate-fade-in">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-accent-500 to-accent-700 flex-shrink-0 flex items-center justify-center shadow-md shadow-accent-500/25">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div className="glass rounded-2xl rounded-tl-sm px-4 py-3">
                <div className="flex gap-1 items-center h-5">
                  {[0, 1, 2].map((i) => (
                    <span key={i} className="w-1.5 h-1.5 rounded-full bg-accent-400 animate-bounce"
                      style={{ animationDelay: `${i * 0.15}s` }} />
                  ))}
                  <span className="text-ink-400 text-xs ml-2">Retrieving and reasoning...</span>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-xl px-4 py-3 animate-fade-in max-w-lg mx-auto">
              {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input area */}
      <div className="glass border-t border-ink-700/50 sticky bottom-0">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex gap-3 items-end">
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Ask a question about your document... (Enter to send, Shift+Enter for newline)"
                rows={1}
                className="input-field resize-none overflow-hidden pr-4 py-3.5 leading-relaxed"
                style={{ minHeight: "52px", maxHeight: "160px" }}
                onInput={(e) => {
                  e.target.style.height = "auto";
                  e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px";
                }}
              />
            </div>
            <button
              onClick={handleSend}
              disabled={!input.trim() || asking}
              className="btn-primary h-[52px] w-[52px] flex items-center justify-center flex-shrink-0 rounded-xl"
            >
              {asking
                ? <Loader2 className="w-5 h-5 animate-spin" />
                : <Send className="w-5 h-5" />}
            </button>
          </div>
          <p className="text-ink-600 text-xs mt-2 text-center">
            Powered by Llama 3.3 · Embeddings via all-MiniLM-L6-v2 · FAISS vector search
          </p>
        </div>
      </div>
    </div>
  );
}
