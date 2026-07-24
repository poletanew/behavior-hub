import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiRequest } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { Patient, User, WorkspaceDashboardResponse } from "../types";

const COLORS = {
  teal: "#14B8A6",
  blueLight: "#3B82F6",
  green: "#22C55E",
  red: "#EF4444",
  orange: "#F59E0B",
  neutral: "#64748B",
  border: "#E2E8F0",
};

function toneFor(pct: number): string {
  if (pct >= 70) return "bg-success/10 text-success";
  if (pct >= 40) return "bg-warning/10 text-warning";
  return "bg-danger/10 text-danger";
}

const RESULT_LABELS: Record<string, { label: string; color: string }> = {
  correct: { label: "Correta", color: COLORS.green },
  incorrect: { label: "Incorreta", color: COLORS.red },
  partial: { label: "Parcial", color: COLORS.orange },
  no_response: { label: "Não respondida", color: COLORS.neutral },
};

export default function DashboardPage() {
  const { user } = useAuth();
  const [panel, setPanel] = useState<"paciente" | "profissional">("paciente");
  const [patients, setPatients] = useState<Patient[]>([]);
  const [professionals, setProfessionals] = useState<User[]>([]);
  const [patientId, setPatientId] = useState("");
  const [professionalId, setProfessionalId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [rankOrder, setRankOrder] = useState<"top" | "bottom">("top");
  const [data, setData] = useState<WorkspaceDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiRequest<Patient[]>("/patients").then(setPatients);
    apiRequest<User[]>("/professionals").then((list) => setProfessionals(list.filter((p) => p.user_type !== "family")));
  }, []);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (panel === "paciente" && patientId) params.set("patient_id", patientId);
    if (panel === "profissional" && professionalId) params.set("professional_id", professionalId);
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    apiRequest<WorkspaceDashboardResponse>(`/dashboard/workspace?${params.toString()}`)
      .then(setData)
      .finally(() => setLoading(false));
  }, [panel, patientId, professionalId, dateFrom, dateTo]);

  const distributionData = data
    ? (Object.entries(data.distribution) as [keyof typeof RESULT_LABELS, number][])
        .filter(([, value]) => value > 0)
        .map(([key, value]) => ({ name: RESULT_LABELS[key].label, value, color: RESULT_LABELS[key].color }))
    : [];

  const ranking = data
    ? [...data.training_ranking]
        .sort((a, b) => (rankOrder === "top" ? b.accuracy_pct - a.accuracy_pct : a.accuracy_pct - b.accuracy_pct))
        .slice(0, 5)
    : [];

  return (
    <div>
      <h1 className="text-[22px] font-bold text-brand-navy mb-1">Área de Trabalho</h1>
      <p className="text-neutralState text-[13.5px] mb-4">
        Bem-vindo(a){user?.name ? `, ${user.name}` : ""} — painel calculado em tempo real a partir dos dados registrados.
      </p>

      <div className="flex gap-1 mb-3.5">
        <button
          onClick={() => setPanel("paciente")}
          className={`px-4 py-2 rounded-t-lg text-[12.5px] font-bold border-b-[2.5px] ${
            panel === "paciente" ? "bg-white text-brand-blue border-brand-turquoise" : "text-neutralState border-transparent"
          }`}
        >
          Painel do Paciente
        </button>
        <button
          onClick={() => setPanel("profissional")}
          className={`px-4 py-2 rounded-t-lg text-[12.5px] font-bold border-b-[2.5px] ${
            panel === "profissional" ? "bg-white text-brand-blue border-brand-turquoise" : "text-neutralState border-transparent"
          }`}
        >
          Painel do Profissional
        </button>
      </div>

      <div className="bg-white rounded-card shadow-card p-5 mb-4">
        <div className="grid grid-cols-3 gap-2.5">
          {panel === "paciente" ? (
            <div>
              <label className="block text-[12.5px] font-semibold text-brand-graphite mb-1">Paciente</label>
              <select
                className="w-full rounded-lg border border-borderMuted px-3 py-2 text-[13.5px]"
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
              >
                <option value="">Todos</option>
                {patients.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <div>
              <label className="block text-[12.5px] font-semibold text-brand-graphite mb-1">Profissional</label>
              <select
                className="w-full rounded-lg border border-borderMuted px-3 py-2 text-[13.5px]"
                value={professionalId}
                onChange={(e) => setProfessionalId(e.target.value)}
              >
                <option value="">Todos</option>
                {professionals.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label className="block text-[12.5px] font-semibold text-brand-graphite mb-1">Data início</label>
            <input
              type="date"
              className="w-full rounded-lg border border-borderMuted px-3 py-2 text-[13.5px]"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-[12.5px] font-semibold text-brand-graphite mb-1">Data fim</label>
            <input
              type="date"
              className="w-full rounded-lg border border-borderMuted px-3 py-2 text-[13.5px]"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-3.5 mb-4">
        <div className="bg-white rounded-card shadow-card p-5">
          <div className="text-neutralState text-xs mb-1.5">Sessões realizadas</div>
          <div className="text-2xl font-extrabold text-brand-navy">{loading ? "…" : data?.kpis.sessions_count ?? 0}</div>
        </div>
        <div className="bg-white rounded-card shadow-card p-5">
          <div className="text-neutralState text-xs mb-1.5">Programas aplicados</div>
          <div className="text-2xl font-extrabold text-brand-navy">{loading ? "…" : data?.kpis.programs_count ?? 0}</div>
        </div>
        <div className="bg-white rounded-card shadow-card p-5">
          <div className="text-neutralState text-xs mb-1.5">Média tentativas/sessão</div>
          <div className="text-2xl font-extrabold text-brand-navy">{loading ? "…" : data?.kpis.avg_trials_per_session ?? 0}</div>
        </div>
        <div className="bg-white rounded-card shadow-card p-5">
          <div className="text-neutralState text-xs mb-1.5">Média de acerto</div>
          <div className="text-2xl font-extrabold text-brand-navy">{loading ? "…" : `${data?.kpis.avg_accuracy_pct ?? 0}%`}</div>
        </div>
      </div>

      {!loading && data && data.kpis.sessions_count === 0 ? (
        <div className="bg-white rounded-card shadow-card p-10 text-center">
          <div className="text-3xl mb-1.5">🌱</div>
          <p className="text-neutralState text-sm">Nenhuma sessão no período/filtro selecionado ainda.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white rounded-card shadow-card p-5">
            <h3 className="text-sm font-semibold text-brand-graphite mb-2.5">Desempenho por Área</h3>
            <ResponsiveContainer width="100%" height={190}>
              <BarChart data={data?.area_performance ?? []}>
                <CartesianGrid stroke={COLORS.border} vertical={false} />
                <XAxis dataKey="area" tick={{ fontSize: 10.5 }} />
                <YAxis tick={{ fontSize: 11 }} unit="%" />
                <Tooltip />
                <Bar dataKey="accuracy_pct" fill={COLORS.teal} radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-card shadow-card p-5">
            <div className="flex justify-between items-center mb-2.5">
              <h3 className="text-sm font-semibold text-brand-graphite">Treinos: Maior/Menor Desempenho</h3>
              <div className="flex gap-1">
                <button
                  onClick={() => setRankOrder("top")}
                  className={`text-[10.5px] px-2 py-1 rounded-md border border-borderMuted font-bold ${
                    rankOrder === "top" ? "bg-brand-blue text-white" : "bg-white text-brand-graphite"
                  }`}
                >
                  Maior
                </button>
                <button
                  onClick={() => setRankOrder("bottom")}
                  className={`text-[10.5px] px-2 py-1 rounded-md border border-borderMuted font-bold ${
                    rankOrder === "bottom" ? "bg-brand-blue text-white" : "bg-white text-brand-graphite"
                  }`}
                >
                  Menor
                </button>
              </div>
            </div>
            {ranking.length === 0 ? (
              <p className="text-neutralState text-xs">Sem dados suficientes ainda.</p>
            ) : (
              ranking.map((t, i) => (
                <div
                  key={t.training_id}
                  className={`flex justify-between items-center py-1.5 ${i < ranking.length - 1 ? "border-b border-borderMuted" : ""}`}
                >
                  <span className="text-[12.5px] text-brand-graphite">{t.title}</span>
                  <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full ${toneFor(t.accuracy_pct)}`}>
                    {t.accuracy_pct}%
                  </span>
                </div>
              ))
            )}
          </div>

          <div className="bg-white rounded-card shadow-card p-5">
            <h3 className="text-sm font-semibold text-brand-graphite mb-2.5">Distribuição de Resultados</h3>
            <ResponsiveContainer width="100%" height={190}>
              <PieChart>
                <Pie data={distributionData} dataKey="value" nameKey="name" innerRadius={38} outerRadius={68}>
                  {distributionData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Legend wrapperStyle={{ fontSize: 10.5 }} />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-card shadow-card p-5">
            <h3 className="text-sm font-semibold text-brand-graphite mb-2.5">Sessões por Semana</h3>
            <ResponsiveContainer width="100%" height={190}>
              <BarChart data={data?.weekly_sessions ?? []}>
                <CartesianGrid stroke={COLORS.border} vertical={false} />
                <XAxis dataKey="week_label" tick={{ fontSize: 10.5 }} />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="sessions_count" fill={COLORS.blueLight} radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
