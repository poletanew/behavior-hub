import { useEffect, useState } from "react";
import { apiRequest, ApiError } from "../api/client";
import { AuditLogEntry, Patient } from "../types";

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
  password_changed: "Senha alterada",
  user_name_updated: "Nome de usuário atualizado",
};

export default function AuditLogPage() {
  const [viewMode, setViewMode] = useState<"action" | "patient">("action");

  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [entityType, setEntityType] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [patients, setPatients] = useState<Patient[]>([]);
  const [patientSearch, setPatientSearch] = useState("");
  const [selectedPatientId, setSelectedPatientId] = useState("");
  const [patientTrail, setPatientTrail] = useState<AuditLogEntry[] | null>(null);
  const [patientTrailError, setPatientTrailError] = useState<string | null>(null);

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
  useEffect(() => {
    apiRequest<Patient[]>("/patients").then(setPatients);
  }, []);

  function openPatientTrail(patientId: string) {
    setSelectedPatientId(patientId);
    setPatientTrail(null);
    setPatientTrailError(null);
    apiRequest<AuditLogEntry[]>(`/audit-logs/patients/${patientId}`)
      .then(setPatientTrail)
      .catch(() => setPatientTrailError("Não foi possível carregar a auditoria deste paciente."));
  }

  const filteredPatients = patients.filter((p) => p.name.toLowerCase().includes(patientSearch.toLowerCase()));
  const selectedPatient = patients.find((p) => p.id === selectedPatientId);

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-navy mb-2">Log de Auditoria</h1>
      <p className="text-sm text-neutralState mb-6">
        Registro de ações relevantes na sua clínica, isolado por tenant.
      </p>

      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setViewMode("action")}
          className={`rounded-btn px-3 py-1.5 text-sm font-medium ${
            viewMode === "action" ? "bg-brand-navy text-white" : "bg-white border border-slate-300"
          }`}
        >
          Por ação
        </button>
        <button
          onClick={() => setViewMode("patient")}
          className={`rounded-btn px-3 py-1.5 text-sm font-medium ${
            viewMode === "patient" ? "bg-brand-navy text-white" : "bg-white border border-slate-300"
          }`}
        >
          Por paciente
        </button>
      </div>

      {viewMode === "action" ? (
        <>
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
        </>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-white rounded-card shadow-sm p-4">
            <input
              placeholder="Buscar paciente por nome..."
              value={patientSearch}
              onChange={(e) => setPatientSearch(e.target.value)}
              className="w-full h-9 rounded-btn border border-slate-300 px-2 text-sm mb-3"
            />
            <ul className="divide-y divide-slate-100 max-h-[60vh] overflow-y-auto">
              {filteredPatients.map((p) => (
                <li key={p.id}>
                  <button
                    onClick={() => openPatientTrail(p.id)}
                    className={`w-full text-left px-2 py-2 text-sm rounded-btn ${
                      selectedPatientId === p.id ? "bg-brand-turquoise/10" : "hover:bg-slate-50"
                    }`}
                  >
                    {p.name}
                  </button>
                </li>
              ))}
              {filteredPatients.length === 0 && (
                <li className="text-neutralState text-sm px-2 py-2">Nenhum paciente encontrado.</li>
              )}
            </ul>
          </div>

          <div className="lg:col-span-2 bg-white rounded-card shadow-sm p-4">
            {!selectedPatientId ? (
              <p className="text-neutralState text-sm">Selecione um paciente à esquerda para ver sua auditoria.</p>
            ) : patientTrailError ? (
              <p className="text-danger text-sm">{patientTrailError}</p>
            ) : patientTrail === null ? (
              <p className="text-neutralState text-sm">Carregando...</p>
            ) : (
              <>
                <h2 className="font-semibold text-brand-navy mb-3">
                  Auditoria de {selectedPatient?.name} — todas as ações de todos os profissionais
                </h2>
                {patientTrail.length === 0 ? (
                  <p className="text-neutralState text-sm">Nenhuma ação registrada para este paciente ainda.</p>
                ) : (
                  <ul className="space-y-2">
                    {patientTrail.map((entry) => (
                      <li key={entry.id} className="border-b border-slate-50 pb-2 text-sm">
                        <span className="text-neutralState">{new Date(entry.timestamp).toLocaleString("pt-BR")}</span>
                        {" — "}
                        <span className="font-medium">{entry.actor_name ?? "Sistema"}</span>
                        {": "}
                        <span>{ACTION_LABELS[entry.action] ?? entry.action}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
