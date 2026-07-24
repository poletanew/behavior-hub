import { FormEvent, useEffect, useState } from "react";
import { apiRequest, ApiError } from "../api/client";
import { SPECIALTIES, specialtyLabel } from "../utils/specialty";

interface Invitation {
  id: string;
  email: string;
  specialty: string | null;
  role: string;
  status: string;
  expires_at: string;
  created_at: string;
}

interface InvitationCreated extends Invitation {
  raw_token: string;
}

const ROLE_LABELS: Record<string, string> = {
  professional: "Profissional",
  supervisor: "Supervisor",
  at: "Auxiliar Terapêutico (AT)",
};

export default function InvitationsPage() {
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("professional");
  const [specialty, setSpecialty] = useState("");
  const [lastLink, setLastLink] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    apiRequest<Invitation[]>("/invitations").then(setInvitations);
  }

  useEffect(load, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const invitation = await apiRequest<InvitationCreated>("/invitations", {
        method: "POST",
        body: { email, role, specialty: role !== "at" && specialty ? specialty : null },
      });
      const link = `${window.location.origin}/invitations/${invitation.raw_token}/accept`;
      setLastLink(link);
      setEmail("");
      setSpecialty("");
      load();
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("Você não tem permissão para gerar convites.");
      } else {
        setError("Não foi possível gerar o convite.");
      }
    }
  }

  async function handleRevoke(id: string) {
    await apiRequest(`/invitations/${id}/revoke`, { method: "POST" });
    load();
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-navy mb-6">Profissionais — Convites</h1>

      <form onSubmit={handleCreate} className="bg-white rounded-card shadow-card p-6 mb-6 flex gap-3 items-end max-w-lg">
        <div className="flex-1">
          <label className="block text-sm font-medium mb-1">E-mail do profissional</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full h-10 rounded-btn border border-slate-300 px-3"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Papel</label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="h-10 rounded-btn border border-slate-300 px-3 text-sm"
          >
            <option value="professional">Profissional</option>
            <option value="supervisor">Supervisor</option>
            <option value="at">Auxiliar Terapêutico (AT)</option>
          </select>
        </div>
        {role !== "at" && (
          <div>
            <label className="block text-sm font-medium mb-1">Especialidade (opcional)</label>
            <select
              value={specialty}
              onChange={(e) => setSpecialty(e.target.value)}
              className="h-10 rounded-btn border border-slate-300 px-3 text-sm"
            >
              <option value="">Não especificada</option>
              {SPECIALTIES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
        )}
        <button type="submit" className="h-10 rounded-btn bg-brand-turquoise text-white px-4 text-sm font-medium">
          Gerar convite
        </button>
      </form>
      {error && <p className="text-danger text-sm mb-4">{error}</p>}
      {lastLink && (
        <div className="bg-brand-grayLight border border-brand-blueLight rounded-card p-4 mb-6 text-sm break-all">
          Link do convite (válido por 7 dias): <a href={lastLink} className="text-brand-blue underline">{lastLink}</a>
        </div>
      )}

      <div className="bg-white rounded-card shadow-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-brand-navy text-white">
            <tr>
              <th className="text-left px-4 py-3">E-mail</th>
              <th className="text-left px-4 py-3">Papel</th>
              <th className="text-left px-4 py-3">Especialidade</th>
              <th className="text-left px-4 py-3">Status</th>
              <th className="text-left px-4 py-3">Expira em</th>
              <th className="text-right px-4 py-3">Ações</th>
            </tr>
          </thead>
          <tbody>
            {invitations.map((inv, idx) => (
              <tr key={inv.id} className={idx % 2 === 1 ? "bg-slate-50" : undefined}>
                <td className="px-4 py-3">{inv.email}</td>
                <td className="px-4 py-3">{ROLE_LABELS[inv.role] ?? inv.role}</td>
                <td className="px-4 py-3">{specialtyLabel(inv.specialty) ?? "—"}</td>
                <td className="px-4 py-3 capitalize">{inv.status}</td>
                <td className="px-4 py-3">{new Date(inv.expires_at).toLocaleDateString("pt-BR")}</td>
                <td className="px-4 py-3 text-right">
                  {inv.status === "pending" && (
                    <button onClick={() => handleRevoke(inv.id)} className="text-danger hover:underline">
                      Revogar
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {invitations.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-neutralState">
                  Nenhum convite gerado ainda.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
