import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiRequest } from "../api/client";
import { ClinicalSession, Patient, SessionTrainingProgress, Training } from "../types";

const RESULT_LABELS: Record<string, string> = {
  correct: "Correta",
  incorrect: "Incorreta",
  partial: "Parcial",
  no_response: "Não respondida",
};

const PROMPT_LABELS: Record<string, string> = {
  independent: "Independente",
  gestural: "Ajuda gestual",
  verbal: "Ajuda verbal",
  modeling: "Modelação",
  partial_physical: "Física parcial",
  full_physical: "Física total",
};

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("pt-BR");
}

function TrainingTrialsCard({
  sessionTrainingId,
  trainingTitle,
}: {
  sessionTrainingId: string;
  trainingTitle: string;
}) {
  const [progress, setProgress] = useState<SessionTrainingProgress | null>(null);
  const [result, setResult] = useState("correct");
  const [promptLevel, setPromptLevel] = useState("independent");
  const [notes, setNotes] = useState("");

  function load() {
    apiRequest<SessionTrainingProgress>(`/session-trainings/${sessionTrainingId}/progress`).then(setProgress);
  }

  useEffect(load, [sessionTrainingId]);

  async function addTrial() {
    await apiRequest(`/session-trainings/${sessionTrainingId}/trials`, {
      method: "POST",
      body: { result, prompt_level: promptLevel, notes: notes || null },
    });
    setNotes("");
    load();
  }

  async function removeTrial(trialId: string) {
    await apiRequest(`/trials/${trialId}`, { method: "DELETE" });
    load();
  }

  if (!progress) return null;

  return (
    <div className="bg-white rounded-card shadow-sm p-6 mb-6">
      <h3 className="font-semibold text-brand-navy mb-4">Treino: {trainingTitle}</h3>

      <ul className="space-y-2 mb-4">
        {progress.trials.map((trial) => (
          <li key={trial.id} className="flex items-center justify-between border border-slate-100 rounded-btn px-3 py-2 text-sm">
            <div>
              <span className="font-medium">Tentativa {trial.attempt_number}</span> —{" "}
              <span>Nível de ajuda: {PROMPT_LABELS[trial.prompt_level]}</span> —{" "}
              <span>Resultado: {RESULT_LABELS[trial.result]}</span>
              {trial.notes && <div className="text-neutralState text-xs mt-1">{trial.notes}</div>}
            </div>
            <button onClick={() => removeTrial(trial.id)} className="text-danger text-xs hover:underline">
              Remover
            </button>
          </li>
        ))}
        {progress.trials.length === 0 && (
          <li className="text-neutralState text-sm">Nenhuma tentativa registrada ainda para este treino.</li>
        )}
      </ul>

      <div className="flex flex-wrap items-end gap-3 mb-3">
        <div>
          <label className="block text-xs font-medium mb-1">Resultado</label>
          <select value={result} onChange={(e) => setResult(e.target.value)} className="h-9 rounded-btn border border-slate-300 px-2 text-sm">
            {Object.entries(RESULT_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">Nível de ajuda</label>
          <select
            value={promptLevel}
            onChange={(e) => setPromptLevel(e.target.value)}
            className="h-9 rounded-btn border border-slate-300 px-2 text-sm"
          >
            {Object.entries(PROMPT_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex-1 min-w-[160px]">
          <label className="block text-xs font-medium mb-1">Observação (opcional)</label>
          <input
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full h-9 rounded-btn border border-slate-300 px-2 text-sm"
          />
        </div>
        <button onClick={addTrial} className="h-9 rounded-btn bg-brand-turquoise text-white px-4 text-sm font-medium">
          + Adicionar tentativa
        </button>
      </div>

      <div className="flex gap-6 text-sm font-medium text-brand-navy">
        <span>Percentual de acerto: {progress.accuracy_pct !== null ? `${progress.accuracy_pct}%` : "-"}</span>
        <span>Independência: {progress.independence_pct !== null ? `${progress.independence_pct}%` : "-"}</span>
      </div>
    </div>
  );
}

export default function SessionDetailPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [session, setSession] = useState<ClinicalSession | null>(null);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [trainings, setTrainings] = useState<Training[]>([]);

  useEffect(() => {
    if (!sessionId) return;
    apiRequest<ClinicalSession>(`/sessions/${sessionId}`).then(async (s) => {
      setSession(s);
      const p = await apiRequest<Patient>(`/patients/${s.patient_id}`);
      setPatient(p);
    });
    apiRequest<Training[]>("/trainings").then(setTrainings);
  }, [sessionId]);

  if (!session) return <p className="text-neutralState">Carregando...</p>;

  return (
    <div>
      <Link to="/sessions" className="text-sm text-brand-blue underline mb-4 inline-block">
        ← Voltar para Atendimentos
      </Link>

      <div className="bg-white rounded-card shadow-sm p-6 mb-6">
        <h1 className="text-2xl font-bold text-brand-navy">
          {patient ? (
            <Link to={`/patients/${patient.id}`} className="hover:underline">
              {patient.name}
            </Link>
          ) : (
            "Atendimento"
          )}
        </h1>
        <p className="text-neutralState text-sm mt-1">{formatDateTime(session.occurred_at)}</p>
        {session.notes && <p className="text-sm mt-2">{session.notes}</p>}
      </div>

      {session.trainings.map((st) => {
        const training = trainings.find((t) => t.id === st.training_id);
        return (
          <TrainingTrialsCard key={st.id} sessionTrainingId={st.id} trainingTitle={training?.title || "Treino"} />
        );
      })}
    </div>
  );
}
