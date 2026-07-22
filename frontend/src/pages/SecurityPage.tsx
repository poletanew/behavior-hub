import { FormEvent, useEffect, useState } from "react";
import { apiRequest, ApiError, setTokens } from "../api/client";
import { useAuth } from "../context/AuthContext";

interface TwoFactorStatus {
  is_2fa_enabled: boolean;
  required: boolean;
}

interface TwoFactorSetup {
  secret: string;
  otpauth_uri: string;
}

function ChangeNameForm() {
  const { user, refreshUser } = useAuth();
  const [name, setName] = useState(user?.name ?? "");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (user) setName(user.name);
  }, [user]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setSaving(true);
    try {
      await apiRequest("/auth/change-name", { method: "PATCH", body: { name } });
      await refreshUser();
      setMessage("Nome de usuário atualizado com sucesso.");
    } catch {
      setError("Não foi possível atualizar o nome. Tente novamente.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bg-white rounded-card shadow-sm p-6 max-w-xl space-y-3">
      <h2 className="font-semibold text-brand-navy">Nome de usuário</h2>
      {message && <p className="text-success text-sm">{message}</p>}
      {error && <p className="text-danger text-sm">{error}</p>}
      <form onSubmit={handleSubmit} className="flex gap-3 items-end max-w-md">
        <div className="flex-1">
          <label className="block text-sm font-medium mb-1">Nome de exibição</label>
          <input
            type="text"
            required
            minLength={2}
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full h-10 rounded-btn border border-slate-300 px-3"
          />
        </div>
        <button
          type="submit"
          disabled={saving}
          className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          Salvar
        </button>
      </form>
    </div>
  );
}

function ChangePasswordForm() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setSaving(true);
    try {
      const tokens = await apiRequest<{ access_token: string; refresh_token: string }>("/auth/change-password", {
        method: "POST",
        body: { current_password: currentPassword, new_password: newPassword },
      });
      // Encerra as demais sessões (token_version bumpado no backend), mas mantém
      // esta sessão ativa com o par de tokens novo devolvido pela API.
      setTokens(tokens.access_token, tokens.refresh_token);
      setCurrentPassword("");
      setNewPassword("");
      setMessage("Senha alterada com sucesso. As demais sessões ativas foram encerradas.");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Senha atual incorreta.");
      } else {
        setError("Não foi possível alterar a senha. Tente novamente.");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bg-white rounded-card shadow-sm p-6 max-w-xl space-y-3">
      <h2 className="font-semibold text-brand-navy">Senha</h2>
      <p className="text-xs text-neutralState">
        Trocar a senha encerra imediatamente as demais sessões ativas desta conta.
      </p>
      {message && <p className="text-success text-sm">{message}</p>}
      {error && <p className="text-danger text-sm">{error}</p>}
      <form onSubmit={handleSubmit} className="space-y-3 max-w-xs">
        <div>
          <label className="block text-sm font-medium mb-1">Senha atual</label>
          <input
            type="password"
            required
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className="w-full h-10 rounded-btn border border-slate-300 px-3"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Nova senha</label>
          <input
            type="password"
            required
            minLength={8}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="w-full h-10 rounded-btn border border-slate-300 px-3"
          />
        </div>
        <button
          type="submit"
          disabled={saving}
          className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          Alterar senha
        </button>
      </form>
    </div>
  );
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
        Dados de acesso e autenticação de dois fatores (2FA) com aplicativo autenticador.
      </p>

      <div className="space-y-6 mb-6">
        <ChangeNameForm />
        <ChangePasswordForm />
      </div>

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
