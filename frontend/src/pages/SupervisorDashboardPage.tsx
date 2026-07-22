import { useEffect, useState } from "react";
import { apiRequest } from "../api/client";
import EmptyState from "../components/EmptyState";
import { SupervisorDashboardTherapistRow } from "../types";

export default function SupervisorDashboardPage() {
  const [rows, setRows] = useState<SupervisorDashboardTherapistRow[] | null>(null);

  useEffect(() => {
    apiRequest<{ therapists: SupervisorDashboardTherapistRow[] }>("/clinic/supervisor-dashboard").then((data) =>
      setRows(data.therapists)
    );
  }, []);

  if (!rows) return <p className="text-neutralState">Carregando...</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-navy mb-2">Painel de Supervisão</h1>
      <p className="text-sm text-neutralState mb-6">
        Visão consolidada por equipe (Seção 29.4): percentual de sessões completas, adesão ao plano de
        tratamento e alertas automáticos de baixa adesão ou ausência de registro por terapeuta.
      </p>

      {rows.length === 0 ? (
        <EmptyState icon="👥" message="Nenhum profissional ativo na equipe." />
      ) : (
        <div className="bg-white rounded-card shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-xs text-neutralState uppercase">
                <th className="px-4 py-3">Terapeuta</th>
                <th className="px-4 py-3">Pacientes</th>
                <th className="px-4 py-3">Sessões completas</th>
                <th className="px-4 py-3">Faltas</th>
                <th className="px-4 py-3">% completude</th>
                <th className="px-4 py-3">Objetivos ativos</th>
                <th className="px-4 py-3">% adesão ao plano</th>
                <th className="px-4 py-3">Alertas</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.professional_id} className="border-b border-slate-50 last:border-0">
                  <td className="px-4 py-3 font-medium">{row.professional_name}</td>
                  <td className="px-4 py-3">{row.assigned_patients_count}</td>
                  <td className="px-4 py-3">{row.completed_sessions_count}</td>
                  <td className="px-4 py-3">{row.no_show_count}</td>
                  <td className="px-4 py-3">
                    {row.session_completion_pct === null ? "—" : `${row.session_completion_pct}%`}
                  </td>
                  <td className="px-4 py-3">{row.active_objectives_count}</td>
                  <td className="px-4 py-3">
                    {row.treatment_plan_adherence_pct === null ? "—" : `${row.treatment_plan_adherence_pct}%`}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {row.low_adherence_alert && (
                        <span className="text-[10px] uppercase font-semibold px-2 py-1 rounded-full bg-danger/10 text-danger">
                          Baixa adesão
                        </span>
                      )}
                      {row.no_recent_registration_alert && (
                        <span className="text-[10px] uppercase font-semibold px-2 py-1 rounded-full bg-warning/10 text-warning">
                          Sem registro recente
                        </span>
                      )}
                      {!row.low_adherence_alert && !row.no_recent_registration_alert && (
                        <span className="text-[10px] uppercase font-semibold px-2 py-1 rounded-full bg-success/10 text-success">
                          Em dia
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
