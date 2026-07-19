import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiDownload, apiRequest, ApiError } from "../api/client";
import { Patient, PaymentStatus, SessionCharge } from "../types";

const PAYMENT_STATUS_LABELS: Record<PaymentStatus, string> = {
  pending: "Pendente",
  paid: "Pago",
  overdue: "Em atraso",
};

const PAYMENT_STATUS_COLORS: Record<PaymentStatus, string> = {
  pending: "bg-slate-200 text-neutralState",
  paid: "bg-success/10 text-success",
  overdue: "bg-danger/10 text-danger",
};

function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  window.URL.revokeObjectURL(url);
}

export default function BillingSessionsPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [patientId, setPatientId] = useState("");
  const [charges, setCharges] = useState<SessionCharge[]>([]);
  const [notAvailable, setNotAvailable] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<Patient[]>("/patients").then((data) => {
      setPatients(data);
      if (data.length > 0) setPatientId(data[0].id);
    });
  }, []);

  useEffect(() => {
    if (!patientId) return;
    apiRequest<SessionCharge[]>(`/patients/${patientId}/session-charges`)
      .then(setCharges)
      .catch(() => setCharges([]));
  }, [patientId]);

  async function handleStatusChange(chargeId: string, newStatus: PaymentStatus) {
    await apiRequest(`/session-charges/${chargeId}/status`, {
      method: "POST",
      body: { payment_status: newStatus },
    });
    apiRequest<SessionCharge[]>(`/patients/${patientId}/session-charges`).then(setCharges);
  }

  async function handleExport() {
    setError(null);
    try {
      const blob = await apiDownload("/session-charges/export.csv");
      downloadBlob(blob, "faturamento-por-sessao.csv");
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setNotAvailable(true);
      } else {
        setError("Não foi possível exportar o CSV.");
      }
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-brand-navy">Faturamento por Sessão</h1>
        <button
          onClick={handleExport}
          className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium"
        >
          Exportar CSV
        </button>
      </div>

      {notAvailable && (
        <div className="bg-brand-grayLight border border-brand-blueLight rounded-card p-4 mb-6 text-sm">
          Faturamento por sessão está disponível apenas nos planos <strong>Premium ou Enterprise</strong>. Veja{" "}
          <Link to="/plans" className="text-brand-blue underline">
            Planos
          </Link>
          .
        </div>
      )}
      {error && <p className="text-danger text-sm mb-4">{error}</p>}

      <select
        value={patientId}
        onChange={(e) => setPatientId(e.target.value)}
        className="h-10 rounded-btn border border-slate-300 px-3 mb-6"
      >
        {patients.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>

      <div className="bg-white rounded-card shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-brand-navy text-white">
            <tr>
              <th className="text-left px-4 py-3">Data da sessão</th>
              <th className="text-left px-4 py-3">Valor</th>
              <th className="text-left px-4 py-3">Vencimento</th>
              <th className="text-left px-4 py-3">Status</th>
              <th className="text-left px-4 py-3">Observações</th>
            </tr>
          </thead>
          <tbody>
            {charges.map((charge, idx) => (
              <tr key={charge.id} className={idx % 2 === 1 ? "bg-slate-50" : undefined}>
                <td className="px-4 py-3">{new Date(charge.session_date).toLocaleString("pt-BR")}</td>
                <td className="px-4 py-3">R$ {charge.amount.toFixed(2)}</td>
                <td className="px-4 py-3">{charge.due_date ?? "-"}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${PAYMENT_STATUS_COLORS[charge.payment_status]}`}
                    >
                      {PAYMENT_STATUS_LABELS[charge.payment_status]}
                    </span>
                    <select
                      value={charge.payment_status}
                      onChange={(e) => handleStatusChange(charge.id, e.target.value as PaymentStatus)}
                      className="h-8 text-xs rounded-btn border border-slate-300 px-2"
                    >
                      <option value="pending">Pendente</option>
                      <option value="paid">Pago</option>
                      <option value="overdue">Em atraso</option>
                    </select>
                  </div>
                </td>
                <td className="px-4 py-3 text-neutralState">{charge.notes ?? ""}</td>
              </tr>
            ))}
            {charges.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-neutralState">
                  Nenhuma cobrança registrada para este paciente. Vá até um atendimento para cobrar uma sessão.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
