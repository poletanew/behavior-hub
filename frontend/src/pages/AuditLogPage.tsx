import { useEffect, useState } from "react";
import { apiRequest, ApiError } from "../api/client";
import { AuditLogEntry } from "../types";

const ENTITY_TYPE_OPTIONS = [
  { value: "", label: "Todos os tipos" },
  { value: "patient", label: "Paciente" },
  { value: "patient_assignment", label: "Atribuição de profissional" },
  { value: "objective", label: "Objetivo" },
  { value: "resource", label: "Recurso" },
  { value: "session", label: "Atendimento" },
  { value: "trial", label: "Tentativa" },
  { value: "report_summary", label: "Resumo de relatório" },
  { value: "clinic", label: "Clínica" },
  { value: "invitation", label: "Convite" },
  { value: "clinic_permission_settings", label: "Configurações" },
  { value: "user", label: "Usuário" },
];

const ENTITY_TYPE_LABELS: Record<string, string> = Object.fromEntries(
  ENTITY_TYPE_OPTIONS.filter((opt) => opt.value).map((opt) => [opt.value, opt.label])
);

const ACTION_LABELS: Record<string, string> = {
  clinic_registered: "Clínica cadastrada",
  individual_registered: "Profissional individual cadastrado",
  invitation_created: "Convite gerado",
  invitation_accepted: "Convite aceito",
  invitation_revoked: "Convite revogado",
  clinic_permission_settings_updated: "Permissões da clínica atualizadas",
  patient_created: "Paciente cadastrado",
  patient_updated: "Paciente atualizado",
  patient_deleted: "Paciente excluído",
  patient_restored: "Paciente restaurado",
  patient_assignment_upserted: "Profissional atribuído ao paciente",
  patient_assignment_removed: "Atribuição de profissional removida",
  objective_created: "Objetivo criado",
  objective_updated: "Objetivo atualizado",
  objective_deleted: "Objetivo excluído",
  objective_restored: "Objetivo restaurado",
  objective_comment_added: "Comentário adicionado ao objetivo",
  objective_duplicate_alert_overridden: "Alerta de duplicidade ignorado",
  session_created: "Atendimento registrado",
  trial_created: "Tentativa registrada",
  trial_updated: "Tentativa atualizada",
  trial_deleted: "Tentativa excluída",
  resource_uploaded: "Recurso enviado",
  resource_deleted: "Recurso excluído",
  resource_restored: "Recurso restaurado",
  report_summary_generated: "Resumo de relatório gerado",
  report_summary_updated: "Resumo de relatório editado",
};

export default function AuditLogPage() {
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [entityType, setEntityType] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams();
    if (entityType) params.set("entity_type", entityType);
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    apiRequest<AuditLogEntry[]>(`/audit-logs?${params.toString()}`)
      .then(setEntries)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setError("Somente administradores da clínica têm acesso ao log de auditoria.");
        } else {
          setError("Não foi possível carregar o log de auditoria.");
        }
      })
      .finally(() => setLoading(false));
  }

  useEffect(load, [entityType, dateFrom, dateTo]);

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-navy mb-2">Log de Auditoria</h1>
      <p className="text-sm text-neutralState mb-6">
        Registro de ações relevantes na sua clínica, isolado por tenant.
      </p>

      <div className="bg-white rounded-card shadow-sm p-4 mb-6 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs font-medium mb-1">Tipo de entidade</label>
          <select
            value={entityType}
            onChange={(e) => setEntityType(e.target.value)}
            className="h-9 rounded-btn border border-slate-300 px-2 text-sm"
          >
            {ENTITY_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">De</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="h-9 rounded-btn border border-slate-300 px-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">Até</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="h-9 rounded-btn border border-slate-300 px-2 text-sm"
          />
        </div>
      </div>

      {error && <p className="text-danger text-sm mb-4">{error}</p>}

      {loading ? (
        <p className="text-neutralState">Carregando...</p>
      ) : entries.length === 0 && !error ? (
        <div className="bg-white rounded-card shadow-sm p-10 text-center text-neutralState">
          Nenhum registro de auditoria encontrado.
        </div>
      ) : !error ? (
        <div className="bg-white rounded-card shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-brand-navy text-white">
              <tr>
                <th className="text-left px-4 py-3">Data/hora</th>
                <th className="text-left px-4 py-3">Autor</th>
                <th className="text-left px-4 py-3">Ação</th>
                <th className="text-left px-4 py-3">Entidade</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry, idx) => (
                <tr key={entry.id} className={idx % 2 === 1 ? "bg-slate-50" : undefined}>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {new Date(entry.timestamp).toLocaleString("pt-BR")}
                  </td>
                  <td className="px-4 py-3">{entry.actor_name ?? "Sistema"}</td>
                  <td className="px-4 py-3">{ACTION_LABELS[entry.action] ?? entry.action}</td>
                  <td className="px-4 py-3">{ENTITY_TYPE_LABELS[entry.entity_type] ?? entry.entity_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
