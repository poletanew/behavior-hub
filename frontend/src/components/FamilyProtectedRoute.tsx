import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function FamilyProtectedRoute({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="flex items-center justify-center h-screen text-brand-graphite">Carregando...</div>;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  if (user.user_type !== "family") {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}
