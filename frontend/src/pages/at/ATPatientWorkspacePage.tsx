import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiRequest } from "../../api/client";
import { ClinicalSession, SessionTrainingProgress, TrainingPatientLink } from "../../types";

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

function TrialRegistrationCard({ sessionTrainingId, trainingTitle }: { sessionTrainingId: string; trainingTitle: string }) {
  const [progress, setProgress] = useState<SessionTrainingProgress | null>(null);
  const [result, setResult] = useState("correct");
  const [promptLevel, setPromptLevel] = useState("independent");

  function load() {
    apiRequest<SessionTrainingProgress>(`/session-trainings/${sessionTrainingId}/progress`).then(setProgress);
  }

  useEffect(load, [sessionTrainingId]);

  async function addTrial() {
    await apiRequest(`/session-trainings/${sessionTrainingId}/trials`, {
      method: "POST",
      body: { result, prompt_level: promptLevel },
    });
    load();
  }

  if (!progress) return null;

  return (
    <div className="bg-white rounded-card shadow-sm p-6 mb-6">
      <h3 className="font-semibold text-brand-navy mb-3">Treino: {trainingTitle}</h3>
      <ul className="space-y-2 mb-4">
        {progress.trials.map((trial) => (
          <li key={trial.id} className="border border-slate-100 rounded-btn px-3 py-2 text-sm">
            <span className="font-medium">Tentativa {trial.attempt_number}</span> —{" "}
            <span>{PROMPT_LABELS[trial.prompt_level]}</span> — <span>{RESULT_LABELS[trial.result]}</span>
          </li>
        ))}
        {progress.trials.length === 0 && (
          <li className="text-neutralState text-sm">Nenhuma tentativa registrada ainda.</li>
        )}
      </ul>
      <div className="flex flex-wrap items-end gap-3">
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
        <button onClick={addTrial} className="h-9 rounded-btn bg-brand-turquoise text-white px-4 text-sm font-medium">
          + Registrar tentativa
        </button>
      </div>
    </div>
  );
}

export default function ATPatientWorkspacePage() {
  const { patientId } = useParams<{ patientId: string }>();
  const [links, setLinks] = useState<TrainingPatientLink[] | null>(null);
  const [activeSession, setActiveSession] = useState<ClinicalSession | null>(null);
  const [error, setError] = useState<string | null>(null);

  function loadLinks() {
    if (!patientId) return;
    apiRequest<TrainingPatientLink[]>(`/at-portal/patients/${patientId}/trainings`).then(setLinks);
  }

  useEffect(loadLinks, [patientId]);

  async function applyTraining(trainingId: string) {
    setError(null);
    try {
      const session = await apiRequest<ClinicalSession>(`/at-portal/patients/${patientId}/apply`, {
        method: "POST",
        body: { training_id: trainingId, occurred_at: new Date().toISOString() },
      });
      setActiveSession(session);
      loadLinks();
    } catch {
      setError("Não foi possível iniciar a aplicação deste treino.");
    }
  }

  return (
    <div>
      <Link to="/at/patients" className="text-sm text-brand-blue underline mb-4 inline-block">
        ← Voltar para Meus pacientes
      </Link>
      <h1 className="text-2xl font-bold text-brand-navy mb-2">Treinos prescritos</h1>
      <p className="text-sm text-neutralState mb-6">
        Escolha um treino prescrito para aplicar e registrar as tentativas desta sessão.
      </p>
      {error && <p className="text-danger text-sm mb-4">{error}</p>}

      {links === null ? (
        <p className="text-neutralState">Carregando...</p>
      ) : links.length === 0 ? (
        <div className="bg-white rounded-card shadow-sm p-10 text-center text-neutralState">
          Nenhum treino prescrito para este paciente ainda.
        </div>
      ) : (
        <div className="bg-white rounded-card shadow-sm divide-y divide-slate-100 mb-6">
          {links.map((link) => {
            const sessionTraining = activeSession?.trainings.find((t) => t.training_id === link.training_id);
            return (
              <div key={link.id} className="px-4 py-3">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-medium">{link.training_title}</span>{" "}
                    <span
                      className={`ml-2 rounded px-1.5 py-0.5 text-[10px] font-medium ${
                        link.status === "applied" ? "bg-success/10 text-success" : "bg-brand-blueLight/20 text-brand-blue"
                      }`}
                    >
                      {link.status === "applied" ? "Aplicado" : "Prescrito"}
                    </span>
                  </div>
                  {!sessionTraining && (
                    <button
                      onClick={() => applyTraining(link.training_id)}
                      className="rounded-btn bg-brand-turquoise text-white px-3 py-1.5 text-xs font-medium"
                    >
                      Aplicar agora
                    </button>
                  )}
                </div>
                {sessionTraining && (
                  <div className="mt-3">
                    <TrialRegistrationCard sessionTrainingId={sessionTraining.id} trainingTitle={link.training_title} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
