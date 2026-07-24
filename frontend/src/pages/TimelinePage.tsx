import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiRequest } from "../api/client";
import EmptyState from "../components/EmptyState";
import { Patient, TimelineEntry } from "../types";

const EVENT_LABELS: Record<string, string> = {
  session_completed: "Atendimento",
  objective_created: "Objetivo criado",
  objective_updated: "Objetivo atualizado",
  objective_deleted: "Objetivo excluído",
  objective_restored: "Objetivo restaurado",
  objective_mastered: "Marco de evolução",
  patient_assignment_upserted: "Profissional vinculado",
  patient_assignment_removed: "Profissional desvinculado",
  report_generated: "Relatório gerado",
  assessment_applied: "Avaliação aplicada",
};

const EVENT_COLORS: Record<string, string> = {
  session_completed: "bg-brand-blueLight text-brand-navy",
  objective_created: "bg-brand-turquoise/20 text-brand-navy",
  objective_updated: "bg-slate-200 text-neutralState",
  objective_deleted: "bg-danger/10 text-danger",
  objective_restored: "bg-success/10 text-success",
  objective_mastered: "bg-amber-100 text-amber-700",
  patient_assignment_upserted: "bg-brand-blueLight text-brand-navy",
  patient_assignment_removed: "bg-slate-200 text-neutralState",
  report_generated: "bg-success/10 text-success",
  assessment_applied: "bg-brand-turquoise/20 text-brand-navy",
};

function sourceLink(patientId: string, entry: TimelineEntry): string | null {
  switch (entry.source_type) {
    case "session":
      return `/sessions/${entry.source_id}`;
    case "objective":
      return `/patients/${patientId}/treatment-plan`;
    case "report_summary":
      return `/patients/${patientId}/reports`;
    case "assessment":
      return `/patients/${patientId}/assessments`;
    default:
      return null;
  }
}

export default function TimelinePage() {
  const { patientId } = useParams<{ patientId: string }>();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [entries, setEntries] = useState<TimelineEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!patientId) return;
    apiRequest<Patient>(`/patients/${patientId}`).then(setPatient);
    apiRequest<TimelineEntry[]>(`/patients/${patientId}/timeline`)
      .then((data) => setEntries([...data].reverse()))
      .finally(() => setLoading(false));
  }, [patientId]);

  return (
    <div>
      <Link to={`/patients/${patientId}`} className="text-sm text-brand-blue underline mb-4 inline-block">
        ← Voltar para {patient?.name ?? "o paciente"}
      </Link>

      <h1 className="text-2xl font-bold text-brand-navy mb-2">Timeline Clínica</h1>
      <p className="text-sm text-neutralState mb-6">
        Linha do tempo única consolidando avaliações, alterações do plano de tratamento, atendimentos,
        mudanças de profissional e relatórios (Seção 29.2 do PRD), da mais recente para a mais antiga.
      </p>

      {loading ? (
        <p className="text-neutralState">Carregando...</p>
      ) : entries.length === 0 ? (
        <EmptyState icon="🕒" message="Nenhum evento registrado ainda para este paciente." />
      ) : (
        <div className="bg-white rounded-card shadow-card divide-y divide-slate-100">
          {entries.map((entry) => {
            const link = patientId ? sourceLink(patientId, entry) : null;
            const content = (
              <div className="flex items-start gap-3 px-4 py-3">
                <span
                  className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${EVENT_COLORS[entry.event_type] ?? "bg-slate-200 text-neutralState"}`}
                >
                  {EVENT_LABELS[entry.event_type] ?? entry.event_type}
                </span>
                <div className="flex-1">
                  <div className="text-sm">{entry.label}</div>
                  <div className="text-xs text-neutralState mt-0.5">
                    {new Date(entry.occurred_at).toLocaleString("pt-BR")}
                  </div>
                </div>
              </div>
            );
            return link ? (
              <Link key={entry.id} to={link} className="block hover:bg-slate-50">
                {content}
              </Link>
            ) : (
              <div key={entry.id}>{content}</div>
            );
          })}
        </div>
      )}
    </div>
  );
}
