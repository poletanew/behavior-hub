import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { apiRequest } from "../api/client";
import { ClinicalSession, Patient, SessionTrainingProgress, Training } from "../types";
import VoiceDictationButton from "../components/VoiceDictationButton";
import {
  flushQueue,
  getQueuedTrials,
  hasPendingSync,
  isNetworkError,
  queueTrial,
  subscribeQueueChanges,
} from "../offline/offlineQueue";

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
  const [pendingCount, setPendingCount] = useState(0);

  function load() {
    apiRequest<SessionTrainingProgress>(`/session-trainings/${sessionTrainingId}/progress`).then(setProgress);
    setPendingCount(getQueuedTrials(sessionTrainingId).length);
  }

  useEffect(load, [sessionTrainingId]);

  useEffect(() => subscribeQueueChanges(load), [sessionTrainingId]);

  async function addTrial() {
    const payload = { result, prompt_level: promptLevel, notes: notes || null };
    try {
      await apiRequest(`/session-trainings/${sessionTrainingId}/trials`, { method: "POST", body: payload });
    } catch (err) {
      if (isNetworkError(err)) {
        // Seção 32.5 — sem conexão: registra localmente e sincroniza depois.
        queueTrial(sessionTrainingId, payload);
      } else {
        throw err;
      }
    }
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
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-brand-navy">Treino: {trainingTitle}</h3>
        {pendingCount > 0 && (
          <span className="text-[10px] uppercase font-semibold px-2 py-1 rounded-full bg-warning/10 text-warning">
            {pendingCount} tentativa(s) aguardando sincronização
          </span>
        )}
      </div>

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
        {getQueuedTrials(sessionTrainingId).map((queued) => (
          <li
            key={queued.localId}
            className="flex items-center justify-between border border-dashed border-warning rounded-btn px-3 py-2 text-sm bg-warning/5"
          >
            <div>
              <span className="font-medium">Tentativa (offline)</span> —{" "}
              <span>Nível de ajuda: {PROMPT_LABELS[queued.payload.prompt_level]}</span> —{" "}
              <span>Resultado: {RESULT_LABELS[queued.payload.result]}</span>
              <div className="text-warning text-xs mt-1">Aguardando conexão para sincronizar</div>
            </div>
          </li>
        ))}
        {progress.trials.length === 0 && getQueuedTrials(sessionTrainingId).length === 0 && (
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
          <div className="flex gap-2">
            <input
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full h-9 rounded-btn border border-slate-300 px-2 text-sm"
            />
            <VoiceDictationButton
              onTranscript={(transcript) => setNotes((prev) => (prev ? `${prev} ${transcript}` : transcript))}
            />
          </div>
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
  const navigate = useNavigate();
  const [session, setSession] = useState<ClinicalSession | null>(null);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [trainings, setTrainings] = useState<Training[]>([]);
  const [pendingSync, setPendingSync] = useState(hasPendingSync());
  const [showSaveTemplate, setShowSaveTemplate] = useState(false);
  const [templateName, setTemplateName] = useState("");
  const [duplicateDate, setDuplicateDate] = useState("");
  const [showDuplicate, setShowDuplicate] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    apiRequest<ClinicalSession>(`/sessions/${sessionId}`).then(async (s) => {
      setSession(s);
      const p = await apiRequest<Patient>(`/patients/${s.patient_id}`);
      setPatient(p);
    });
    apiRequest<Training[]>("/trainings").then(setTrainings);
  }, [sessionId]);

  useEffect(() => {
    const update = () => setPendingSync(hasPendingSync());
    update();
    return subscribeQueueChanges(update);
  }, []);

  async function handleSyncNow() {
    await flushQueue();
    setPendingSync(hasPendingSync());
  }

  async function handleSaveTemplate(e: FormEvent) {
    e.preventDefault();
    if (!sessionId) return;
    await apiRequest(`/sessions/${sessionId}/save-as-template`, { method: "POST", body: { name: templateName } });
    setShowSaveTemplate(false);
    setTemplateName("");
    setMessage("Modelo de atendimento salvo com sucesso.");
  }

  async function handleDuplicate(e: FormEvent) {
    e.preventDefault();
    if (!sessionId) return;
    const newSession = await apiRequest<ClinicalSession>(`/sessions/${sessionId}/duplicate`, {
      method: "POST",
      body: { occurred_at: new Date(duplicateDate).toISOString() },
    });
    navigate(`/sessions/${newSession.id}`);
  }

  if (!session) return <p className="text-neutralState">Carregando...</p>;

  return (
    <div>
      <Link to="/sessions" className="text-sm text-brand-blue underline mb-4 inline-block">
        ← Voltar para Atendimentos
      </Link>

      {pendingSync && (
        <div className="bg-warning/10 border border-warning rounded-card p-3 mb-4 text-sm flex items-center justify-between">
          <span>Há tentativas registradas offline aguardando sincronização.</span>
          <button onClick={handleSyncNow} className="rounded-btn bg-warning text-white px-3 py-1 text-xs font-medium">
            Sincronizar agora
          </button>
        </div>
      )}

      <div className="bg-white rounded-card shadow-sm p-6 mb-6">
        <div className="flex items-start justify-between">
          <div>
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
          <div className="flex gap-2">
            <button
              onClick={() => setShowSaveTemplate((v) => !v)}
              className="rounded-btn bg-white border border-slate-300 px-3 py-2 text-xs font-medium"
            >
              Salvar como modelo
            </button>
            <button
              onClick={() => setShowDuplicate((v) => !v)}
              className="rounded-btn bg-white border border-slate-300 px-3 py-2 text-xs font-medium"
            >
              Duplicar sessão
            </button>
          </div>
        </div>

        {message && <p className="text-success text-sm mt-3">{message}</p>}

        {showSaveTemplate && (
          <form onSubmit={handleSaveTemplate} className="flex gap-2 items-end mt-4 border-t border-slate-100 pt-4">
            <div className="flex-1">
              <label className="block text-xs font-medium mb-1">Nome do modelo</label>
              <input
                required
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                className="w-full h-9 rounded-btn border border-slate-300 px-2 text-sm"
              />
            </div>
            <button type="submit" className="h-9 rounded-btn bg-brand-turquoise text-white px-4 text-sm font-medium">
              Salvar
            </button>
          </form>
        )}

        {showDuplicate && (
          <form onSubmit={handleDuplicate} className="flex gap-2 items-end mt-4 border-t border-slate-100 pt-4">
            <div className="flex-1">
              <label className="block text-xs font-medium mb-1">Nova data e hora</label>
              <input
                type="datetime-local"
                required
                value={duplicateDate}
                onChange={(e) => setDuplicateDate(e.target.value)}
                className="w-full h-9 rounded-btn border border-slate-300 px-2 text-sm"
              />
            </div>
            <button type="submit" className="h-9 rounded-btn bg-brand-turquoise text-white px-4 text-sm font-medium">
              Criar sessão duplicada
            </button>
          </form>
        )}

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
