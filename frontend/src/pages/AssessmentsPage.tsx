import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiRequest } from "../api/client";
import {
  Assessment,
  AssessmentComparison,
  AssessmentProtocol,
  Patient,
  ProtocolDefinition,
} from "../types";

const PROTOCOL_LABELS: Record<AssessmentProtocol, string> = {
  vb_mapp: "VB-MAPP",
  ablls_r: "ABLLS-R",
};

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

  function toggleSelected(id: string) {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
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
      await apiRequest(`/patients/${patientId}/assessments`, {
        method: "POST",
        body: { protocol, applied_date: appliedDate, domain_scores },
      });
      setShowForm(false);
      setScores({});
      setAppliedDate("");
      load();
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
        Seção 30 do PRD — protocolos-piloto VB-MAPP e ABLLS-R. O Behavior Hub apoia o registro e a
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
        <form onSubmit={handleCreate} className="bg-white rounded-card shadow-sm p-6 mb-6 space-y-4">
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
        <div className="bg-white rounded-card shadow-sm p-10 text-center text-neutralState">
          Nenhuma avaliação {PROTOCOL_LABELS[protocol]} registrada ainda.
        </div>
      ) : (
        <div className="bg-white rounded-card shadow-sm divide-y divide-slate-100 mb-6">
          {assessmentsOfProtocol.map((a) => (
            <label key={a.id} className="flex items-center gap-3 px-4 py-3 text-sm hover:bg-slate-50">
              <input type="checkbox" checked={selectedIds.includes(a.id)} onChange={() => toggleSelected(a.id)} />
              <span className="flex-1">{new Date(a.applied_date).toLocaleDateString("pt-BR")}</span>
              <span className="text-neutralState">{a.raw_scores.length} domínio(s)</span>
            </label>
          ))}
        </div>
      )}

      {assessmentsOfProtocol.length >= 2 && (
        <button
          onClick={handleCompare}
          disabled={selectedIds.length < 2}
          className="rounded-btn bg-brand-blueLight text-white px-4 py-2 text-sm font-medium disabled:opacity-40 mb-6"
        >
          Comparar selecionadas ({selectedIds.length})
        </button>
      )}

      {comparison && (
        <div className="bg-white rounded-card shadow-sm p-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-brand-navy">
              Comparação: {new Date(comparison.applied_dates[0]).toLocaleDateString("pt-BR")} →{" "}
              {new Date(comparison.applied_dates[comparison.applied_dates.length - 1]).toLocaleDateString("pt-BR")}
            </h2>
            <span className="text-[10px] uppercase font-semibold px-2 py-1 rounded-full bg-warning/10 text-warning">
              Rascunho automático por regras — revise antes de aprovar
            </span>
          </div>
          <table className="w-full text-sm mb-4">
            <thead>
              <tr className="text-left text-xs text-neutralState uppercase border-b border-slate-100">
                <th className="py-2">Domínio</th>
                <th className="py-2">Inicial</th>
                <th className="py-2">Final</th>
                <th className="py-2">Ganho absoluto</th>
                <th className="py-2">Ganho relativo</th>
              </tr>
            </thead>
            <tbody>
              {comparison.domains.map((d) => (
                <tr key={d.domain_code} className="border-b border-slate-50 last:border-0">
                  <td className="py-2">{d.domain_label}</td>
                  <td className="py-2">{d.earliest_pct}%</td>
                  <td className="py-2">{d.latest_pct}%</td>
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
