import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Loader2 } from "lucide-react";

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center text-ink-400">
      <Loader2 className="w-6 h-6 animate-spin mr-3" /> Loading...
    </div>
  );

  return user ? children : <Navigate to="/login" replace />;
}
