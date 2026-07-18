import { FormEvent, useEffect, useState } from "react";
import { apiRequest, ApiError } from "../api/client";

interface TwoFactorStatus {
  is_2fa_enabled: boolean;
  required: boolean;
}

interface TwoFactorSetup {
  secret: string;
  otpauth_uri: string;
}

export default function SecurityPage() {
  const [status, setStatus] = useState<TwoFactorStatus | null>(null);
  const [setup, setSetup] = useState<TwoFactorSetup | null>(null);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [showDisableForm, setShowDisableForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  function load() {
    apiRequest<TwoFactorStatus>("/auth/2fa/status").then(setStatus);
  }

  useEffect(load, []);

  async function handleStartSetup() {
    setError(null);
    setMessage(null);
    const data = await apiRequest<TwoFactorSetup>("/auth/2fa/setup", { method: "POST" });
    setSetup(data);
  }

  async function handleEnable(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiRequest("/auth/2fa/enable", { method: "POST", body: { code } });
      setSetup(null);
      setCode("");
      setMessage("Autenticação de dois fatores ativada com sucesso.");
      load();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Código inválido. Verifique o horário do seu dispositivo e tente novamente.");
      } else {
        setError("Não foi possível ativar. Tente novamente.");
      }
    }
  }

  async function handleDisable(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiRequest("/auth/2fa/disable", { method: "POST", body: { password } });
      setShowDisableForm(false);
      setPassword("");
      setMessage("Autenticação de dois fatores desativada.");
      load();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Senha incorreta.");
      } else {
        setError("Não foi possível desativar. Tente novamente.");
      }
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-navy mb-2">Segurança</h1>
      <p className="text-sm text-neutralState mb-6">
        Autenticação de dois fatores (2FA) com aplicativo autenticador (Seção 32.8 do PRD).
      </p>

      {status?.required && (
        <div className="bg-danger/10 border border-danger rounded-card p-4 mb-6 text-sm text-danger">
          O plano Enterprise da sua clínica exige autenticação de dois fatores para administradores.
          Ative abaixo para continuar em conformidade.
        </div>
      )}
      {message && <p className="text-success text-sm mb-4">{message}</p>}
      {error && <p className="text-danger text-sm mb-4">{error}</p>}

      <div className="bg-white rounded-card shadow-sm p-6 max-w-xl space-y-4">
        {!status ? (
          <p className="text-neutralState">Carregando...</p>
        ) : status.is_2fa_enabled ? (
          <>
            <p className="text-sm">
              <span className="font-medium text-success">Ativada.</span> Sua conta pede um código do
              aplicativo autenticador a cada login.
            </p>
            {!showDisableForm ? (
              <button
                onClick={() => setShowDisableForm(true)}
                className="rounded-btn border border-danger text-danger px-4 py-2 text-sm font-medium"
              >
                Desativar 2FA
              </button>
            ) : (
              <form onSubmit={handleDisable} className="space-y-3 max-w-xs">
                <div>
                  <label className="block text-sm font-medium mb-1">Confirme sua senha</label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full h-10 rounded-btn border border-slate-300 px-3"
                  />
                </div>
                <div className="flex gap-3">
                  <button type="submit" className="rounded-btn bg-danger text-white px-4 py-2 text-sm font-medium">
                    Confirmar desativação
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowDisableForm(false)}
                    className="rounded-btn bg-white border border-slate-300 px-4 py-2 text-sm font-medium"
                  >
                    Cancelar
                  </button>
                </div>
              </form>
            )}
          </>
        ) : !setup ? (
          <>
            <p className="text-sm text-neutralState">
              Sua conta ainda não usa autenticação de dois fatores.
            </p>
            <button
              onClick={handleStartSetup}
              className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium"
            >
              Ativar autenticação de dois fatores
            </button>
          </>
        ) : (
          <form onSubmit={handleEnable} className="space-y-4">
            <div>
              <p className="text-sm font-medium mb-1">1. Adicione esta chave no seu aplicativo autenticador</p>
              <p className="text-xs text-neutralState mb-2">
                (Google Authenticator, Authy, 1Password, etc. — use a opção "inserir chave manualmente")
              </p>
              <code className="block bg-slate-100 rounded-btn px-3 py-2 text-sm tracking-widest break-all">
                {setup.secret}
              </code>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">2. Digite o código gerado pelo aplicativo</label>
              <input
                type="text"
                inputMode="numeric"
                required
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="w-full h-10 rounded-btn border border-slate-300 px-3 tracking-widest"
              />
            </div>
            <div className="flex gap-3">
              <button type="submit" className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium">
                Confirmar e ativar
              </button>
              <button
                type="button"
                onClick={() => {
                  setSetup(null);
                  setCode("");
                }}
                className="rounded-btn bg-white border border-slate-300 px-4 py-2 text-sm font-medium"
              >
                Cancelar
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
