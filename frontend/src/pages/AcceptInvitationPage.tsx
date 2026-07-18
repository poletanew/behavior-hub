import { FormEvent, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { apiRequest, ApiError } from "../api/client";

export default function AcceptInvitationPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await apiRequest(`/invitations/${token}/accept`, {
        method: "POST",
        auth: false,
        body: { name, password, accept_terms: acceptTerms },
      });
      navigate("/login");
    } catch (err) {
      if (err instanceof ApiError && err.status === 410) {
        setError("Este convite expirou.");
      } else if (err instanceof ApiError && err.status === 404) {
        setError("Convite inválido ou já utilizado.");
      } else {
        setError("Não foi possível concluir o cadastro.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-navy to-brand-turquoise px-4">
      <div className="bg-white rounded-card shadow-lg p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold text-brand-navy mb-1">Aceitar convite</h1>
        <p className="text-sm text-neutralState mb-6">
          Complete seu cadastro para entrar vinculado à clínica que te convidou.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Nome completo</label>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full h-10 rounded-btn border border-slate-300 px-3"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Senha</label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full h-10 rounded-btn border border-slate-300 px-3"
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={acceptTerms} onChange={(e) => setAcceptTerms(e.target.checked)} />
            Li e aceito os termos de uso.
          </label>
          {error && <p className="text-danger text-sm">{error}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="w-full h-10 rounded-btn bg-brand-turquoise text-white font-medium hover:opacity-90 disabled:opacity-50"
          >
            {submitting ? "Enviando..." : "Concluir cadastro"}
          </button>
        </form>
      </div>
    </div>
  );
}
