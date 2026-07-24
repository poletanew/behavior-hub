import { useEffect, useState } from "react";
import { apiRequest } from "../api/client";
import { ChurnRiskLabel, FinancialOutlook, ManagerDashboardData, ProgramPerformanceRow } from "../types";

const CHURN_RISK_LABELS: Record<ChurnRiskLabel, string> = {
  baixo: "Baixo",
  alto: "Alto",
  assinatura_encerrada: "Assinatura encerrada",
  nao_aplicavel: "Não aplicável (plano Free)",
};

const CHURN_RISK_COLORS: Record<ChurnRiskLabel, string> = {
  baixo: "bg-success/10 text-success",
  alto: "bg-danger/10 text-danger",
  assinatura_encerrada: "bg-slate-200 text-neutralState",
  nao_aplicavel: "bg-slate-200 text-neutralState",
};

const PLAN_LABELS: Record<string, string> = { free: "Free", basic: "Basic", premium: "Premium", enterprise: "Enterprise" };

export default function ManagerDashboardPage() {
  const [data, setData] = useState<ManagerDashboardData | null>(null);
  const [programRows, setProgramRows] = useState<ProgramPerformanceRow[] | null>(null);
  const [financialOutlook, setFinancialOutlook] = useState<FinancialOutlook | null>(null);
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

  useEffect(() => {
    apiRequest<ProgramPerformanceRow[]>("/clinic/manager-dashboard/program-performance").then(setProgramRows);
    apiRequest<FinancialOutlook>("/clinic/manager-dashboard/financial-outlook").then(setFinancialOutlook);
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-navy mb-2">Painel de Gestão</h1>
      <p className="text-sm text-neutralState mb-6">
        Visão de negócio da clínica (Seção 29.5): pacientes e profissionais ativos, sessões
        realizadas, horas clínicas e ocupação — todos derivados dos mesmos dados operacionais.
      </p>

      <div className="flex flex-wrap items-end gap-3 mb-6 bg-white rounded-card shadow-card p-4">
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
          <div className="bg-white rounded-card shadow-card p-5">
            <div className="text-xs text-neutralState uppercase font-medium mb-1">Pacientes ativos</div>
            <div className="text-2xl font-bold text-brand-navy">{data.active_patients_count}</div>
          </div>
          <div className="bg-white rounded-card shadow-card p-5">
            <div className="text-xs text-neutralState uppercase font-medium mb-1">Profissionais ativos</div>
            <div className="text-2xl font-bold text-brand-navy">{data.active_professionals_count}</div>
          </div>
          <div className="bg-white rounded-card shadow-card p-5">
            <div className="text-xs text-neutralState uppercase font-medium mb-1">Sessões realizadas</div>
            <div className="text-2xl font-bold text-brand-navy">{data.sessions_count}</div>
          </div>
          <div className="bg-white rounded-card shadow-card p-5">
            <div className="text-xs text-neutralState uppercase font-medium mb-1">Horas clínicas</div>
            <div className="text-2xl font-bold text-brand-navy">{data.clinical_hours}h</div>
          </div>
          <div className="bg-white rounded-card shadow-card p-5">
            <div className="text-xs text-neutralState uppercase font-medium mb-1">Ocupação</div>
            <div className="text-2xl font-bold text-brand-navy">
              {data.occupancy_rate_pct === null ? "—" : `${data.occupancy_rate_pct}%`}
            </div>
          </div>
        </div>
      )}

      <h2 className="text-lg font-semibold text-brand-navy mt-8 mb-2">Desempenho do Programa</h2>
      <p className="text-sm text-neutralState mb-4">
        Addendum v3.0, RF-32 — agregado por treino da Training Library, restrito a treinos aplicados
        a pelo menos 2 pacientes distintos.
      </p>
      {!programRows ? (
        <p className="text-neutralState">Carregando...</p>
      ) : programRows.length === 0 ? (
        <div className="bg-white rounded-card shadow-card p-6 text-center text-neutralState">
          Nenhum treino atingiu o mínimo de 2 pacientes ainda.
        </div>
      ) : (
        <div className="bg-white rounded-card shadow-card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-xs text-neutralState uppercase">
                <th className="px-4 py-3">Treino</th>
                <th className="px-4 py-3">Pacientes</th>
                <th className="px-4 py-3">Objetivos</th>
                <th className="px-4 py-3">Taxa de domínio</th>
                <th className="px-4 py-3">Tempo médio até dominar</th>
              </tr>
            </thead>
            <tbody>
              {programRows.map((row) => (
                <tr key={row.training_id} className="border-b border-slate-50 last:border-0">
                  <td className="px-4 py-3 font-medium">{row.training_title}</td>
                  <td className="px-4 py-3">{row.patients_count}</td>
                  <td className="px-4 py-3">{row.objectives_count}</td>
                  <td className="px-4 py-3">{row.mastery_rate_pct}%</td>
                  <td className="px-4 py-3">
                    {row.average_days_to_mastery === null ? "—" : `${row.average_days_to_mastery} dias`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h2 className="text-lg font-semibold text-brand-navy mt-8 mb-2">Previsibilidade Financeira</h2>
      <p className="text-sm text-neutralState mb-4">
        Addendum v3.0, RF-32 — usa apenas os dados da própria assinatura da clínica com o Behavior
        Hub (Seção 8.3); não há hoje um valor de receita recorrente por paciente para agregar.
      </p>
      {!financialOutlook ? (
        <p className="text-neutralState">Carregando...</p>
      ) : (
        <div className="bg-white rounded-card shadow-card p-5 max-w-md flex items-center justify-between gap-4">
          <div>
            <div className="text-sm">
              Plano atual: <span className="font-semibold">{PLAN_LABELS[financialOutlook.subscription_plan]}</span>
            </div>
            <div className="text-sm text-neutralState mt-1">
              {financialOutlook.current_period_end
                ? `Renovação em ${new Date(financialOutlook.current_period_end).toLocaleDateString("pt-BR")}${
                    financialOutlook.days_until_renewal !== null
                      ? ` (${financialOutlook.days_until_renewal} dias)`
                      : ""
                  }`
                : "Sem data de renovação (plano sem assinatura ativa)"}
            </div>
          </div>
          <span
            className={`text-xs uppercase font-semibold px-2 py-1 rounded-full shrink-0 ${
              CHURN_RISK_COLORS[financialOutlook.churn_risk_label]
            }`}
          >
            Risco: {CHURN_RISK_LABELS[financialOutlook.churn_risk_label]}
          </span>
        </div>
      )}
    </div>
  );
}
