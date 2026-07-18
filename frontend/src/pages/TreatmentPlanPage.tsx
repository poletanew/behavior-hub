import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiRequest, ApiError } from "../api/client";
import { DuplicateCandidate, Objective, ObjectivePriority, ObjectiveStatus, Patient, TreatmentArea, TreatmentPlan } from "../types";

const AREA_LABELS: Record<TreatmentArea, string> = {
  psicologia: "Psicologia",
  aba: "ABA",
  fonoaudiologia: "Fonoaudiologia",
  terapia_ocupacional: "Terapia Ocupacional",
  psicopedagogia: "Psicopedagogia",
  fisioterapia: "Fisioterapia",
  nutricao: "Nutrição",
  outra: "Outra",
};

const STATUS_LABELS: Record<ObjectiveStatus, string> = {
  not_started: "Não iniciado",
  in_progress: "Em andamento",
  mastered: "Dominado",
  paused: "Pausado",
  discontinued: "Descontinuado",
};

const STATUS_COLORS: Record<ObjectiveStatus, string> = {
  not_started: "bg-slate-100 text-slate-600",
  in_progress: "bg-info/10 text-info",
  mastered: "bg-success/10 text-success",
  paused: "bg-warning/10 text-warning",
  discontinued: "bg-danger/10 text-danger",
};

const PRIORITY_LABELS: Record<ObjectivePriority, string> = { low: "Baixa", medium: "Média", high: "Alta" };

function ObjectiveCard({ objective, onChanged }: { objective: Objective; onChanged: () => void }) {
  const [expanded, setExpanded] = useState(false);

  async function updateStatus(status: ObjectiveStatus) {
    await apiRequest(`/objectives/${objective.id}`, { method: "PATCH", body: { status } });
    onChanged();
  }

  async function handleDelete() {
    if (!confirm("Excluir este objetivo? O histórico será mantido.")) return;
    await apiRequest(`/objectives/${objective.id}`, { method: "DELETE" });
    onChanged();
  }

  return (
    <div className="bg-white rounded-card shadow-sm p-4 mb-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-medium text-brand-navy">{objective.title}</div>
          <div className="text-xs text-neutralState mt-0.5">Prioridade: {PRIORITY_LABELS[objective.priority]}</div>
        </div>
        <span className={`text-[10px] uppercase font-semibold px-2 py-1 rounded-full ${STATUS_COLORS[objective.status]}`}>
          {STATUS_LABELS[objective.status]}
        </span>
      </div>

      <button onClick={() => setExpanded((v) => !v)} className="text-xs text-brand-blue underline mt-2">
        {expanded ? "Ocultar detalhes" : "Ver detalhes"}
      </button>

      {expanded && (
        <div className="mt-2 text-sm space-y-1 border-t border-slate-100 pt-2">
          {objective.description && <p>{objective.description}</p>}
          {objective.criteria && (
            <p>
              <span className="font-medium">Critério de domínio:</span> {objective.criteria}
            </p>
          )}
          {objective.strategies && (
            <p>
              <span className="font-medium">Estratégias:</span> {objective.strategies}
            </p>
          )}
          <div className="flex flex-wrap gap-2 pt-2">
            <select
              value={objective.status}
              onChange={(e) => updateStatus(e.target.value as ObjectiveStatus)}
              className="h-8 text-xs rounded-btn border border-slate-300 px-2"
            >
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <button onClick={handleDelete} className="h-8 text-xs text-danger px-2">
              Excluir
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function TreatmentPlanPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [plan, setPlan] = useState<TreatmentPlan | null>(null);
  const [areaFilter, setAreaFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [area, setArea] = useState<TreatmentArea>("aba");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [criteria, setCriteria] = useState("");
  const [strategies, setStrategies] = useState("");
  const [priority, setPriority] = useState<ObjectivePriority>("medium");
  const [duplicateCandidates, setDuplicateCandidates] = useState<DuplicateCandidate[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    if (!patientId) return;
    apiRequest<Patient>(`/patients/${patientId}`).then(setPatient);
    const params = new URLSearchParams();
    if (areaFilter) params.set("area", areaFilter);
    if (statusFilter) params.set("status", statusFilter);
    apiRequest<TreatmentPlan>(`/patients/${patientId}/treatment-plan?${params.toString()}`).then(setPlan);
  }

  useEffect(load, [patientId, areaFilter, statusFilter]);

  function resetForm() {
    setTitle("");
    setDescription("");
    setCriteria("");
    setStrategies("");
    setPriority("medium");
    setDuplicateCandidates(null);
    setError(null);
  }

  async function submitObjective(force: boolean) {
    try {
      await apiRequest(`/patients/${patientId}/treatment-plan/objectives`, {
        method: "POST",
        body: { area, title, description: description || null, criteria: criteria || null, strategies: strategies || null, priority, force },
      });
      setShowForm(false);
      resetForm();
      load();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        const detail = err.detail as { duplicate_candidates: DuplicateCandidate[] };
        setDuplicateCandidates(detail.duplicate_candidates);
      } else if (err instanceof ApiError && err.status === 403) {
        setError("Você não tem permissão para editar objetivos desta área.");
      } else {
        setError("Não foi possível salvar o objetivo.");
      }
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    await submitObjective(false);
  }

  const objectivesByArea: Record<string, Objective[]> = {};
  for (const objective of plan?.objectives || []) {
    objectivesByArea[objective.area] = objectivesByArea[objective.area] || [];
    objectivesByArea[objective.area].push(objective);
  }

  return (
    <div>
      <Link to={`/patients/${patientId}`} className="text-sm text-brand-blue underline mb-4 inline-block">
        ← Voltar para o paciente
      </Link>

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-brand-navy">Plano de Tratamento{patient ? ` — ${patient.name}` : ""}</h1>
        <button
          onClick={() => {
            resetForm();
            setShowForm((v) => !v);
          }}
          className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium"
        >
          + Novo objetivo
        </button>
      </div>

      <div className="flex flex-wrap gap-3 mb-6">
        <select value={areaFilter} onChange={(e) => setAreaFilter(e.target.value)} className="h-9 rounded-btn border border-slate-300 px-2 text-sm">
          <option value="">Todas as áreas</option>
          {Object.entries(AREA_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="h-9 rounded-btn border border-slate-300 px-2 text-sm">
          <option value="">Todos os status</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white rounded-card shadow-sm p-6 mb-6 space-y-4 max-w-xl">
          {duplicateCandidates && duplicateCandidates.length > 0 && (
            <div className="bg-warning/10 border border-warning rounded-card p-4 text-sm">
              <p className="font-medium mb-2">
                Um objetivo semelhante já foi adicionado. Deseja visualizar, mesclar ou continuar?
              </p>
              <ul className="space-y-1 mb-3">
                {duplicateCandidates.map((c) => (
                  <li key={c.id}>
                    "{c.title}" — área: {AREA_LABELS[c.area]} — similaridade: {Math.round(c.similarity * 100)}%
                  </li>
                ))}
              </ul>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => submitObjective(true)}
                  className="rounded-btn bg-warning text-white px-3 py-1.5 text-xs font-medium"
                >
                  Adicionar mesmo assim
                </button>
                <button
                  type="button"
                  onClick={() => setDuplicateCandidates(null)}
                  className="rounded-btn bg-white border border-slate-300 px-3 py-1.5 text-xs font-medium"
                >
                  Cancelar
                </button>
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-1">Área</label>
            <select value={area} onChange={(e) => setArea(e.target.value as TreatmentArea)} className="w-full h-10 rounded-btn border border-slate-300 px-3">
              {Object.entries(AREA_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Objetivo</label>
            <input required value={title} onChange={(e) => setTitle(e.target.value)} className="w-full h-10 rounded-btn border border-slate-300 px-3" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Descrição</label>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} className="w-full rounded-btn border border-slate-300 px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Critério de domínio</label>
            <input value={criteria} onChange={(e) => setCriteria(e.target.value)} className="w-full h-10 rounded-btn border border-slate-300 px-3" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Estratégias</label>
            <input value={strategies} onChange={(e) => setStrategies(e.target.value)} className="w-full h-10 rounded-btn border border-slate-300 px-3" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Prioridade</label>
            <select value={priority} onChange={(e) => setPriority(e.target.value as ObjectivePriority)} className="w-full h-10 rounded-btn border border-slate-300 px-3">
              {Object.entries(PRIORITY_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          {error && <p className="text-danger text-sm">{error}</p>}
          <div className="flex gap-3">
            <button type="submit" className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium">
              Salvar
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="rounded-btn bg-white border border-slate-300 px-4 py-2 text-sm font-medium">
              Cancelar
            </button>
          </div>
        </form>
      )}

      {plan && plan.objectives.length === 0 ? (
        <div className="bg-white rounded-card shadow-sm p-10 text-center text-neutralState">
          Nenhum objetivo cadastrado ainda para este paciente.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {Object.entries(objectivesByArea).map(([areaKey, objectives]) => (
            <div key={areaKey}>
              <h2 className="font-semibold text-brand-navy mb-2">{AREA_LABELS[areaKey as TreatmentArea]}</h2>
              {objectives.map((objective) => (
                <ObjectiveCard key={objective.id} objective={objective} onChanged={load} />
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
