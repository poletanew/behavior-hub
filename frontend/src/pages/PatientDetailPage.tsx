import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { apiRequest } from "../api/client";
import {
  ClinicalAlert,
  ClinicalSession,
  ClinicalSuggestion,
  Patient,
  SessionTemplate,
  Training,
  TrainingCategory,
  User,
} from "../types";
import { useAuth } from "../context/AuthContext";
import { professionalDisplayName } from "../utils/specialty";
import { schoolShiftLabel } from "../utils/patient";

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("pt-BR");
}

const ALERT_LABELS: Record<string, string> = {
  no_collection: "Sem coleta",
  regression: "Regressão",
  stagnation: "Estagnação",
  fading_candidate: "Candidato a fading",
};

const ALERT_COLORS: Record<string, string> = {
  no_collection: "bg-slate-200 text-neutralState",
  regression: "bg-danger/10 text-danger",
  stagnation: "bg-amber-100 text-amber-700",
  fading_candidate: "bg-success/10 text-success",
};

const SUGGESTION_LABELS: Record<string, string> = {
  new_program: "Novo programa",
  fading: "Fading",
  mastery_ready: "Objetivo dominado",
};

const SUGGESTION_COLORS: Record<string, string> = {
  new_program: "bg-brand-blueLight text-brand-navy",
  fading: "bg-success/10 text-success",
  mastery_ready: "bg-amber-100 text-amber-700",
};

export default function PatientDetailPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [patient, setPatient] = useState<Patient | null>(null);
  const [alerts, setAlerts] = useState<ClinicalAlert[]>([]);
  const [suggestions, setSuggestions] = useState<ClinicalSuggestion[]>([]);
  const [sessions, setSessions] = useState<ClinicalSession[]>([]);
  const [categories, setCategories] = useState<TrainingCategory[]>([]);
  const [trainings, setTrainings] = useState<Training[]>([]);
  const [templates, setTemplates] = useState<SessionTemplate[]>([]);
  const [professionals, setProfessionals] = useState<User[]>([]);
  const [showNewSession, setShowNewSession] = useState(false);
  const [professionalId, setProfessionalId] = useState("");
  const [occurredAt, setOccurredAt] = useState("");
  const [notes, setNotes] = useState("");
  const [selectedTrainingIds, setSelectedTrainingIds] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  function load() {
    if (!patientId) return;
    apiRequest<Patient>(`/patients/${patientId}`).then(setPatient);
    apiRequest<ClinicalAlert[]>(`/patients/${patientId}/alerts`).then(setAlerts);
    apiRequest<ClinicalSuggestion[]>(`/patients/${patientId}/suggestions`).then(setSuggestions);
    apiRequest<ClinicalSession[]>(`/sessions?patient_id=${patientId}`).then(setSessions);
    apiRequest<SessionTemplate[]>(`/session-templates?patient_id=${patientId}`).then(setTemplates);
  }

  useEffect(load, [patientId]);

  useEffect(() => {
    apiRequest<TrainingCategory[]>("/training-categories").then(setCategories);
    apiRequest<Training[]>("/trainings").then(setTrainings);
    apiRequest<User[]>("/professionals").then((list) => {
      setProfessionals(list.filter((p) => p.user_type !== "family"));
    });
  }, []);

  useEffect(() => {
    if (user?.id && !professionalId) setProfessionalId(user.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  function applyTemplate(templateId: string) {
    const template = templates.find((t) => t.id === templateId);
    if (template) {
      setSelectedTrainingIds(template.trainings.map((t) => t.training_id));
    }
  }

  async function handleCreateSession(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const session = await apiRequest<ClinicalSession>("/sessions", {
        method: "POST",
        body: {
          patient_id: patientId,
          professional_id: professionalId || user?.id,
          occurred_at: new Date(occurredAt).toISOString(),
          notes: notes || null,
          training_ids: selectedTrainingIds,
        },
      });
      navigate(`/sessions/${session.id}`);
    } catch {
      setError("Não foi possível criar o atendimento. Selecione o profissional responsável e ao menos um treino.");
    }
  }

  async function decideSuggestion(suggestionId: string, action: "approve" | "dismiss") {
    await apiRequest<ClinicalSuggestion>(`/suggestions/${suggestionId}/${action}`, { method: "POST" });
    setSuggestions((prev) => prev.filter((s) => s.id !== suggestionId));
  }

  function toggleTraining(id: string) {
    setSelectedTrainingIds((prev) => (prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]));
  }

  if (!patient) return <p className="text-neutralState">Carregando...</p>;

  return (
    <div>
      <Link to="/patients" className="text-sm text-brand-blue underline mb-4 inline-block">
        ← Voltar para Pacientes
      </Link>

      <div className="bg-white rounded-card shadow-sm p-6 mb-6">
        <h1 className="text-2xl font-bold text-brand-navy">{patient.name}</h1>
        <p className="text-neutralState text-sm mt-1">Nascimento: {patient.birth_date}</p>
        {patient.guardian_name && <p className="text-sm mt-1">Responsável: {patient.guardian_name}</p>}
        {patient.diagnosis && <p className="text-sm mt-1">Diagnóstico: {patient.diagnosis}</p>}
        {patient.phone && <p className="text-sm mt-1">Telefone: {patient.phone}</p>}
        {patient.address && <p className="text-sm mt-1">Endereço: {patient.address}</p>}
        {patient.school_name && (
          <p className="text-sm mt-1">
            Escola: {patient.school_name}
            {schoolShiftLabel(patient.school_shift) ? ` · ${schoolShiftLabel(patient.school_shift)}` : ""}
          </p>
        )}
        <div className="flex gap-4 mt-3 text-sm">
          <Link to={`/patients/${patientId}/treatment-plan`} className="text-brand-blue underline">
            Plano de Tratamento
          </Link>
          <Link to={`/patients/${patientId}/reports`} className="text-brand-blue underline">
            Reports
          </Link>
          <Link to={`/patients/${patientId}/timeline`} className="text-brand-blue underline">
            Timeline
          </Link>
          <Link to={`/patients/${patientId}/assessments`} className="text-brand-blue underline">
            Avaliações
          </Link>
          <Link to={`/patients/${patientId}/family-portal-admin`} className="text-brand-blue underline">
            Portal da Família
          </Link>
        </div>
      </div>

      {alerts.length > 0 && (
        <div className="bg-white rounded-card shadow-sm p-4 mb-6">
          <h2 className="font-semibold text-brand-navy mb-3">Alertas clínicos</h2>
          <div className="space-y-2">
            {alerts.map((alert) => (
              <div key={alert.id} className="flex items-start gap-3 text-sm">
                <span className={`shrink-0 rounded px-2 py-0.5 text-xs font-medium ${ALERT_COLORS[alert.alert_type]}`}>
                  {ALERT_LABELS[alert.alert_type] ?? alert.alert_type}
                </span>
                <div>
                  <span>{alert.message}</span>
                  <span className="text-neutralState"> — objetivo: {alert.objective_title}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {suggestions.filter((s) => s.status === "pending").length > 0 && (
        <div className="bg-white rounded-card shadow-sm p-4 mb-6">
          <h2 className="font-semibold text-brand-navy mb-1">Sugestões clínicas</h2>
          <p className="text-xs text-neutralState mb-3">
            Recomendações geradas por regra (Seção 29.1) — revise e aprove ou descarte; nenhuma ação é
            aplicada automaticamente.
          </p>
          <div className="space-y-3">
            {suggestions
              .filter((s) => s.status === "pending")
              .map((suggestion) => (
                <div key={suggestion.id} className="flex items-start justify-between gap-3 text-sm">
                  <div className="flex items-start gap-3">
                    <span
                      className={`shrink-0 rounded px-2 py-0.5 text-xs font-medium ${SUGGESTION_COLORS[suggestion.suggestion_type]}`}
                    >
                      {SUGGESTION_LABELS[suggestion.suggestion_type] ?? suggestion.suggestion_type}
                    </span>
                    <div>
                      <span>{suggestion.message}</span>
                      {suggestion.objective_title && (
                        <span className="text-neutralState"> — objetivo: {suggestion.objective_title}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <button
                      onClick={() => decideSuggestion(suggestion.id, "approve")}
                      className="rounded-btn bg-success text-white px-3 py-1 text-xs font-medium"
                    >
                      Aprovar
                    </button>
                    <button
                      onClick={() => decideSuggestion(suggestion.id, "dismiss")}
                      className="rounded-btn bg-white border border-slate-300 px-3 py-1 text-xs font-medium"
                    >
                      Descartar
                    </button>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-brand-navy">Histórico de sessões</h2>
        <button
          onClick={() => setShowNewSession((v) => !v)}
          className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium"
        >
          Novo Atendimento
        </button>
      </div>

      {showNewSession && (
        <form onSubmit={handleCreateSession} className="bg-white rounded-card shadow-sm p-6 mb-6 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Paciente</label>
            <div className="w-full h-10 rounded-btn border border-slate-200 bg-slate-50 px-3 flex items-center text-neutralState">
              {patient.name}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Profissional / Terapeuta responsável</label>
            <select
              required
              value={professionalId}
              onChange={(e) => setProfessionalId(e.target.value)}
              className="w-full h-10 rounded-btn border border-slate-300 px-3"
            >
              <option value="">Selecione...</option>
              {professionals.map((p) => (
                <option key={p.id} value={p.id}>
                  {professionalDisplayName(p)}
                </option>
              ))}
            </select>
          </div>
          {templates.length > 0 && (
            <div>
              <label className="block text-sm font-medium mb-1">Usar modelo de atendimento (opcional)</label>
              <select
                onChange={(e) => e.target.value && applyTemplate(e.target.value)}
                className="w-full h-10 rounded-btn border border-slate-300 px-3"
                defaultValue=""
              >
                <option value="">Selecionar treinos manualmente</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium mb-1">Data e hora</label>
            <input
              type="datetime-local"
              required
              value={occurredAt}
              onChange={(e) => setOccurredAt(e.target.value)}
              className="w-full h-10 rounded-btn border border-slate-300 px-3"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Observações</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full rounded-btn border border-slate-300 px-3 py-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Treinos do dia</label>
            <div className="max-h-64 overflow-y-auto border border-slate-200 rounded-btn divide-y">
              {categories.map((category) => (
                <div key={category.id}>
                  <div className="bg-slate-50 px-3 py-1 text-xs font-semibold uppercase text-neutralState">
                    {category.name}
                  </div>
                  {trainings
                    .filter((t) => t.category_id === category.id)
                    .map((training) => (
                      <label key={training.id} className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-slate-50">
                        <input
                          type="checkbox"
                          checked={selectedTrainingIds.includes(training.id)}
                          onChange={() => toggleTraining(training.id)}
                        />
                        {training.title}
                      </label>
                    ))}
                </div>
              ))}
            </div>
          </div>
          {error && <p className="text-danger text-sm">{error}</p>}
          <div className="flex gap-3">
            <button type="submit" className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium">
              Iniciar atendimento
            </button>
            <button
              type="button"
              onClick={() => setShowNewSession(false)}
              className="rounded-btn bg-white border border-slate-300 px-4 py-2 text-sm font-medium"
            >
              Cancelar
            </button>
          </div>
        </form>
      )}

      {sessions.length === 0 ? (
        <div className="bg-white rounded-card shadow-sm p-10 text-center text-neutralState">
          Nenhuma sessão registrada ainda.
        </div>
      ) : (
        <div className="bg-white rounded-card shadow-sm divide-y divide-slate-100">
          {sessions.map((session) => (
            <Link
              key={session.id}
              to={`/sessions/${session.id}`}
              className="flex justify-between px-4 py-3 hover:bg-slate-50"
            >
              <span>{formatDateTime(session.occurred_at)}</span>
              <span className="text-neutralState text-sm">{session.trainings.length} treino(s)</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
