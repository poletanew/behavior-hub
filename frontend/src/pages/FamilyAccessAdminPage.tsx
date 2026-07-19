import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiRequest, ApiError } from "../api/client";
import { FamilyAccess, FamilyMessage, Patient } from "../types";

const WHITELIST_FIELDS: { key: keyof FamilyAccess; label: string }[] = [
  { key: "can_view_evolution_charts", label: "Evolução (gráficos)" },
  { key: "can_view_upcoming_appointments", label: "Próximos agendamentos" },
  { key: "can_view_team_guidance", label: "Orientações da equipe" },
  { key: "can_view_home_materials", label: "Materiais para casa" },
  { key: "can_use_messaging", label: "Mensagens com a equipe" },
];

export default function FamilyAccessAdminPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [accesses, setAccesses] = useState<FamilyAccess[]>([]);
  const [messages, setMessages] = useState<FamilyMessage[]>([]);
  const [email, setEmail] = useState("");
  const [lastLink, setLastLink] = useState<string | null>(null);
  const [messageBody, setMessageBody] = useState("");
  const [error, setError] = useState<string | null>(null);

  function load() {
    if (!patientId) return;
    apiRequest<Patient>(`/patients/${patientId}`).then(setPatient);
    apiRequest<FamilyAccess[]>(`/patients/${patientId}/family-accesses`).then(setAccesses);
    apiRequest<FamilyMessage[]>(`/patients/${patientId}/family-messages`).then(setMessages);
  }

  useEffect(load, [patientId]);

  async function handleInvite(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const invitation = await apiRequest<{ raw_token: string }>("/invitations", {
        method: "POST",
        body: { email, role: "family", patient_id: patientId },
      });
      setLastLink(`${window.location.origin}/invitations/${invitation.raw_token}/accept`);
      setEmail("");
    } catch (err) {
      setError(err instanceof ApiError ? String(err.detail) : "Não foi possível gerar o convite.");
    }
  }

  async function toggleField(access: FamilyAccess, field: keyof FamilyAccess) {
    const updated = await apiRequest<FamilyAccess>(`/family-accesses/${access.id}`, {
      method: "PATCH",
      body: { [field]: !access[field] },
    });
    setAccesses((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
  }

  async function handleRevoke(accessId: string) {
    await apiRequest(`/family-accesses/${accessId}/revoke`, { method: "POST" });
    load();
  }

  async function handleSendMessage(e: FormEvent) {
    e.preventDefault();
    if (!messageBody.trim()) return;
    await apiRequest(`/patients/${patientId}/family-messages`, { method: "POST", body: { body: messageBody } });
    setMessageBody("");
    load();
  }

  if (!patient) return <p className="text-neutralState">Carregando...</p>;

  return (
    <div>
      <Link to={`/patients/${patientId}`} className="text-sm text-brand-blue underline mb-4 inline-block">
        ← Voltar para {patient.name}
      </Link>
      <h1 className="text-2xl font-bold text-brand-navy mb-1">Portal da Família</h1>
      <p className="text-sm text-neutralState mb-6">
        Cada categoria abaixo só é exibida ao responsável depois de liberada explicitamente aqui (whitelist,
        nunca por omissão).
      </p>

      <form onSubmit={handleInvite} className="bg-white rounded-card shadow-sm p-6 mb-6 flex gap-3 items-end max-w-lg">
        <div className="flex-1">
          <label className="block text-sm font-medium mb-1">E-mail do responsável</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full h-10 rounded-btn border border-slate-300 px-3"
          />
        </div>
        <button type="submit" className="h-10 rounded-btn bg-brand-turquoise text-white px-4 text-sm font-medium">
          Convidar
        </button>
      </form>
      {error && <p className="text-danger text-sm mb-4">{error}</p>}
      {lastLink && (
        <div className="bg-brand-grayLight border border-brand-blueLight rounded-card p-4 mb-6 text-sm break-all">
          Link do convite (válido por 7 dias): <a href={lastLink} className="text-brand-blue underline">{lastLink}</a>
        </div>
      )}

      <div className="space-y-4 mb-8">
        {accesses.map((access) => (
          <div key={access.id} className="bg-white rounded-card shadow-sm p-6">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="font-semibold text-brand-navy">{access.family_user_name}</div>
                <div className="text-xs text-neutralState">{access.family_user_email}</div>
              </div>
              {access.revoked_at ? (
                <span className="text-xs text-danger font-medium">Acesso revogado</span>
              ) : (
                <button onClick={() => handleRevoke(access.id)} className="text-danger text-sm hover:underline">
                  Revogar acesso
                </button>
              )}
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              {WHITELIST_FIELDS.map((field) => (
                <label key={field.key} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={Boolean(access[field.key])}
                    disabled={Boolean(access.revoked_at)}
                    onChange={() => toggleField(access, field.key)}
                  />
                  {field.label}
                </label>
              ))}
            </div>
          </div>
        ))}
        {accesses.length === 0 && (
          <div className="bg-white rounded-card shadow-sm p-6 text-center text-neutralState">
            Nenhum responsável convidado ainda.
          </div>
        )}
      </div>

      <div className="bg-white rounded-card shadow-sm p-6">
        <h2 className="font-semibold text-brand-navy mb-3">Mensagens com a família</h2>
        <div className="space-y-2 mb-4 max-h-64 overflow-y-auto">
          {messages.map((m) => (
            <div key={m.id} className="text-sm">
              <span className="font-medium">{m.sender_name}: </span>
              <span className="text-neutralState">{m.body}</span>
            </div>
          ))}
          {messages.length === 0 && <p className="text-sm text-neutralState">Nenhuma mensagem ainda.</p>}
        </div>
        <form onSubmit={handleSendMessage} className="flex gap-2">
          <input
            value={messageBody}
            onChange={(e) => setMessageBody(e.target.value)}
            placeholder="Escreva uma mensagem..."
            className="flex-1 h-10 rounded-btn border border-slate-300 px-3"
          />
          <button type="submit" className="h-10 rounded-btn bg-brand-turquoise text-white px-4 text-sm font-medium">
            Enviar
          </button>
        </form>
      </div>
    </div>
  );
}
