import React, {
  useState,
  useEffect,
  useRef,
} from "react";
import { useParams, useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

import "katex/dist/katex.min.css";

pdfjs.GlobalWorkerOptions.workerSrc =
  new URL(
    "pdfjs-dist/build/pdf.worker.min.js",
    import.meta.url
  ).toString();
import { chatAPI } from "../api/client";

import {
  ArrowLeft,
  Send,
  Loader2,
  BookOpen,
  FileText,
  ChevronDown,
  ChevronUp,
  Sparkles,
  User,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";

export default function ChatPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();

  const [session, setSession] = useState(null);
  const [messages, setMessages] = useState([]);

  const [input, setInput] = useState("");

  const [loading, setLoading] = useState(true);
  const [asking, setAsking] = useState(false);

  const [error, setError] = useState("");

  const [showPreview, setShowPreview] = useState(true);

  const [expandedCitations, setExpandedCitations] =
    useState({});
  const [numPages, setNumPages] = useState(null);
  const [activePage, setActivePage] = useState(null);

  const bottomRef = useRef();
  const pageRefs = useRef({});
  const textareaRef = useRef();

  // ────────────────────────────────────────────────────────────────────────────

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

  // ────────────────────────────────────────────────────────────────────────────

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, asking]);

  // ────────────────────────────────────────────────────────────────────────────

 const handleSend = async () => {
  const q = input.trim();

  if (!q || asking) return;

  setInput("");
  setError("");
  setAsking(true);

  const optimisticUser = {
    id: Date.now(),
    role: "user",
    content: q,
    sources: [],
  };

  setMessages((prev) => [...prev, optimisticUser]);

  // Placeholder assistant message
  const assistantId = Date.now() + 1;

  const streamingAssistant = {
    id: assistantId,
    role: "assistant",
    content: "",
    sources: [],
  };

  setMessages((prev) => [
    ...prev,
    streamingAssistant,
  ]);

  try {

    await chatAPI.askStream(
      sessionId,
      q,
      (partialText,citations) => {

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? {
                  ...msg,
                  content: partialText,
                  sources: citations || [],
                }
              : msg
          )
        );

      }
    );

  } catch (err) {

    setError(
      err.message || "Failed to stream answer"
    );

    setMessages((prev) =>
      prev.filter(
        (m) =>
          m.id !== optimisticUser.id &&
          m.id !== assistantId
      )
    );

  } finally {

    setAsking(false);

    textareaRef.current?.focus();
  }
};
  // ────────────────────────────────────────────────────────────────────────────

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleCitations = (id) => {
    setExpandedCitations((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const scrollToPage = (pageNumber) => {

  setActivePage(pageNumber);

  const element = pageRefs.current[pageNumber];

  if (element) {
    element.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

};

  // ────────────────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-ink-400">
        <Loader2 className="w-6 h-6 animate-spin mr-3" />
        Loading session...
      </div>
    );
  }

  // ────────────────────────────────────────────────────────────────────────────

const token = localStorage.getItem("token");

const pdfUrl = session
  ? `${import.meta.env.VITE_API_URL}/documents/${session.document_id}/file?token=${token}`
  : null;


const renderContentWithCitations = (text) => {

  const parts = text.split(
    /(\[Page\s+\d+\])/g
  );

  return parts.map((part, idx) => {

    const match = part.match(
      /\[Page\s+(\d+)\]/
    );

    if (match) {

      const pageNumber = Number(match[1]);

      return (
        <button
          key={idx}
          onClick={() =>
            scrollToPage(pageNumber)
          }
          className="mx-1 text-accent-400 hover:text-accent-300 underline underline-offset-2 transition-colors"
        >
          {part}
        </button>
      );
    }

    return (
      <ReactMarkdown
        key={idx}
         remarkPlugins={[remarkGfm]}
        
      >
        {part}
      </ReactMarkdown>
    );
  });
};

  // ────────────────────────────────────────────────────────────────────────────

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Header */}
      <header className="glass border-b border-ink-700/50 z-10">
        <div className="px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => navigate("/dashboard")}
            className="w-9 h-9 rounded-xl hover:bg-ink-700 flex items-center justify-center text-ink-300 hover:text-white transition-all"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>

          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-accent-500 to-accent-700 flex items-center justify-center shadow-md shadow-accent-500/25">
            <BookOpen className="w-5 h-5 text-white" />
          </div>

          <div className="flex-1 min-w-0">
            <p className="text-white font-medium text-sm truncate">
              {session?.title || "Chat"}
            </p>

            <p className="text-ink-500 text-xs">
              Llama 3.3 8B · FAISS RAG
            </p>
          </div>

          <button
            onClick={() =>
              setShowPreview((prev) => !prev)
            }
            className="w-9 h-9 rounded-xl hover:bg-ink-700 flex items-center justify-center text-ink-300 hover:text-white transition-all"
            title={
              showPreview
                ? "Hide PDF Preview"
                : "Show PDF Preview"
            }
          >
            {showPreview ? (
              <PanelLeftClose className="w-5 h-5" />
            ) : (
              <PanelLeftOpen className="w-5 h-5" />
            )}
          </button>
        </div>
      </header>

      {/* Main split layout */}
      <div className="flex-1 flex overflow-hidden">
            {/* PDF Preview */}
{showPreview && (
  <div className="w-1/2 border-r border-ink-700 bg-ink-950 hidden lg:block overflow-y-auto">
    {pdfUrl ? (
      <div className="p-4 flex flex-col items-center">
       <Document
  file={pdfUrl}
  onLoadSuccess={({ numPages }) =>
    setNumPages(numPages)
  }
  loading={
    <div className="text-ink-400 mt-10">
      Loading PDF...
    </div>
  }
  error={
    <div className="text-red-400 mt-10">
      Failed to load PDF
    </div>
  }
>
  {numPages &&
    Array.from(
      { length: numPages },
      (_, index) => (
          <div
  key={`page_${index + 1}`}
  ref={(el) =>
    (pageRefs.current[index + 1] = el)
  }
  className={`mb-4 shadow-2xl border-2 rounded-lg transition-all ${
    activePage === index + 1
      ? "border-accent-400 shadow-accent-500/30"
      : "border-transparent"
  }`}
>
          <Page
            pageNumber={index + 1}
            width={550}
            renderTextLayer={true}
            renderAnnotationLayer={true}
          />
        </div>
      )
    )}
</Document>
      </div>
    ) : (
      <div className="h-full flex items-center justify-center text-ink-500">
        PDF unavailable
      </div>
    )}
  </div>
)}
        

        {/* Chat Section */}
        <div
          className={`flex flex-col ${
            showPreview
              ? "w-full lg:w-1/2"
              : "w-full"
          }`}
        >
          {/* Messages */}
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
              {messages.length === 0 && !asking && (
                <div className="text-center py-20">
                  <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-accent-500/20 to-accent-700/20 border border-accent-500/20 flex items-center justify-center mb-4">
                    <Sparkles className="w-8 h-8 text-accent-400" />
                  </div>

                  <h2 className="font-display text-2xl font-bold text-white mb-2">
                    Ask anything
                  </h2>

                  <p className="text-ink-400 text-sm max-w-sm mx-auto">
                    Ask questions about your document.
                  </p>
                </div>
              )}

              {/* Messages */}
              {messages.map((msg, idx) => (
                <div
                  key={msg.id || idx}
                  className={`flex gap-3 ${
                    msg.role === "user"
                      ? "flex-row-reverse"
                      : ""
                  }`}
                >
                  {/* Avatar */}
                  <div
                    className={`w-8 h-8 rounded-xl flex-shrink-0 flex items-center justify-center
                    ${
                      msg.role === "user"
                        ? "bg-accent-500/20 border border-accent-500/30"
                        : "bg-gradient-to-br from-accent-500 to-accent-700"
                    }`}
                  >
                    {msg.role === "user" ? (
                      <User className="w-4 h-4 text-accent-400" />
                    ) : (
                      <Sparkles className="w-4 h-4 text-white" />
                    )}
                  </div>

                  {/* Bubble */}
                  <div
                    className={`flex-1 max-w-[85%] flex flex-col gap-2 ${
                      msg.role === "user"
                        ? "items-end"
                        : "items-start"
                    }`}
                  >
                    <div
                      className={`rounded-2xl px-4 py-3 text-sm leading-relaxed
                      ${
                        msg.role === "user"
                          ? "bg-accent-500/15 border border-accent-500/20 text-ink-100 rounded-tr-sm"
                          : "glass text-ink-100 rounded-tl-sm"
                      }`}
                    >
                      {msg.role === "user" ? (
                        <p>{msg.content}</p>
                      ) : (
                        <div className="prose-chat">
                         {renderContentWithCitations(
  msg.content
)}
                        </div>
                      )}
                    </div>

                    {/* Citations */}
                    {msg.role === "assistant" &&
                      msg.sources &&
                      msg.sources.length > 0 && (
                        <div className="w-full">
                          <button
                            onClick={() =>
                              toggleCitations(
                                msg.id || idx
                              )
                            }
                            className="flex items-center gap-1.5 text-xs text-ink-400 hover:text-ink-200 transition-colors"
                          >
                            <FileText className="w-3.5 h-3.5" />

                            {msg.sources.length} source
                            {msg.sources.length > 1
                              ? "s"
                              : ""}

                            {expandedCitations[
                              msg.id || idx
                            ] ? (
                              <ChevronUp className="w-3.5 h-3.5" />
                            ) : (
                              <ChevronDown className="w-3.5 h-3.5" />
                            )}
                          </button>

                          {expandedCitations[
                            msg.id || idx
                          ] && (
                            <div className="mt-2 space-y-2">
                              {msg.sources.map(
                                (src, i) => (
                                  <div
                                    key={i}
                                    onClick={() => scrollToPage(src.page)}
                                    className="bg-ink-900 border border-ink-700 rounded-xl p-3 cursor-pointer hover:border-accent-500/40 hover:bg-ink-800 transition-all"
                                  >
                                    <div className="flex items-center gap-2 mb-1.5">
                                      <span className="text-xs font-medium text-accent-400 bg-accent-500/10 border border-accent-500/20 px-2 py-0.5 rounded-full">
                                        Page {src.page}
                                      </span>
                                    </div>

                                    <p className="text-ink-400 text-xs leading-relaxed font-mono">
                                      {src.snippet}
                                    </p>
                                  </div>
                                )
                              )}
                            </div>
                          )}
                        </div>
                      )}
                  </div>
                </div>
              ))}

              {/* Thinking */}
              {asking && messages[messages.length - 1]?.role !== "assistant" && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-accent-500 to-accent-700 flex items-center justify-center">
                    <Sparkles className="w-4 h-4 text-white" />
                  </div>

                  <div className="glass rounded-2xl rounded-tl-sm px-4 py-3">
                    <div className="flex gap-1 items-center h-5">
                      {[0, 1, 2].map((i) => (
                        <span
                          key={i}
                          className="w-1.5 h-1.5 rounded-full bg-accent-400 animate-bounce"
                          style={{
                            animationDelay: `${
                              i * 0.15
                            }s`,
                          }}
                        />
                      ))}

                      <span className="text-ink-400 text-xs ml-2">
                        Retrieving and reasoning...
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {error && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-xl px-4 py-3">
                  {error}
                </div>
              )}

              <div ref={bottomRef} />
            </div>
          </div>

          {/* Input */}
          <div className="glass border-t border-ink-700/50">
            <div className="px-4 py-4">
              <div className="flex gap-3 items-end">
                <div className="flex-1 relative">
                  <textarea
                    ref={textareaRef}
                    value={input}
                    onChange={(e) =>
                      setInput(e.target.value)
                    }
                    onKeyDown={handleKey}
                    placeholder="Ask a question about your document..."
                    rows={1}
                    className="input-field resize-none overflow-hidden pr-4 py-3.5 leading-relaxed"
                    style={{
                      minHeight: "52px",
                      maxHeight: "160px",
                    }}
                    onInput={(e) => {
                      e.target.style.height = "auto";

                      e.target.style.height =
                        Math.min(
                          e.target.scrollHeight,
                          160
                        ) + "px";
                    }}
                  />
                </div>

                <button
                  onClick={handleSend}
                  disabled={!input.trim() || asking}
                  className="btn-primary h-[52px] w-[52px] flex items-center justify-center rounded-xl"
                >
                  {asking ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Send className="w-5 h-5" />
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}