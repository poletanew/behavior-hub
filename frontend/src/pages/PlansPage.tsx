import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { apiRequest, ApiError } from "../api/client";
import { BillingStatus, PlanId } from "../types";

interface PlanColumn {
  id: PlanId;
  label: string;
  rows: string[];
}

const FEATURE_LABELS = [
  "Pacientes",
  "Novas sessões",
  "Foto em sessão",
  "Gráficos avançados",
  "ProfessionalRegistration (convites)",
  "Compartilhamento de pacientes",
  "Recursos terapêuticos",
  "Clinical Intelligence (alertas/timeline/heatmap)",
  "Suporte/branding",
];

const STATUS_LABELS: Record<string, string> = {
  none: "Sem assinatura paga",
  active: "Ativa",
  trialing: "Em período de teste",
  past_due: "Pagamento em atraso",
  canceled: "Cancelada",
  incomplete: "Incompleta",
  incomplete_expired: "Expirada",
  unpaid: "Não paga",
};

const PLAN_COLUMNS: PlanColumn[] = [
  {
    id: "free",
    label: "Free",
    rows: ["Até 3", "Sim", "Não", "Não", "Não", "Não", "Básico", "Não", "Padrão"],
  },
  {
    id: "basic",
    label: "Basic",
    rows: ["Limite configurável", "Sim", "Configurável", "Parcial", "Não", "Não", "Sim", "Não", "Padrão"],
  },
  {
    id: "premium",
    label: "Premium",
    rows: ["Maior limite", "Sim", "Sim", "Sim", "Não", "Limitado", "Sim", "Parcial", "Avançado"],
  },
  {
    id: "enterprise",
    label: "Enterprise",
    rows: ["Clínica e múltiplos usuários", "Sim", "Sim", "Sim", "Sim", "Sim", "Sim", "Sim", "Clínica"],
  },
];

export default function PlansPage() {
  const [searchParams] = useSearchParams();
  const checkoutResult = searchParams.get("checkout");
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingPlan, setLoadingPlan] = useState<PlanId | null>(null);
  const [loadingPortal, setLoadingPortal] = useState(false);

  function load() {
    apiRequest<BillingStatus>("/billing/status")
      .then(setStatus)
      .catch(() => setError("Não foi possível carregar o status da assinatura."));
  }

  useEffect(load, []);

  async function handleSubscribe(plan: PlanId) {
    setError(null);
    setLoadingPlan(plan);
    try {
      const response = await apiRequest<{ checkout_url: string }>("/stripe/checkout", {
        method: "POST",
        body: { plan },
      });
      window.location.href = response.checkout_url;
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        setError(
          "O pagamento via Stripe ainda não foi configurado neste ambiente. Assim que as chaves forem cadastradas, este botão levará ao Checkout do Stripe."
        );
      } else if (err instanceof ApiError && err.status === 403) {
        setError("Apenas o administrador da clínica ou a conta individual podem gerenciar o plano.");
      } else {
        setError("Não foi possível iniciar o checkout. Tente novamente.");
      }
    } finally {
      setLoadingPlan(null);
    }
  }

  async function handleManageSubscription() {
    setError(null);
    setLoadingPortal(true);
    try {
      const response = await apiRequest<{ portal_url: string }>("/stripe/portal", { method: "POST" });
      window.location.href = response.portal_url;
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        setError("O Portal do Cliente Stripe ainda não foi configurado neste ambiente.");
      } else if (err instanceof ApiError && err.status === 400) {
        setError("Você ainda não tem uma assinatura ativa — assine um plano pago primeiro.");
      } else {
        setError("Não foi possível abrir o portal de gerenciamento.");
      }
    } finally {
      setLoadingPortal(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-navy mb-2">Planos</h1>
      <p className="text-sm text-neutralState mb-6">
        Comparativo de planos (Seção 8.1 do PRD). Upgrade/downgrade levam ao Stripe Checkout; "Gerenciar
        assinatura" abre o Portal do Cliente Stripe.
      </p>

      {!status?.stripe_configured && (
        <div className="bg-brand-grayLight border border-brand-blueLight rounded-card p-4 mb-6 text-sm">
          O pagamento via Stripe ainda não está configurado neste ambiente. A tela e a lógica de planos já
          estão prontas; assim que as chaves de API forem cadastradas, os botões abaixo funcionam de ponta a
          ponta sem nenhuma mudança de código.
        </div>
      )}
      {checkoutResult === "success" && (
        <div className="bg-success/10 border border-success rounded-card p-4 mb-6 text-sm text-success">
          Assinatura confirmada! Pode levar alguns instantes até o plano ser atualizado aqui.
        </div>
      )}
      {checkoutResult === "cancel" && (
        <div className="bg-brand-grayLight border border-slate-300 rounded-card p-4 mb-6 text-sm">
          Checkout cancelado — nenhuma cobrança foi feita.
        </div>
      )}
      {error && <p className="text-danger text-sm mb-4">{error}</p>}

      {status && (
        <div className="bg-white rounded-card shadow-card p-4 mb-6 max-w-xl text-sm">
          <p>
            Plano atual: <span className="font-semibold text-brand-navy capitalize">{status.subscription_plan ?? "free"}</span>
            {" — "}
            status da assinatura: <span>{STATUS_LABELS[status.subscription_status] ?? status.subscription_status}</span>
          </p>
          {status.subscription_current_period_end && (
            <p className="text-neutralState mt-1">
              Próxima renovação: {new Date(status.subscription_current_period_end).toLocaleDateString("pt-BR")}
            </p>
          )}
          <button
            onClick={handleManageSubscription}
            disabled={loadingPortal}
            className="mt-3 rounded-btn border border-brand-navy text-brand-navy px-4 py-2 text-sm font-medium disabled:opacity-50"
          >
            {loadingPortal ? "Abrindo..." : "Gerenciar assinatura"}
          </button>
        </div>
      )}

      <div className="bg-white rounded-card shadow-card overflow-x-auto">
        <table className="w-full text-sm min-w-[720px]">
          <thead>
            <tr className="bg-brand-navy text-white">
              <th className="text-left px-4 py-3">Recurso</th>
              {PLAN_COLUMNS.map((col) => (
                <th
                  key={col.id}
                  className={`text-left px-4 py-3 ${status?.subscription_plan === col.id ? "bg-brand-turquoise" : ""}`}
                >
                  {col.label}
                  {status?.subscription_plan === col.id && (
                    <span className="block text-[10px] font-normal uppercase tracking-wide">Plano atual</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {FEATURE_LABELS.map((feature, rowIdx) => (
              <tr key={feature} className={rowIdx % 2 === 1 ? "bg-slate-50" : undefined}>
                <td className="px-4 py-2 font-medium">{feature}</td>
                {PLAN_COLUMNS.map((col) => (
                  <td key={col.id} className="px-4 py-2">
                    {col.rows[rowIdx]}
                  </td>
                ))}
              </tr>
            ))}
            <tr className="bg-slate-100">
              <td className="px-4 py-3 font-medium">Assinar</td>
              {PLAN_COLUMNS.map((col) => (
                <td key={col.id} className="px-4 py-3">
                  {col.id === "free" ? (
                    <span className="text-neutralState text-xs">Plano inicial de toda conta nova</span>
                  ) : (
                    <button
                      onClick={() => handleSubscribe(col.id)}
                      disabled={loadingPlan === col.id || status?.subscription_plan === col.id}
                      className="rounded-btn bg-brand-turquoise text-white px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                    >
                      {status?.subscription_plan === col.id
                        ? "Plano atual"
                        : loadingPlan === col.id
                          ? "Redirecionando..."
                          : "Assinar"}
                    </button>
                  )}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
