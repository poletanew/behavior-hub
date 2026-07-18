import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { apiDownload, apiRequest } from "../api/client";
import { Patient, ReportData, ReportSummary, Training, TrainingCategory } from "../types";

const CHART_COLORS = ["#3B82F6", "#14B8A6", "#22C55E", "#84CC16", "#8B5CF6", "#334155"];
const PROMPT_LABELS: Record<string, string> = {
  independent: "Independente",
  gestural: "Ajuda gestual",
  verbal: "Ajuda verbal",
  modeling: "Modelação",
  partial_physical: "Física parcial",
  full_physical: "Física total",
};

function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  window.URL.revokeObjectURL(url);
}

export default function ReportsPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [data, setData] = useState<ReportData | null>(null);
  const [categories, setCategories] = useState<TrainingCategory[]>([]);
  const [trainings, setTrainings] = useState<Training[]>([]);
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [summaryDraft, setSummaryDraft] = useState("");

  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [trainingId, setTrainingId] = useState("");
  const [categoryId, setCategoryId] = useState("");

  function loadReport() {
    if (!patientId) return;
    const params = new URLSearchParams();
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    if (trainingId) params.set("training_id", trainingId);
    if (categoryId) params.set("category_id", categoryId);
    apiRequest<ReportData>(`/reports/patients/${patientId}?${params.toString()}`).then(setData);
  }

  useEffect(() => {
    if (!patientId) return;
    apiRequest<Patient>(`/patients/${patientId}`).then(setPatient);
    apiRequest<TrainingCategory[]>("/training-categories").then(setCategories);
    apiRequest<Training[]>("/trainings").then(setTrainings);
    apiRequest<ReportSummary>(`/reports/patients/${patientId}/summary`)
      .then((s) => {
        setSummary(s);
        setSummaryDraft(s.content);
      })
      .catch(() => setSummary(null));
  }, [patientId]);

  useEffect(loadReport, [patientId, dateFrom, dateTo, trainingId, categoryId]);

  async function generateSummary() {
    if (!patientId) return;
    const today = new Date().toISOString().slice(0, 10);
    const s = await apiRequest<ReportSummary>(`/reports/patients/${patientId}/summary/generate`, {
      method: "POST",
      body: {
        period_start: dateFrom || "2000-01-01",
        period_end: dateTo || today,
        training_id: trainingId || null,
        category_id: categoryId || null,
      },
    });
    setSummary(s);
    setSummaryDraft(s.content);
  }

  async function saveSummary(status?: "approved" | "discarded") {
    if (!summary) return;
    const updated = await apiRequest<ReportSummary>(`/reports/summaries/${summary.id}`, {
      method: "PATCH",
      body: { content: summaryDraft, status },
    });
    setSummary(updated);
  }

  async function exportCsv() {
    if (!patientId) return;
    const blob = await apiDownload(`/reports/patients/${patientId}/export.csv`);
    downloadBlob(blob, `relatorio-${patientId}.csv`);
  }

  async function exportPdf() {
    if (!patientId) return;
    const params = new URLSearchParams();
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    const blob = await apiDownload(`/reports/patients/${patientId}/export.pdf?${params.toString()}`);
    downloadBlob(blob, `relatorio-${patientId}.pdf`);
  }

  if (!data) return <p className="text-neutralState">Carregando...</p>;

  const pieData = [
    { name: "Correta", value: data.pie.correct },
    { name: "Incorreta", value: data.pie.incorrect },
    { name: "Parcial", value: data.pie.partial },
    { name: "Não respondida", value: data.pie.no_response },
  ];

  const promptLevelsSet = new Set<string>();
  data.stacked_bar.forEach((point) => Object.keys(point.distribution_pct).forEach((k) => promptLevelsSet.add(k)));
  const promptLevels = Array.from(promptLevelsSet);
  const stackedBarData = data.stacked_bar.map((point) => ({ date: point.date, ...point.distribution_pct }));

  return (
    <div>
      <Link to={`/patients/${patientId}`} className="text-sm text-brand-blue underline mb-4 inline-block">
        ← Voltar para o paciente
      </Link>

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-brand-navy">Reports{patient ? ` — ${patient.name}` : ""}</h1>
        <div className="flex gap-2">
          <button onClick={exportCsv} className="rounded-btn bg-white border border-slate-300 px-3 py-2 text-sm font-medium">
            Exportar CSV
          </button>
          <button onClick={exportPdf} className="rounded-btn bg-white border border-slate-300 px-3 py-2 text-sm font-medium">
            Exportar PDF
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-3 mb-6 bg-white rounded-card shadow-sm p-4">
        <div>
          <label className="block text-xs font-medium mb-1">De</label>
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="h-9 rounded-btn border border-slate-300 px-2 text-sm" />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">Até</label>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="h-9 rounded-btn border border-slate-300 px-2 text-sm" />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">Treino</label>
          <select value={trainingId} onChange={(e) => setTrainingId(e.target.value)} className="h-9 rounded-btn border border-slate-300 px-2 text-sm">
            <option value="">Todos</option>
            {trainings.map((t) => (
              <option key={t.id} value={t.id}>
                {t.title}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">Área</label>
          <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)} className="h-9 rounded-btn border border-slate-300 px-2 text-sm">
            <option value="">Todas</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="bg-white rounded-card shadow-sm p-6 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-brand-navy">Resumo</h2>
          <span className="text-[10px] uppercase font-semibold px-2 py-1 rounded-full bg-warning/10 text-warning">
            Rascunho automático por regras — revise antes de exportar
          </span>
        </div>
        {summary ? (
          <>
            <textarea
              value={summaryDraft}
              onChange={(e) => setSummaryDraft(e.target.value)}
              className="w-full rounded-btn border border-slate-300 px-3 py-2 text-sm min-h-[100px]"
            />
            <div className="flex gap-2 mt-3">
              <button onClick={() => saveSummary()} className="rounded-btn bg-white border border-slate-300 px-3 py-1.5 text-xs font-medium">
                Salvar edição
              </button>
              <button onClick={() => saveSummary("approved")} className="rounded-btn bg-success text-white px-3 py-1.5 text-xs font-medium">
                Aprovar
              </button>
              <button onClick={() => saveSummary("discarded")} className="rounded-btn bg-white border border-slate-300 px-3 py-1.5 text-xs font-medium">
                Descartar
              </button>
              <button onClick={generateSummary} className="rounded-btn bg-brand-blueLight text-white px-3 py-1.5 text-xs font-medium">
                Gerar novamente
              </button>
            </div>
          </>
        ) : (
          <button onClick={generateSummary} className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium">
            Gerar resumo do período
          </button>
        )}
      </div>

      {data.total_trials === 0 ? (
        <div className="bg-white rounded-card shadow-sm p-10 text-center text-neutralState">
          Nenhuma tentativa registrada para os filtros selecionados.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-card shadow-sm p-6">
            <h3 className="font-semibold text-brand-navy mb-2">Evolução do percentual de acerto</h3>
            {data.line.map((series) => (
              <div key={series.training_id} className="mb-4">
                <div className="text-xs text-neutralState mb-1">{series.training_title}</div>
                <ResponsiveContainer width="100%" height={180}>
                  <LineChart data={series.points}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                    <XAxis dataKey="date" fontSize={9} />
                    <YAxis domain={[0, 100]} fontSize={9} />
                    <Tooltip contentStyle={{ background: "#334155", color: "#fff", border: "none" }} />
                    <Line type="monotone" dataKey="accuracy_pct" name="Acerto %" stroke={CHART_COLORS[0]} strokeWidth={2} />
                    <Line type="monotone" dataKey="independence_pct" name="Independência %" stroke={CHART_COLORS[1]} strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ))}
          </div>

          <div className="bg-white rounded-card shadow-sm p-6">
            <h3 className="font-semibold text-brand-navy mb-2">Comparação entre treinos</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={data.bar}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="training_title" fontSize={9} />
                <YAxis domain={[0, 100]} fontSize={9} />
                <Tooltip contentStyle={{ background: "#334155", color: "#fff", border: "none" }} />
                <Bar dataKey="accuracy_pct" name="Acerto %" fill={CHART_COLORS[0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-card shadow-sm p-6">
            <h3 className="font-semibold text-brand-navy mb-2">Distribuição de níveis de ajuda por sessão</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={stackedBarData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="date" fontSize={9} />
                <YAxis fontSize={9} />
                <Tooltip contentStyle={{ background: "#334155", color: "#fff", border: "none" }} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                {promptLevels.map((level, idx) => (
                  <Bar key={level} dataKey={level} name={PROMPT_LABELS[level] || level} stackId="a" fill={CHART_COLORS[idx % CHART_COLORS.length]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-card shadow-sm p-6">
            <h3 className="font-semibold text-brand-navy mb-2">Distribuição de resultados</h3>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80}>
                  {pieData.map((_, idx) => (
                    <Cell key={idx} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <Tooltip contentStyle={{ background: "#334155", color: "#fff", border: "none" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-card shadow-sm p-6">
            <h3 className="font-semibold text-brand-navy mb-2">Visão resumida por área (radar)</h3>
            {data.radar.some((r) => r.insufficient_data) && (
              <p className="text-xs text-warning mb-2">
                Atenção: algumas áreas têm poucas tentativas registradas — leitura sujeita a limitações estatísticas.
              </p>
            )}
            <ResponsiveContainer width="100%" height={220}>
              <RadarChart data={data.radar}>
                <PolarGrid stroke="#E2E8F0" />
                <PolarAngleAxis dataKey="area" fontSize={9} />
                <Radar dataKey="accuracy_pct" name="Acerto %" stroke={CHART_COLORS[4]} fill={CHART_COLORS[4]} fillOpacity={0.4} />
                <Tooltip contentStyle={{ background: "#334155", color: "#fff", border: "none" }} />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-card shadow-sm p-6">
            <h3 className="font-semibold text-brand-navy mb-2">Avanço acumulado</h3>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={data.cumulative}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="date" fontSize={9} />
                <YAxis fontSize={9} />
                <Tooltip contentStyle={{ background: "#334155", color: "#fff", border: "none" }} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <Line type="monotone" dataKey="cumulative_correct" name="Corretas acumuladas" stroke={CHART_COLORS[2]} strokeWidth={2} />
                <Line type="monotone" dataKey="cumulative_independence_pct" name="Independência % acumulada" stroke={CHART_COLORS[4]} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
