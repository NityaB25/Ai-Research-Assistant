import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Redirect to login on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// ── Auth ─────────────────────────────────────────────────────────────────────
export const authAPI = {
  signup: (data) => api.post("/auth/signup", data),
  login: (data) => api.post("/auth/login", data),
  me: () => api.get("/auth/me"),
};

// ── Documents ────────────────────────────────────────────────────────────────
export const documentsAPI = {
  upload: (file, onProgress) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/documents/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e) => onProgress && onProgress(Math.round((e.loaded * 100) / e.total)),
    });
  },
  list: () => api.get("/documents/"),
  status: (id) => api.get(`/documents/${id}/status`),
  delete: (id) => api.delete(`/documents/${id}`),
};

// ── Chat ─────────────────────────────────────────────────────────────────────
export const chatAPI = {
  createSession: (documentId, title) =>
    api.post("/chat/sessions", { document_id: documentId, title }),
  listSessions: () => api.get("/chat/sessions"),
  getSession: (id) => api.get(`/chat/sessions/${id}`),
  deleteSession: (id) => api.delete(`/chat/sessions/${id}`),
  ask: (sessionId, question, topK = 5) =>
    api.post(`/chat/sessions/${sessionId}/ask`, { question, top_k: topK }),



  askStream: async (sessionId, question, onChunk) => {
  const token = localStorage.getItem("token");

  const response = await fetch(
      `${import.meta.env.VITE_API_URL}/chat/sessions/${sessionId}/ask-stream`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        Accept: "text/event-stream",
      },
      body: JSON.stringify({
        question,
        top_k: 5,
      }),
    }
  );

  if (!response.ok) {
    throw new Error("Streaming request failed");
  }

  const reader = response.body.getReader();

  const decoder = new TextDecoder();

  let fullText = "";

  while (true) {

  const { done, value } = await reader.read();

  if (done) break;

  const chunk = decoder.decode(value);

  fullText += chunk;

  const sourceMarker = "__SOURCES__";

  if (fullText.includes(sourceMarker)) {

    const parts = fullText.split(sourceMarker);

    const cleanText = parts[0];

    const citations = JSON.parse(parts[1]);

    onChunk(cleanText, citations);

  } else {

    onChunk(fullText, []);

  }
}

  return fullText;
},
};

export default api;
