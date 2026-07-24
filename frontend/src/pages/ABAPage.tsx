import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest, ApiError } from "../api/client";
import { ABAAssignedPatient, ABATrialReviewEntry, ATSummary, Patient } from "../types";

const RESULT_LABELS: Record<string, string> = {
  correct: "Correta",
  incorrect: "Incorreta",
  partial: "Parcial",
  no_response: "Não respondida",
};

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("pt-BR");
}

export default function ABAPage() {
  const [ats, setAts] = useState<ATSummary[]>([]);
  const [selectedAtId, setSelectedAtId] = useState("");
  const [atPatients, setAtPatients] = useState<ABAAssignedPatient[] | null>(null);
  const [allPatients, setAllPatients] = useState<Patient[]>([]);
  const [assignPatientId, setAssignPatientId] = useState("");
  const [assignError, setAssignError] = useState<string | null>(null);
  const [assignMessage, setAssignMessage] = useState<string | null>(null);
  const [trials, setTrials] = useState<ABATrialReviewEntry[]>([]);

  function loadAts() {
    apiRequest<ATSummary[]>("/aba/ats").then(setAts);
  }

  useEffect(() => {
    loadAts();
    apiRequest<Patient[]>("/patients").then(setAllPatients);
    apiRequest<ABATrialReviewEntry[]>("/aba/trials").then(setTrials);
  }, []);

  useEffect(() => {
    if (!selectedAtId) {
      setAtPatients(null);
      return;
    }
    apiRequest<ABAAssignedPatient[]>(`/aba/ats/${selectedAtId}/patients`).then(setAtPatients);
  }, [selectedAtId]);

  async function handleAssign(e: FormEvent) {
    e.preventDefault();
    setAssignError(null);
    setAssignMessage(null);
    if (!selectedAtId || !assignPatientId) return;
    try {
      await apiRequest(`/patients/${assignPatientId}/assignments`, {
        method: "POST",
        body: { professional_id: selectedAtId },
      });
      setAssignMessage("Paciente atribuído ao AT.");
      setAssignPatientId("");
      loadAts();
      apiRequest<ABAAssignedPatient[]>(`/aba/ats/${selectedAtId}/patients`).then(setAtPatients);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setAssignError("Você não tem permissão para atribuir pacientes.");
      } else {
        setAssignError("Não foi possível atribuir o paciente.");
      }
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-navy mb-2">ABA</h1>
      <p className="text-sm text-neutralState mb-6">
        Espaço de trabalho do supervisor: atribua ATs (Auxiliares Terapêuticos) a pacientes,
        acompanhe os treinos aplicados e revise as tentativas registradas (Addendum v2.1, RF-11).
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-white rounded-card shadow-card p-6">
          <h2 className="font-semibold text-brand-navy mb-3">Auxiliares Terapêuticos</h2>
          {ats.length === 0 ? (
            <p className="text-neutralState text-sm">Nenhum AT convidado ainda.</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {ats.map((at) => (
                <li key={at.id} className="flex items-center justify-between gap-2">
                  <button
                    onClick={() => setSelectedAtId(at.id)}
                    className={`flex-1 text-left px-2 py-2 text-sm rounded-btn ${
                      selectedAtId === at.id ? "bg-brand-turquoise/10" : "hover:bg-slate-50"
                    }`}
                  >
                    <div className="font-medium">{at.name}</div>
                    <div className="text-xs text-neutralState">
                      {at.email} · {at.assigned_patient_count} paciente(s) atribuído(s)
                    </div>
                  </button>
                  <Link
                    to={`/professionals/${at.id}/performance`}
                    className="text-brand-blue text-xs hover:underline shrink-0 pr-2"
                  >
                    Ver desempenho
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="bg-white rounded-card shadow-card p-6">
          <h2 className="font-semibold text-brand-navy mb-3">Atribuir paciente ao AT selecionado</h2>
          {!selectedAtId ? (
            <p className="text-neutralState text-sm">Selecione um AT à esquerda.</p>
          ) : (
            <>
              <form onSubmit={handleAssign} className="flex gap-2 mb-4">
                <select
                  required
                  value={assignPatientId}
                  onChange={(e) => setAssignPatientId(e.target.value)}
                  className="flex-1 h-9 rounded-btn border border-slate-300 px-2 text-sm"
                >
                  <option value="">Selecione um paciente...</option>
                  {allPatients.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
                <button type="submit" className="h-9 rounded-btn bg-brand-turquoise text-white px-4 text-sm font-medium">
                  Atribuir
                </button>
              </form>
              {assignError && <p className="text-danger text-sm mb-3">{assignError}</p>}
              {assignMessage && <p className="text-success text-sm mb-3">{assignMessage}</p>}

              <div className="text-xs font-semibold uppercase text-neutralState mb-2">Pacientes já atribuídos</div>
              <ul className="text-sm space-y-1">
                {atPatients?.map((p) => <li key={p.id}>{p.name}</li>)}
                {atPatients?.length === 0 && <li className="text-neutralState">Nenhum paciente atribuído ainda.</li>}
              </ul>
            </>
          )}
        </div>
      </div>

      <div className="bg-white rounded-card shadow-card p-6">
        <h2 className="font-semibold text-brand-navy mb-1">Tentativas recentes registradas por ATs</h2>
        <p className="text-xs text-neutralState mb-4">
          Visão de acompanhamento/revisão — não bloqueia nem altera os indicadores clínicos.
        </p>
        {trials.length === 0 ? (
          <p className="text-neutralState text-sm">Nenhuma tentativa registrada por AT ainda.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-neutralState border-b border-slate-100">
                <th className="py-2">AT</th>
                <th className="py-2">Paciente</th>
                <th className="py-2">Treino</th>
                <th className="py-2">Resultado</th>
                <th className="py-2">Quando</th>
              </tr>
            </thead>
            <tbody>
              {trials.map((entry) => (
                <tr key={entry.trial_id} className="border-b border-slate-50">
                  <td className="py-2">{entry.at_name}</td>
                  <td className="py-2">{entry.patient_name}</td>
                  <td className="py-2">{entry.training_title}</td>
                  <td className="py-2">{RESULT_LABELS[entry.result] ?? entry.result}</td>
                  <td className="py-2 text-neutralState">{formatDateTime(entry.recorded_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
