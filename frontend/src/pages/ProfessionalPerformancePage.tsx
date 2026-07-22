import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiDownload, apiRequest } from "../api/client";
import { ProfessionalPerformance } from "../types";

const EFFICIENCY_LABELS: Record<string, string> = {
  alta: "Alta",
  media: "Média",
  baixa: "Baixa",
};

const EFFICIENCY_COLORS: Record<string, string> = {
  alta: "bg-success/10 text-success",
  media: "bg-warning/10 text-warning",
  baixa: "bg-danger/10 text-danger",
};

function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  window.URL.revokeObjectURL(url);
}

export default function ProfessionalPerformancePage() {
  const { professionalId } = useParams<{ professionalId: string }>();
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [data, setData] = useState<ProfessionalPerformance | null>(null);

  function load() {
    if (!professionalId) return;
    const params = new URLSearchParams();
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    apiRequest<ProfessionalPerformance>(
      `/reports/professionals/${professionalId}/performance?${params.toString()}`
    ).then(setData);
  }

  useEffect(load, [professionalId, dateFrom, dateTo]);

  async function handleExportPdf() {
    if (!professionalId) return;
    const params = new URLSearchParams();
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    const blob = await apiDownload(`/reports/professionals/${professionalId}/performance/export.pdf?${params.toString()}`);
    downloadBlob(blob, `desempenho-${professionalId}.pdf`);
  }

  if (!data) return <p className="text-neutralState">Carregando...</p>;

  return (
    <div>
      <Link to="/supervisor-dashboard" className="text-sm text-brand-blue underline mb-4 inline-block">
        ← Voltar para o Painel de Supervisão
      </Link>
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold text-brand-navy">Desempenho — {data.professional_name}</h1>
        <button
          onClick={handleExportPdf}
          className="rounded-btn border border-brand-navy text-brand-navy px-4 py-2 text-sm font-medium"
        >
          Exportar (.pdf)
        </button>
      </div>
      <p className="text-sm text-neutralState mb-6">
        Addendum v3.0, RF-31 — relatório individual, distinto do Painel de Supervisão: sessões
        realizadas, consistência de registro, percentual médio de acerto e eficiência do aplicador.
      </p>

      <div className="bg-white rounded-card shadow-sm p-4 mb-6 flex flex-wrap gap-4 items-end">
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

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-card shadow-sm p-4">
          <div className="text-xs text-neutralState uppercase font-semibold mb-1">Atendimentos realizados</div>
          <div className="text-2xl font-bold text-brand-navy">{data.sessions_count}</div>
        </div>
        <div className="bg-white rounded-card shadow-sm p-4">
          <div className="text-xs text-neutralState uppercase font-semibold mb-1">Consistência de registro</div>
          <div className="text-2xl font-bold text-brand-navy">
            {data.registration_consistency_pct === null ? "—" : `${data.registration_consistency_pct}%`}
          </div>
          <div className="text-xs text-neutralState mt-1">Sessões com ao menos uma tentativa registrada</div>
        </div>
        <div className="bg-white rounded-card shadow-sm p-4">
          <div className="text-xs text-neutralState uppercase font-semibold mb-1">Percentual médio de acerto</div>
          <div className="text-2xl font-bold text-brand-navy">
            {data.average_accuracy_pct === null ? "—" : `${data.average_accuracy_pct}%`}
          </div>
        </div>
        <div className="bg-white rounded-card shadow-sm p-4">
          <div className="text-xs text-neutralState uppercase font-semibold mb-1">Eficiência do aplicador</div>
          <div className="flex items-center gap-2">
            {data.applier_efficiency_label ? (
              <span
                className={`text-xs uppercase font-semibold px-2 py-1 rounded-full ${
                  EFFICIENCY_COLORS[data.applier_efficiency_label]
                }`}
              >
                {EFFICIENCY_LABELS[data.applier_efficiency_label]}
              </span>
            ) : (
              <span className="text-2xl font-bold text-brand-navy">—</span>
            )}
          </div>
          {data.procedure_variability_pp !== null && (
            <div className="text-xs text-neutralState mt-1">
              Variabilidade entre sessões: {data.procedure_variability_pp} p.p.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
