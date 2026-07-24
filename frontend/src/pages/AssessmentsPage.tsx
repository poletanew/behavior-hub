import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiRequest } from "../api/client";
import EmptyState from "../components/EmptyState";
import AiDraftNote from "../components/AiDraftNote";
import {
  Assessment,
  AssessmentComparison,
  AssessmentProtocol,
  Patient,
  PlanDraftItem,
  ProtocolDefinition,
  SuggestedTrainingFolderEntry,
} from "../types";

const PROTOCOL_LABELS: Record<AssessmentProtocol, string> = {
  vb_mapp: "VB-MAPP",
  socially_savvy: "Socially Savvy Checklist",
};

const MAX_ASSESSMENTS_TO_COMPARE = 4;
const COMPARE_CHART_COLORS = ["#3B82F6", "#14B8A6", "#F59E0B", "#8B5CF6"];

function DomainChart({ assessment }: { assessment: Assessment }) {
  return (
    <div className="bg-white rounded-card shadow-card p-6 mb-6">
      <h2 className="font-semibold text-brand-navy mb-3">
        Gráfico de domínios — {new Date(assessment.applied_date).toLocaleDateString("pt-BR")}
      </h2>
      <ResponsiveContainer width="100%" height={Math.max(220, assessment.raw_scores.length * 28)}>
        <BarChart data={assessment.raw_scores} layout="vertical" margin={{ left: 24 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
          <YAxis type="category" dataKey="domain_label" width={220} tick={{ fontSize: 12 }} />
          <Tooltip formatter={(value: number) => `${value}%`} />
          <Bar dataKey="normalized_pct" name="Desempenho" fill="#14B8A6" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function AssessmentsPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [protocols, setProtocols] = useState<ProtocolDefinition[]>([]);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [protocol, setProtocol] = useState<AssessmentProtocol>("vb_mapp");
  const [appliedDate, setAppliedDate] = useState("");
  const [scores, setScores] = useState<Record<string, { raw_value: string; max_value: string }>>({});

  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [comparison, setComparison] = useState<AssessmentComparison | null>(null);

  const [chartAssessment, setChartAssessment] = useState<Assessment | null>(null);
  const [draftAssessment, setDraftAssessment] = useState<Assessment | null>(null);
  const [draftItems, setDraftItems] = useState<PlanDraftItem[]>([]);
  const [activating, setActivating] = useState(false);
  const [activateError, setActivateError] = useState<string | null>(null);
  const [activateSuccess, setActivateSuccess] = useState(false);

  const [folderAssessment, setFolderAssessment] = useState<Assessment | null>(null);
  const [suggestedFolder, setSuggestedFolder] = useState<SuggestedTrainingFolderEntry[] | null>(null);
  const [linkedTrainingIds, setLinkedTrainingIds] = useState<Set<string>>(new Set());

  function load() {
    if (!patientId) return;
    apiRequest<Patient>(`/patients/${patientId}`).then(setPatient);
    apiRequest<Assessment[]>(`/patients/${patientId}/assessments`).then(setAssessments);
  }

  useEffect(load, [patientId]);
  useEffect(() => {
    apiRequest<ProtocolDefinition[]>("/assessment-protocols").then(setProtocols);
  }, []);

  const activeProtocolDef = protocols.find((p) => p.protocol === protocol);
  const priorAssessmentsOfProtocol = assessments
    .filter((a) => a.protocol === protocol)
    .sort((a, b) => (a.applied_date < b.applied_date ? 1 : -1));

  function duplicatePriorAssessment() {
    const latest = priorAssessmentsOfProtocol[0];
    if (!latest) return;
    const prefilled: Record<string, { raw_value: string; max_value: string }> = {};
    for (const domain of latest.raw_scores) {
      prefilled[domain.domain_code] = { raw_value: String(domain.raw_value), max_value: String(domain.max_value) };
    }
    setScores(prefilled);
  }

  function toggleSelected(id: string) {
    setSelectedIds((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= MAX_ASSESSMENTS_TO_COMPARE) return prev;
      return [...prev, id];
    });
    setComparison(null);
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!activeProtocolDef) return;
    type DomainScoreInput = { domain_code: string; raw_value: number; max_value?: number };
    const domain_scores: DomainScoreInput[] = [];
    for (const d of activeProtocolDef.domains) {
      const entry = scores[d.domain_code];
      if (!entry || !entry.raw_value) continue;
      domain_scores.push({
        domain_code: d.domain_code,
        raw_value: Number(entry.raw_value),
        max_value: entry.max_value ? Number(entry.max_value) : undefined,
      });
    }

    try {
      const created = await apiRequest<Assessment>(`/patients/${patientId}/assessments`, {
        method: "POST",
        body: { protocol, applied_date: appliedDate, domain_scores },
      });
      setShowForm(false);
      setScores({});
      setAppliedDate("");
      load();
      setChartAssessment(created);
      if (created.ai_generated_plan_draft.length > 0) {
        openDraft(created);
      }
    } catch {
      setError("Não foi possível registrar a avaliação. Verifique a data (uma aplicação por dia por protocolo) e as pontuações.");
    }
  }

  async function handleCompare() {
    if (selectedIds.length < 2) return;
    const params = new URLSearchParams({ protocol });
    selectedIds.forEach((id) => params.append("assessment_ids", id));
    const data = await apiRequest<AssessmentComparison>(`/patients/${patientId}/assessments/compare?${params.toString()}`);
    setComparison(data);
  }

  function openDraft(a: Assessment) {
    setDraftAssessment(a);
    setDraftItems(a.ai_generated_plan_draft.map((item) => ({ ...item })));
    setActivateError(null);
    setActivateSuccess(false);
  }

  function updateDraftItem(index: number, field: keyof PlanDraftItem, value: string) {
    setDraftItems((prev) => prev.map((item, i) => (i === index ? { ...item, [field]: value } : item)));
  }

  async function openFolder(a: Assessment) {
    setFolderAssessment(a);
    setSuggestedFolder(null);
    const data = await apiRequest<SuggestedTrainingFolderEntry[]>(`/assessments/${a.id}/suggested-training-folder`);
    setSuggestedFolder(data);
  }

  async function linkSuggestedTraining(trainingId: string) {
    if (!patientId) return;
    await apiRequest(`/trainings/${trainingId}/link`, { method: "POST", body: { patient_id: patientId } });
    setLinkedTrainingIds((prev) => new Set(prev).add(trainingId));
  }

  async function handleActivateDraft() {
    if (!draftAssessment) return;
    setActivating(true);
    setActivateError(null);
    try {
      await apiRequest(`/assessments/${draftAssessment.id}/activate-plan-draft`, {
        method: "POST",
        body: { items: draftItems },
      });
      setActivateSuccess(true);
      load();
    } catch {
      setActivateError("Não foi possível ativar o plano. O rascunho desta avaliação já pode ter sido ativado.");
    } finally {
      setActivating(false);
    }
  }

  if (!patient) return <p className="text-neutralState">Carregando...</p>;

  const assessmentsOfProtocol = assessments.filter((a) => a.protocol === protocol);

  return (
    <div>
      <Link to={`/patients/${patientId}`} className="text-sm text-brand-blue underline mb-4 inline-block">
        ← Voltar para {patient.name}
      </Link>

      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold text-brand-navy">Avaliações Padronizadas</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium"
        >
          Nova avaliação
        </button>
      </div>
      <p className="text-sm text-neutralState mb-6">
        Seção 30 do PRD — protocolos-piloto VB-MAPP e Socially Savvy Checklist. O Behavior Hub apoia o registro e a
        visualização das pontuações; a aplicação e a interpretação clínica permanecem sob
        responsabilidade do profissional habilitado.
      </p>

      <div className="flex gap-2 mb-4">
        {protocols.map((p) => (
          <button
            key={p.protocol}
            onClick={() => {
              setProtocol(p.protocol);
              setSelectedIds([]);
              setComparison(null);
            }}
            className={`rounded-btn px-3 py-1.5 text-sm font-medium ${
              protocol === p.protocol ? "bg-brand-navy text-white" : "bg-white border border-slate-300"
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {showForm && activeProtocolDef && (
        <form onSubmit={handleCreate} className="bg-white rounded-card shadow-card p-6 mb-6 space-y-4">
          {priorAssessmentsOfProtocol.length > 0 && (
            <div className="bg-brand-grayLight rounded-btn p-3 flex items-center justify-between">
              <p className="text-xs text-neutralState">
                Já existe uma aplicação anterior de {PROTOCOL_LABELS[protocol]} para este paciente
                ({new Date(priorAssessmentsOfProtocol[0].applied_date).toLocaleDateString("pt-BR")}).
              </p>
              <button
                type="button"
                onClick={duplicatePriorAssessment}
                className="rounded-btn bg-white border border-slate-300 px-3 py-1.5 text-xs font-medium shrink-0 ml-3"
              >
                Duplicar avaliação anterior como ponto de partida
              </button>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium mb-1">Data de aplicação</label>
            <input
              type="date"
              required
              value={appliedDate}
              onChange={(e) => setAppliedDate(e.target.value)}
              className="h-10 rounded-btn border border-slate-300 px-3"
            />
          </div>
          <div className="max-h-80 overflow-y-auto border border-slate-200 rounded-btn divide-y">
            {activeProtocolDef.domains.map((domain) => (
              <div key={domain.domain_code} className="flex items-center gap-3 px-3 py-2 text-sm">
                <span className="flex-1">{domain.domain_label}</span>
                <input
                  type="number"
                  min={0}
                  placeholder="Pontuação"
                  value={scores[domain.domain_code]?.raw_value ?? ""}
                  onChange={(e) =>
                    setScores((prev) => ({
                      ...prev,
                      [domain.domain_code]: { ...prev[domain.domain_code], raw_value: e.target.value },
                    }))
                  }
                  className="w-24 h-8 rounded-btn border border-slate-300 px-2 text-sm"
                />
                <span className="text-neutralState text-xs">/</span>
                <input
                  type="number"
                  min={1}
                  placeholder={domain.max_value !== null ? String(domain.max_value) : "Máximo"}
                  value={scores[domain.domain_code]?.max_value ?? ""}
                  onChange={(e) =>
                    setScores((prev) => ({
                      ...prev,
                      [domain.domain_code]: { ...prev[domain.domain_code], max_value: e.target.value },
                    }))
                  }
                  className="w-20 h-8 rounded-btn border border-slate-300 px-2 text-sm"
                />
              </div>
            ))}
          </div>
          {error && <p className="text-danger text-sm">{error}</p>}
          <div className="flex gap-3">
            <button type="submit" className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium">
              Salvar avaliação
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-btn bg-white border border-slate-300 px-4 py-2 text-sm font-medium"
            >
              Cancelar
            </button>
          </div>
        </form>
      )}

      {assessmentsOfProtocol.length === 0 ? (
        <EmptyState icon="🧩" message={`Nenhuma avaliação ${PROTOCOL_LABELS[protocol]} registrada ainda.`} />
      ) : (
        <div className="bg-white rounded-card shadow-card divide-y divide-slate-100 mb-6">
          {assessmentsOfProtocol.map((a) => (
            <div key={a.id} className="flex items-center gap-3 px-4 py-3 text-sm hover:bg-slate-50">
              <input
                type="checkbox"
                checked={selectedIds.includes(a.id)}
                disabled={!selectedIds.includes(a.id) && selectedIds.length >= MAX_ASSESSMENTS_TO_COMPARE}
                onChange={() => toggleSelected(a.id)}
              />
              <span className="flex-1">{new Date(a.applied_date).toLocaleDateString("pt-BR")}</span>
              <span className="text-neutralState">{a.raw_scores.length} domínio(s)</span>
              <button
                onClick={() => setChartAssessment(chartAssessment?.id === a.id ? null : a)}
                className="text-brand-blue underline text-xs"
              >
                {chartAssessment?.id === a.id ? "Ocultar gráfico" : "Ver gráfico"}
              </button>
              <button onClick={() => openFolder(a)} className="text-brand-blue underline text-xs">
                Pasta de treinos sugerida
              </button>
              {a.ai_generated_plan_draft.length > 0 &&
                (a.plan_draft_activated_at ? (
                  <span className="text-[10px] uppercase font-semibold px-2 py-1 rounded-full bg-success/10 text-success">
                    Plano ativado
                  </span>
                ) : (
                  <button
                    onClick={() => openDraft(a)}
                    className="text-[10px] uppercase font-semibold px-2 py-1 rounded-full bg-brand-turquoise/10 text-brand-turquoise"
                  >
                    Rascunho de plano (IA)
                  </button>
                ))}
            </div>
          ))}
        </div>
      )}

      {chartAssessment && <DomainChart assessment={chartAssessment} />}

      {draftAssessment && (
        <div className="bg-white rounded-card shadow-card p-6 mb-6">
          <h2 className="font-semibold text-brand-navy mb-1">
            Rascunho de Plano de Tratamento — {new Date(draftAssessment.applied_date).toLocaleDateString("pt-BR")}
          </h2>
          <AiDraftNote />
          <p className="text-xs text-neutralState mb-4">
            Objetivos sugeridos a partir dos domínios de menor desempenho desta avaliação. Edite os
            campos livremente antes de ativar — nada é adicionado ao plano de tratamento do paciente
            até você confirmar.
          </p>
          <div className="space-y-4 mb-4">
            {draftItems.map((item, index) => (
              <div key={item.domain_code} className="border border-slate-200 rounded-btn p-4 space-y-2">
                <div className="text-xs text-neutralState">
                  Domínio: {item.domain_label} ({item.normalized_pct}%)
                </div>
                <input
                  value={item.title}
                  onChange={(e) => updateDraftItem(index, "title", e.target.value)}
                  className="w-full h-9 rounded-btn border border-slate-300 px-2 text-sm font-medium"
                />
                <textarea
                  value={item.description}
                  onChange={(e) => updateDraftItem(index, "description", e.target.value)}
                  className="w-full rounded-btn border border-slate-300 px-2 py-1.5 text-sm"
                />
                <input
                  value={item.criteria}
                  onChange={(e) => updateDraftItem(index, "criteria", e.target.value)}
                  placeholder="Critério de domínio"
                  className="w-full h-9 rounded-btn border border-slate-300 px-2 text-sm"
                />
                <input
                  value={item.strategies}
                  onChange={(e) => updateDraftItem(index, "strategies", e.target.value)}
                  placeholder="Estratégias"
                  className="w-full h-9 rounded-btn border border-slate-300 px-2 text-sm"
                />
              </div>
            ))}
          </div>
          {activateError && <p className="text-danger text-sm mb-2">{activateError}</p>}
          {activateSuccess ? (
            <p className="text-success text-sm font-medium">
              Plano ativado! Os objetivos já aparecem no Plano de Tratamento do paciente.
            </p>
          ) : (
            <div className="flex gap-3">
              <button
                onClick={handleActivateDraft}
                disabled={activating}
                className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium disabled:opacity-50"
              >
                {activating ? "Ativando..." : "Ativar Plano de Tratamento"}
              </button>
              <button
                onClick={() => setDraftAssessment(null)}
                className="rounded-btn bg-white border border-slate-300 px-4 py-2 text-sm font-medium"
              >
                Fechar
              </button>
            </div>
          )}
        </div>
      )}

      {folderAssessment && (
        <div className="bg-white rounded-card shadow-card p-6 mb-6">
          <div className="flex items-center justify-between mb-1">
            <h2 className="font-semibold text-brand-navy">
              Pasta de treinos sugerida — {new Date(folderAssessment.applied_date).toLocaleDateString("pt-BR")}
            </h2>
            <span className="text-[10px] uppercase font-semibold px-2 py-1 rounded-full bg-brand-turquoise/10 text-brand-turquoise">
              Sugestão automática — revise antes de vincular
            </span>
          </div>
          <p className="text-xs text-neutralState mb-4">
            Treinos da Biblioteca de Treino relevantes às áreas de menor pontuação desta avaliação
            (Addendum v3.0, RF-36). Nenhum vínculo é criado automaticamente — revise e clique em
            "Vincular" para cada treino desejado.
          </p>
          {!suggestedFolder ? (
            <p className="text-neutralState text-sm">Carregando...</p>
          ) : suggestedFolder.length === 0 ? (
            <p className="text-sm text-neutralState">Nenhuma área de baixa pontuação identificada nesta avaliação.</p>
          ) : (
            <div className="space-y-4 mb-4">
              {suggestedFolder.map((entry) => (
                <div key={entry.domain_code} className="border border-slate-200 rounded-btn p-4">
                  <div className="text-sm font-medium mb-2">
                    {entry.domain_label} ({entry.normalized_pct}%)
                  </div>
                  {entry.trainings.length === 0 ? (
                    <p className="text-xs text-neutralState">
                      Nenhum treino da Biblioteca encontrado para este domínio ainda.
                    </p>
                  ) : (
                    <ul className="space-y-2">
                      {entry.trainings.map((t) => (
                        <li key={t.training_id} className="flex items-center justify-between gap-3 text-sm">
                          <span>{t.title}</span>
                          {linkedTrainingIds.has(t.training_id) ? (
                            <span className="text-xs text-success font-medium shrink-0">Vinculado</span>
                          ) : (
                            <button
                              onClick={() => linkSuggestedTraining(t.training_id)}
                              className="rounded-btn bg-white border border-slate-300 px-3 py-1 text-xs font-medium shrink-0"
                            >
                              Vincular
                            </button>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          )}
          <button
            onClick={() => setFolderAssessment(null)}
            className="rounded-btn bg-white border border-slate-300 px-4 py-2 text-sm font-medium"
          >
            Fechar
          </button>
        </div>
      )}

      {assessmentsOfProtocol.length >= 2 && (
        <div className="mb-6">
          <button
            onClick={handleCompare}
            disabled={selectedIds.length < 2}
            className="rounded-btn bg-brand-blueLight text-white px-4 py-2 text-sm font-medium disabled:opacity-40"
          >
            Comparar selecionadas ({selectedIds.length})
          </button>
          <p className="text-xs text-neutralState mt-1">
            Selecione de 2 a {MAX_ASSESSMENTS_TO_COMPARE} avaliações do mesmo protocolo (Addendum v3.0, RF-33).
          </p>
        </div>
      )}

      {comparison && (
        <div className="bg-white rounded-card shadow-card p-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-brand-navy">
              Comparação de {comparison.applied_dates.length} avaliações:{" "}
              {new Date(comparison.applied_dates[0]).toLocaleDateString("pt-BR")} →{" "}
              {new Date(comparison.applied_dates[comparison.applied_dates.length - 1]).toLocaleDateString("pt-BR")}
            </h2>
            <span className="text-[10px] uppercase font-semibold px-2 py-1 rounded-full bg-warning/10 text-warning">
              Rascunho automático por regras — revise antes de aprovar
            </span>
          </div>

          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={comparison.domains.map((d) => ({ domain_label: d.domain_label, ...d.values_by_date }))}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis dataKey="domain_label" fontSize={9} />
              <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} fontSize={9} />
              <Tooltip formatter={(value: number) => `${value}%`} contentStyle={{ background: "#334155", color: "#fff", border: "none" }} />
              <Legend wrapperStyle={{ fontSize: 10 }} />
              {comparison.applied_dates.map((date, idx) => (
                <Line
                  key={date}
                  type="monotone"
                  dataKey={date}
                  name={new Date(date).toLocaleDateString("pt-BR")}
                  stroke={COMPARE_CHART_COLORS[idx % COMPARE_CHART_COLORS.length]}
                  strokeWidth={2}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>

          <table className="w-full text-sm my-4">
            <thead>
              <tr className="text-left text-xs text-neutralState uppercase border-b border-slate-100">
                <th className="py-2">Domínio</th>
                {comparison.applied_dates.map((date) => (
                  <th key={date} className="py-2">
                    {new Date(date).toLocaleDateString("pt-BR")}
                  </th>
                ))}
                <th className="py-2">Ganho absoluto</th>
                <th className="py-2">Ganho relativo</th>
              </tr>
            </thead>
            <tbody>
              {comparison.domains.map((d) => (
                <tr key={d.domain_code} className="border-b border-slate-50 last:border-0">
                  <td className="py-2">{d.domain_label}</td>
                  {comparison.applied_dates.map((date) => (
                    <td key={date} className="py-2">
                      {d.values_by_date[date]}%
                    </td>
                  ))}
                  <td className={`py-2 ${d.gain_absolute_pp > 0 ? "text-success" : d.gain_absolute_pp < 0 ? "text-danger" : ""}`}>
                    {d.gain_absolute_pp > 0 ? "+" : ""}
                    {d.gain_absolute_pp} p.p.
                  </td>
                  <td className="py-2">{d.gain_relative_pct === null ? "—" : `${d.gain_relative_pct}%`}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-sm text-neutralState">{comparison.interpretive_summary}</p>
        </div>
      )}
    </div>
  );
}
