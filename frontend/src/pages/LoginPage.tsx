import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? "E-mail ou senha inválidos." : "Erro ao entrar. Tente novamente.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-navy to-brand-turquoise px-4">
      <div className="bg-white rounded-card shadow-lg p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold text-brand-navy mb-1">Behavior Hub</h1>
        <p className="text-sm text-neutralState mb-6">Entre com sua conta para continuar.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">E-mail</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full h-10 rounded-btn border border-slate-300 px-3 focus:outline-none focus:ring-2 focus:ring-brand-blueLight"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Senha</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full h-10 rounded-btn border border-slate-300 px-3 focus:outline-none focus:ring-2 focus:ring-brand-blueLight"
            />
          </div>
          {error && <p className="text-danger text-sm">{error}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="w-full h-10 rounded-btn bg-brand-turquoise text-white font-medium hover:opacity-90 disabled:opacity-50"
          >
            {submitting ? "Entrando..." : "Entrar"}
          </button>
        </form>

        <p className="text-sm text-center mt-6 text-neutralState">
          Não tem conta?{" "}
          <Link to="/register" className="text-brand-blue underline">
            Criar conta
          </Link>
        </p>
      </div>
    </div>
  );
}
