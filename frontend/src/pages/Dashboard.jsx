import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { documentsAPI, chatAPI } from "../api/client";
import { useAuth } from "../context/AuthContext";
import {
  BookOpen,
  Upload,
  Trash2,
  MessageSquare,
  Loader2,
  FileText,
  CheckCircle,
  XCircle,
  Clock,
  LogOut,
  RefreshCw,
  Plus,
  History,
} from "lucide-react";

const STATUS_CONFIG = {
  ready: { icon: CheckCircle, color: "text-emerald-400", label: "Ready" },
  processing: { icon: Clock, color: "text-yellow-400", label: "Processing" },
  error: { icon: XCircle, color: "text-red-400", label: "Error" },
};

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [docs, setDocs] = useState([]);
  const [sessions, setSessions] = useState([]);

  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState("");

  const fileRef = useRef();
  const pollRef = useRef({});

  // ────────────────────────────────────────────────────────────────────────────
  // Fetch docs + sessions
  // ────────────────────────────────────────────────────────────────────────────

  const fetchData = async () => {
    try {
      const [docsRes, sessionsRes] = await Promise.all([
        documentsAPI.list(),
        chatAPI.listSessions(),
      ]);

      setDocs(docsRes.data);
      setSessions(sessionsRes.data);

      docsRes.data.forEach((d) => {
        if (d.status === "processing" && !pollRef.current[d.id]) {
          pollRef.current[d.id] = setInterval(
            () => pollStatus(d.id),
            3000
          );
        }
      });
    } catch (err) {
      console.error(err);
    }

    setLoading(false);
  };

  const pollStatus = async (id) => {
    try {
      const res = await documentsAPI.status(id);

      if (res.data.status !== "processing") {
        clearInterval(pollRef.current[id]);
        delete pollRef.current[id];
        fetchData();
      }
    } catch {}
  };

  useEffect(() => {
    fetchData();

    return () => {
      Object.values(pollRef.current).forEach(clearInterval);
    };
  }, []);

  // ────────────────────────────────────────────────────────────────────────────
  // Upload
  // ────────────────────────────────────────────────────────────────────────────

  const handleUpload = async (e) => {
    const file = e.target.files[0];

    if (!file) return;

    setUploading(true);
    setError("");
    setUploadProgress(0);

    try {
      await documentsAPI.upload(file, setUploadProgress);
      await fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
      fileRef.current.value = "";
    }
  };

  // ────────────────────────────────────────────────────────────────────────────
  // Delete doc
  // ────────────────────────────────────────────────────────────────────────────

  const handleDelete = async (id) => {
    if (!confirm("Delete this document and all its chats?")) return;

    try {
      await documentsAPI.delete(id);

      setDocs((d) => d.filter((doc) => doc.id !== id));

      setSessions((prev) =>
        prev.filter((s) => s.document_id !== id)
      );
    } catch (err) {
      setError(err.response?.data?.detail || "Delete failed");
    }
  };

  // ────────────────────────────────────────────────────────────────────────────
  // Create new chat
  // ────────────────────────────────────────────────────────────────────────────

  const createNewChat = async (doc) => {
    if (doc.status !== "ready") return;

    try {
      const res = await chatAPI.createSession(
        doc.id,
        `Chat: ${doc.original_name}`
      );

      navigate(`/chat/${res.data.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to open chat");
    }
  };

  // ────────────────────────────────────────────────────────────────────────────
  // Continue existing chat
  // ────────────────────────────────────────────────────────────────────────────

  const openExistingChat = (sessionId) => {
    navigate(`/chat/${sessionId}`);
  };

  // ────────────────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="glass border-b border-ink-700/50 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-accent-500 to-accent-700 flex items-center justify-center shadow-md shadow-accent-500/25">
              <BookOpen className="w-5 h-5 text-white" />
            </div>

            <span className="font-display text-xl font-bold text-white">
              Research AI
            </span>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-ink-400 text-sm hidden sm:block">
              Hello,{" "}
              <span className="text-white font-medium">
                {user?.username}
              </span>
            </span>

            <button
              onClick={logout}
              className="btn-ghost flex items-center gap-2 text-sm py-2 px-3"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-6xl mx-auto px-6 py-10">
        {/* Upload zone */}
        <div
          onClick={() =>
            !uploading && fileRef.current.click()
          }
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();

            const f = e.dataTransfer.files[0];

            if (f) {
              fileRef.current.files = e.dataTransfer.files;

              handleUpload({
                target: { files: [f] },
              });
            }
          }}
          className={`relative card border-2 border-dashed cursor-pointer transition-all duration-300 mb-10
            ${
              uploading
                ? "border-accent-500/50 bg-accent-500/5"
                : "border-ink-600 hover:border-accent-500/50 hover:bg-ink-800/50"
            }`}
        >
          <div className="flex flex-col items-center justify-center py-10 text-center">
            {uploading ? (
              <>
                <Loader2 className="w-10 h-10 text-accent-500 animate-spin mb-4" />

                <p className="text-white font-medium mb-2">
                  Uploading & Processing...
                </p>

                <div className="w-48 bg-ink-700 rounded-full h-1.5 mt-2">
                  <div
                    className="h-1.5 rounded-full bg-gradient-to-r from-accent-500 to-accent-400 transition-all duration-300"
                    style={{
                      width: `${uploadProgress}%`,
                    }}
                  />
                </div>

                <p className="text-ink-400 text-sm mt-2">
                  {uploadProgress}%
                </p>
              </>
            ) : (
              <>
                <div className="w-16 h-16 rounded-2xl bg-ink-800 border border-ink-600 flex items-center justify-center mb-4">
                  <Upload className="w-7 h-7 text-ink-300" />
                </div>

                <p className="text-white font-medium mb-1">
                  Drop a PDF here or click to upload
                </p>

                <p className="text-ink-400 text-sm">
                  Max 50 MB · PDF only
                </p>
              </>
            )}
          </div>

          <input
            ref={fileRef}
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleUpload}
            className="hidden"
          />
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-xl px-4 py-3 mb-6">
            {error}
          </div>
        )}

        {/* Title */}
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-display text-xl font-bold text-white">
            Your Library
          </h2>

          <button
            onClick={fetchData}
            className="text-ink-400 hover:text-ink-200 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {/* Loading */}
        {loading ? (
          <div className="flex items-center justify-center py-20 text-ink-400">
            <Loader2 className="w-6 h-6 animate-spin mr-3" />
            Loading documents...
          </div>
        ) : docs.length === 0 ? (
          <div className="text-center py-20 text-ink-500">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-40" />

            <p className="font-medium">No documents yet</p>

            <p className="text-sm mt-1">
              Upload a PDF to get started
            </p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {docs.map((doc) => {
              const cfg =
                STATUS_CONFIG[doc.status] ||
                STATUS_CONFIG.processing;

              const StatusIcon = cfg.icon;

              const docSessions = sessions.filter(
                (s) => s.document_id === doc.id
              );

              return (
                <div
                  key={doc.id}
                  className="card glass-hover flex flex-col gap-4"
                >
                  {/* Top */}
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-xl bg-ink-800 border border-ink-600 flex items-center justify-center flex-shrink-0">
                      <FileText className="w-5 h-5 text-ink-300" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <p
                        className="text-white font-medium text-sm leading-snug truncate"
                        title={doc.original_name}
                      >
                        {doc.original_name}
                      </p>

                      <p className="text-ink-500 text-xs mt-0.5">
                        {new Date(
                          doc.uploaded_at
                        ).toLocaleDateString()}
                      </p>
                    </div>
                  </div>

                  {/* Stats */}
                  {doc.status === "ready" && (
                    <div className="flex gap-4 text-xs text-ink-400">
                      <span>{doc.page_count} pages</span>
                      <span>{doc.chunk_count} chunks</span>
                    </div>
                  )}

                  {/* Previous chats */}
                  {docSessions.length > 0 && (
                    <div className="border-t border-ink-700 pt-3">
                      <div className="flex items-center gap-2 text-xs text-ink-400 mb-2">
                        <History className="w-3.5 h-3.5" />
                        Previous Chats
                      </div>

                      <div className="space-y-2 max-h-32 overflow-y-auto">
                        {docSessions.map((session) => (
                          <button
                            key={session.id}
                            onClick={() =>
                              openExistingChat(session.id)
                            }
                            className="w-full text-left px-3 py-2 rounded-lg bg-ink-800 hover:bg-ink-700 border border-ink-700 hover:border-ink-600 transition-all"
                          >
                            <p className="text-sm text-white truncate">
                              {session.title}
                            </p>

                            <p className="text-xs text-ink-500 mt-1">
                              {new Date(
                                session.created_at
                              ).toLocaleString()}
                            </p>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Footer */}
                  <div className="flex items-center justify-between mt-auto pt-2">
                    <div
                      className={`flex items-center gap-1.5 text-xs font-medium ${cfg.color}`}
                    >
                      {doc.status === "processing" ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <StatusIcon className="w-3.5 h-3.5" />
                      )}

                      {cfg.label}
                    </div>

                    <div className="flex gap-2">
                      {/* New chat */}
                      <button
                        onClick={() => createNewChat(doc)}
                        disabled={doc.status !== "ready"}
                        title="New chat"
                        className="w-8 h-8 rounded-lg bg-accent-500/10 hover:bg-accent-500/20 border border-accent-500/20
                                   flex items-center justify-center text-accent-400 transition-all duration-200
                                   disabled:opacity-30 disabled:cursor-not-allowed"
                      >
                        <Plus className="w-4 h-4" />
                      </button>

                      {/* Delete */}
                      <button
                        onClick={() =>
                          handleDelete(doc.id)
                        }
                        title="Delete"
                        className="w-8 h-8 rounded-lg bg-red-500/10 hover:bg-red-500/20 border border-red-500/20
                                   flex items-center justify-center text-red-400 transition-all duration-200"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}