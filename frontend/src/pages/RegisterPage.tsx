import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiRequest, ApiError } from "../api/client";

const SPECIALTIES = [
  { value: "psicologo_infantil", label: "Psicólogo infantil" },
  { value: "analista_comportamento_aba", label: "Analista do Comportamento / ABA" },
  { value: "fonoaudiologo", label: "Fonoaudiólogo" },
  { value: "terapeuta_ocupacional", label: "Terapeuta Ocupacional" },
  { value: "psicopedagogo", label: "Psicopedagogo" },
  { value: "fisioterapeuta_pediatrico", label: "Fisioterapeuta pediátrico" },
  { value: "neuropediatra", label: "Neuropediatra" },
  { value: "psiquiatra_infantil", label: "Psiquiatra infantil" },
  { value: "nutricionista_infantil", label: "Nutricionista infantil" },
  { value: "musicoterapeuta", label: "Musicoterapeuta" },
  { value: "arteterapeuta", label: "Arteterapeuta" },
  { value: "psicomotricista", label: "Psicomotricista" },
];

type AccountType = "clinic" | "individual";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [accountType, setAccountType] = useState<AccountType>("clinic");
  const [clinicName, setClinicName] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [specialty, setSpecialty] = useState(SPECIALTIES[0].value);
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (accountType === "clinic") {
        await apiRequest("/auth/register/clinic", {
          method: "POST",
          auth: false,
          body: { clinic_name: clinicName, admin_name: name, email, password, accept_terms: acceptTerms },
        });
      } else {
        await apiRequest("/auth/register/individual", {
          method: "POST",
          auth: false,
          body: { name, email, password, specialty, accept_terms: acceptTerms },
        });
      }
      navigate("/login");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("Este e-mail já está cadastrado.");
      } else {
        setError("Não foi possível concluir o cadastro. Verifique os dados informados.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-navy to-brand-turquoise px-4 py-10">
      <div className="bg-white rounded-card shadow-lg p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-brand-navy mb-1">Criar conta</h1>
        <p className="text-sm text-neutralState mb-6">
          Toda conta nova começa vazia — sem pacientes ou dados de demonstração.
        </p>

        <div className="flex mb-6 rounded-btn overflow-hidden border border-slate-300">
          <button
            type="button"
            onClick={() => setAccountType("clinic")}
            className={`flex-1 py-2 text-sm font-medium ${
              accountType === "clinic" ? "bg-brand-turquoise text-white" : "bg-white text-brand-graphite"
            }`}
          >
            Clínica
          </button>
          <button
            type="button"
            onClick={() => setAccountType("individual")}
            className={`flex-1 py-2 text-sm font-medium ${
              accountType === "individual" ? "bg-brand-turquoise text-white" : "bg-white text-brand-graphite"
            }`}
          >
            Profissional individual
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {accountType === "clinic" && (
            <div>
              <label className="block text-sm font-medium mb-1">Nome da clínica</label>
              <input
                required
                value={clinicName}
                onChange={(e) => setClinicName(e.target.value)}
                className="w-full h-10 rounded-btn border border-slate-300 px-3"
              />
            </div>
          )}
          <div>
            <label className="block text-sm font-medium mb-1">
              {accountType === "clinic" ? "Seu nome (administrador)" : "Nome completo"}
            </label>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full h-10 rounded-btn border border-slate-300 px-3"
            />
          </div>
          {accountType === "individual" && (
            <div>
              <label className="block text-sm font-medium mb-1">Especialidade</label>
              <select
                value={specialty}
                onChange={(e) => setSpecialty(e.target.value)}
                className="w-full h-10 rounded-btn border border-slate-300 px-3"
              >
                {SPECIALTIES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium mb-1">E-mail</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
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
            {submitting ? "Criando conta..." : "Criar conta"}
          </button>
        </form>

        <p className="text-sm text-center mt-6 text-neutralState">
          Já tem conta?{" "}
          <Link to="/login" className="text-brand-blue underline">
            Entrar
          </Link>
        </p>
      </div>
    </div>
  );
}
