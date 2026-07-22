import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest } from "../api/client";
import { DashboardData } from "../types";

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("pt-BR");
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiRequest<DashboardData>("/dashboard")
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-neutralState">Carregando...</p>;
  if (!data) return <p className="text-danger">Não foi possível carregar a área de trabalho.</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-navy mb-6">Área de Trabalho</h1>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-card shadow-sm p-6">
          <div className="text-sm text-neutralState">Pacientes ativos</div>
          <div className="text-3xl font-bold text-brand-navy">{data.active_patients_count}</div>
        </div>
        <div className="bg-white rounded-card shadow-sm p-6">
          <div className="text-sm text-neutralState">Sessões hoje</div>
          <div className="text-3xl font-bold text-brand-navy">{data.sessions_today_count}</div>
        </div>
        <div className="bg-white rounded-card shadow-sm p-6">
          <div className="text-sm text-neutralState">Planos pendentes</div>
          <div className="text-3xl font-bold text-brand-navy">0</div>
        </div>
      </div>

      <div className="bg-white rounded-card shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-brand-navy">Sessões recentes</h2>
          <Link to="/sessions" className="text-sm text-brand-blue underline">
            Ver todos
          </Link>
        </div>

        {data.recent_sessions.length === 0 ? (
          <div className="text-center py-10 animate-fade-in">
            <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-brand-turquoise/10 text-2xl">
              ✨
            </div>
            <p className="text-neutralState mb-4">
              Nenhuma sessão registrada. Adicione um paciente para iniciar.
            </p>
            <Link
              to="/patients"
              className="inline-block rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium"
            >
              + Adicionar paciente
            </Link>
          </div>
        ) : (
          <ul className="divide-y divide-slate-100">
            {data.recent_sessions.map((session) => (
              <li key={session.id} className="py-3">
                <Link to={`/sessions/${session.id}`} className="flex justify-between hover:text-brand-blue">
                  <span>{formatDateTime(session.occurred_at)}</span>
                  <span className="text-neutralState text-sm">{session.trainings.length} treino(s)</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
