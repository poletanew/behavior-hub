import { useEffect, useState } from "react";
import { apiRequest } from "../api/client";
import { ManagerDashboardData } from "../types";

export default function ManagerDashboardPage() {
  const [data, setData] = useState<ManagerDashboardData | null>(null);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  function load() {
    const params = new URLSearchParams();
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    apiRequest<ManagerDashboardData>(`/clinic/manager-dashboard?${params.toString()}`).then((d) => {
      setData(d);
      setDateFrom(d.period_start);
      setDateTo(d.period_end);
    });
  }

  useEffect(load, []);

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-navy mb-2">Painel de Gestão</h1>
      <p className="text-sm text-neutralState mb-6">
        Visão de negócio da clínica (Seção 29.5): pacientes e profissionais ativos, sessões
        realizadas, horas clínicas e ocupação — todos derivados dos mesmos dados operacionais.
      </p>

      <div className="flex flex-wrap items-end gap-3 mb-6 bg-white rounded-card shadow-sm p-4">
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
        <button onClick={load} className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium">
          Aplicar
        </button>
      </div>

      {!data ? (
        <p className="text-neutralState">Carregando...</p>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="bg-white rounded-card shadow-sm p-5">
            <div className="text-xs text-neutralState uppercase font-medium mb-1">Pacientes ativos</div>
            <div className="text-2xl font-bold text-brand-navy">{data.active_patients_count}</div>
          </div>
          <div className="bg-white rounded-card shadow-sm p-5">
            <div className="text-xs text-neutralState uppercase font-medium mb-1">Profissionais ativos</div>
            <div className="text-2xl font-bold text-brand-navy">{data.active_professionals_count}</div>
          </div>
          <div className="bg-white rounded-card shadow-sm p-5">
            <div className="text-xs text-neutralState uppercase font-medium mb-1">Sessões realizadas</div>
            <div className="text-2xl font-bold text-brand-navy">{data.sessions_count}</div>
          </div>
          <div className="bg-white rounded-card shadow-sm p-5">
            <div className="text-xs text-neutralState uppercase font-medium mb-1">Horas clínicas</div>
            <div className="text-2xl font-bold text-brand-navy">{data.clinical_hours}h</div>
          </div>
          <div className="bg-white rounded-card shadow-sm p-5">
            <div className="text-xs text-neutralState uppercase font-medium mb-1">Ocupação</div>
            <div className="text-2xl font-bold text-brand-navy">
              {data.occupancy_rate_pct === null ? "—" : `${data.occupancy_rate_pct}%`}
            </div>
          </div>
        </div>
      )}

      <p className="text-xs text-neutralState mt-6">
        Indicadores de receita e taxa de faturamento não estão disponíveis: o Behavior Hub ainda não tem
        um módulo de cobrança por paciente/sessão — apenas a assinatura da própria clínica (ver Planos).
      </p>
    </div>
  );
}
