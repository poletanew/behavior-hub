import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { apiRequest, apiUpload, ApiError } from "../api/client";
import {
  BehaviorEvent,
  BehaviorIntensity,
  ClinicalSession,
  Patient,
  Reinforcer,
  SessionMediaUrl,
  SessionReinforcer,
  SessionTrainingProgress,
  Training,
} from "../types";
import VoiceDictationButton from "../components/VoiceDictationButton";
import {
  flushQueue,
  getQueuedTrials,
  hasPendingSync,
  isNetworkError,
  queueTrial,
  subscribeQueueChanges,
} from "../offline/offlineQueue";

const INTENSITY_LABELS: Record<BehaviorIntensity, string> = { baixa: "Baixa", media: "Média", alta: "Alta" };

function formatSeconds(seconds: number | null) {
  if (!seconds) return "";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}min ${s}s` : `${s}s`;
}

function SessionMediaCard({ sessionId, session }: { sessionId: string; session: ClinicalSession }) {
  const [mediaUrl, setMediaUrl] = useState<SessionMediaUrl | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [durationSeconds, setDurationSeconds] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function load() {
    if (!session.media_type) {
      setMediaUrl(null);
      return;
    }
    apiRequest<SessionMediaUrl>(`/sessions/${sessionId}/media-url`)
      .then(setMediaUrl)
      .catch(() => setMediaUrl(null));
  }

  useEffect(load, [sessionId, session.media_type]);

  const isVideo = file?.type.startsWith("video/");

  async function handleUpload(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setError(null);
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (isVideo) formData.append("duration_seconds", durationSeconds);
      await apiUpload(`/sessions/${sessionId}/media`, formData);
      setFile(null);
      setDurationSeconds("");
      // A resposta já traz a sessão atualizada, mas o objeto `session` do
      // componente pai só é reatualizado no próximo fetch; busca a URL
      // assinada diretamente em vez de depender de session.media_type.
      const updated = await apiRequest<SessionMediaUrl>(`/sessions/${sessionId}/media-url`);
      setMediaUrl(updated);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("Foto/vídeo não disponível no plano Free.");
      } else if (err instanceof ApiError && err.status === 422) {
        setError(err.message || "Arquivo excede o limite do plano.");
      } else {
        setError("Não foi possível enviar o arquivo.");
      }
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="bg-white rounded-card shadow-card p-6 mb-6">
      <h3 className="font-semibold text-brand-navy mb-3">Foto/Vídeo</h3>
      {mediaUrl && (
        <div className="mb-4">
          {mediaUrl.media_type === "photo" ? (
            <img src={mediaUrl.url} alt="Foto do atendimento" className="max-h-64 rounded-btn border border-slate-200" />
          ) : (
            <video src={mediaUrl.url} controls className="max-h-64 rounded-btn border border-slate-200" />
          )}
          {mediaUrl.duration_seconds && (
            <p className="text-xs text-neutralState mt-1">Duração: {formatSeconds(mediaUrl.duration_seconds)}</p>
          )}
        </div>
      )}
      {error && <p className="text-danger text-sm mb-2">{error}</p>}
      <form onSubmit={handleUpload} className="flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs font-medium mb-1">{mediaUrl ? "Substituir por novo arquivo" : "Anexar foto ou vídeo curto"}</label>
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-sm file:mr-2 file:rounded-btn file:border-0 file:bg-brand-turquoise file:text-white file:px-3 file:py-1.5 file:text-xs file:font-medium"
          />
        </div>
        {isVideo && (
          <div>
            <label className="block text-xs font-medium mb-1">Duração (segundos)</label>
            <input
              type="number"
              min={1}
              required
              value={durationSeconds}
              onChange={(e) => setDurationSeconds(e.target.value)}
              className="h-9 w-24 rounded-btn border border-slate-300 px-2 text-sm"
            />
          </div>
        )}
        <button
          type="submit"
          disabled={!file || uploading}
          className="h-9 rounded-btn bg-brand-turquoise text-white px-4 text-sm font-medium disabled:opacity-50"
        >
          {uploading ? "Enviando..." : "Enviar"}
        </button>
      </form>
    </div>
  );
}

function BehaviorEventsCard({ sessionId, patientId }: { sessionId: string; patientId: string }) {
  const [events, setEvents] = useState<BehaviorEvent[]>([]);
  const [antecedent, setAntecedent] = useState("");
  const [behavior, setBehavior] = useState("");
  const [consequence, setConsequence] = useState("");
  const [frequencyCount, setFrequencyCount] = useState("");
  const [durationSeconds, setDurationSeconds] = useState("");
  const [intensity, setIntensity] = useState<BehaviorIntensity | "">("");
  const [showForm, setShowForm] = useState(false);

  function load() {
    apiRequest<BehaviorEvent[]>(`/sessions/${sessionId}/behavior-events`).then(setEvents);
  }

  useEffect(load, [sessionId]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    await apiRequest(`/patients/${patientId}/behavior-events`, {
      method: "POST",
      body: {
        session_id: sessionId,
        antecedent,
        behavior,
        consequence,
        frequency_count: frequencyCount ? Number(frequencyCount) : null,
        duration_seconds: durationSeconds ? Number(durationSeconds) : null,
        intensity: intensity || null,
      },
    });
    setAntecedent("");
    setBehavior("");
    setConsequence("");
    setFrequencyCount("");
    setDurationSeconds("");
    setIntensity("");
    setShowForm(false);
    load();
  }

  return (
    <div className="bg-white rounded-card shadow-card p-6 mb-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-brand-navy">Comportamento-alvo (modelo ABC)</h3>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-btn bg-white border border-slate-300 px-3 py-1.5 text-xs font-medium"
        >
          + Registrar evento ABC
        </button>
      </div>

      <ul className="space-y-2 mb-3">
        {events.map((event) => (
          <li key={event.id} className="border border-slate-100 rounded-btn px-3 py-2 text-sm">
            <div>
              <span className="font-medium">Antecedente:</span> {event.antecedent}
            </div>
            <div>
              <span className="font-medium">Comportamento:</span> {event.behavior}
            </div>
            <div>
              <span className="font-medium">Consequência:</span> {event.consequence}
            </div>
            <div className="text-xs text-neutralState mt-1 flex gap-3">
              {event.frequency_count !== null && <span>Frequência: {event.frequency_count}x</span>}
              {event.duration_seconds !== null && <span>Duração: {formatSeconds(event.duration_seconds)}</span>}
              {event.intensity && <span>Intensidade: {INTENSITY_LABELS[event.intensity]}</span>}
            </div>
          </li>
        ))}
        {events.length === 0 && !showForm && (
          <li className="text-neutralState text-sm">Nenhum evento ABC registrado nesta sessão ainda.</li>
        )}
      </ul>

      {showForm && (
        <form onSubmit={handleSubmit} className="space-y-3 border-t border-slate-100 pt-4">
          <div>
            <label className="block text-xs font-medium mb-1">Antecedente (o que aconteceu antes)</label>
            <input
              required
              value={antecedent}
              onChange={(e) => setAntecedent(e.target.value)}
              className="w-full h-9 rounded-btn border border-slate-300 px-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Comportamento</label>
            <input
              required
              value={behavior}
              onChange={(e) => setBehavior(e.target.value)}
              className="w-full h-9 rounded-btn border border-slate-300 px-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Consequência (o que aconteceu depois)</label>
            <input
              required
              value={consequence}
              onChange={(e) => setConsequence(e.target.value)}
              className="w-full h-9 rounded-btn border border-slate-300 px-2 text-sm"
            />
          </div>
          <div className="flex flex-wrap gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Frequência</label>
              <input
                type="number"
                min={0}
                value={frequencyCount}
                onChange={(e) => setFrequencyCount(e.target.value)}
                className="h-9 w-24 rounded-btn border border-slate-300 px-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Duração (segundos)</label>
              <input
                type="number"
                min={0}
                value={durationSeconds}
                onChange={(e) => setDurationSeconds(e.target.value)}
                className="h-9 w-28 rounded-btn border border-slate-300 px-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Intensidade</label>
              <select
                value={intensity}
                onChange={(e) => setIntensity(e.target.value as BehaviorIntensity | "")}
                className="h-9 rounded-btn border border-slate-300 px-2 text-sm"
              >
                <option value="">Não informada</option>
                {Object.entries(INTENSITY_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <button type="submit" className="h-9 rounded-btn bg-brand-turquoise text-white px-4 text-sm font-medium">
            Salvar evento
          </button>
        </form>
      )}
    </div>
  );
}

function SessionReinforcersCard({ sessionId, patientId }: { sessionId: string; patientId: string }) {
  const [used, setUsed] = useState<SessionReinforcer[]>([]);
  const [available, setAvailable] = useState<Reinforcer[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [note, setNote] = useState("");
  const [newName, setNewName] = useState("");
  const [showNewForm, setShowNewForm] = useState(false);

  function load() {
    apiRequest<SessionReinforcer[]>(`/sessions/${sessionId}/reinforcers`).then(setUsed);
    apiRequest<Reinforcer[]>(`/patients/${patientId}/reinforcers`).then(setAvailable);
  }

  useEffect(load, [sessionId, patientId]);

  async function handleLink(e: FormEvent) {
    e.preventDefault();
    if (!selectedId) return;
    await apiRequest(`/sessions/${sessionId}/reinforcers`, {
      method: "POST",
      body: { reinforcer_id: selectedId, effectiveness_note: note || null },
    });
    setSelectedId("");
    setNote("");
    load();
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    await apiRequest(`/patients/${patientId}/reinforcers`, { method: "POST", body: { name: newName } });
    setNewName("");
    setShowNewForm(false);
    load();
  }

  return (
    <div className="bg-white rounded-card shadow-card p-6 mb-6">
      <h3 className="font-semibold text-brand-navy mb-3">Reforçadores usados nesta sessão</h3>
      <ul className="space-y-2 mb-3">
        {used.map((u) => (
          <li key={u.id} className="border border-slate-100 rounded-btn px-3 py-2 text-sm">
            <span className="font-medium">{u.reinforcer_name}</span>
            {u.effectiveness_note && <span className="text-neutralState"> — {u.effectiveness_note}</span>}
          </li>
        ))}
        {used.length === 0 && <li className="text-neutralState text-sm">Nenhum reforçador registrado nesta sessão ainda.</li>}
      </ul>

      <form onSubmit={handleLink} className="flex flex-wrap items-end gap-2 mb-2">
        <div>
          <label className="block text-xs font-medium mb-1">Reforçador</label>
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            className="h-9 rounded-btn border border-slate-300 px-2 text-sm"
          >
            <option value="">Selecione...</option>
            {available.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name} ({r.usage_count}x usado)
              </option>
            ))}
          </select>
        </div>
        <div className="flex-1 min-w-[160px]">
          <label className="block text-xs font-medium mb-1">Nota de efetividade (opcional)</label>
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="w-full h-9 rounded-btn border border-slate-300 px-2 text-sm"
          />
        </div>
        <button type="submit" className="h-9 rounded-btn bg-brand-turquoise text-white px-4 text-sm font-medium">
          Vincular
        </button>
      </form>

      {!showNewForm ? (
        <button onClick={() => setShowNewForm(true)} className="text-xs text-brand-blue underline">
          + Cadastrar novo reforçador para este paciente
        </button>
      ) : (
        <form onSubmit={handleCreate} className="flex items-end gap-2 mt-2">
          <div className="flex-1">
            <label className="block text-xs font-medium mb-1">Nome do reforçador</label>
            <input
              required
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="w-full h-9 rounded-btn border border-slate-300 px-2 text-sm"
            />
          </div>
          <button type="submit" className="h-9 rounded-btn bg-white border border-slate-300 px-3 text-xs font-medium">
            Cadastrar
          </button>
        </form>
      )}
    </div>
  );
}

const RESULT_LABELS: Record<string, string> = {
  correct: "Correta",
  incorrect: "Incorreta",
  partial: "Parcial",
  no_response: "Não respondida",
};

// Botões grandes em grade, otimizados para toque com o polegar — padrão
// "uma mão só" de apps de coleta ABA de mercado, em vez de um <select>.
const RESULT_BUTTON_STYLES: Record<string, string> = {
  correct: "bg-success text-white border-success",
  incorrect: "bg-danger text-white border-danger",
  partial: "bg-warning text-white border-warning",
  no_response: "bg-slate-400 text-white border-slate-400",
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
    <div className="bg-white rounded-card shadow-card p-6 mb-6">
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

      <div className="mb-3">
        <label className="block text-xs font-medium mb-1">Nível de ajuda</label>
        <select
          value={promptLevel}
          onChange={(e) => setPromptLevel(e.target.value)}
          className="h-9 rounded-btn border border-slate-300 px-2 text-sm w-full max-w-xs"
        >
          {Object.entries(PROMPT_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <div className="mb-3">
        <label className="block text-xs font-medium mb-1">Resultado</label>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 max-w-lg">
          {Object.entries(RESULT_LABELS).map(([value, label]) => (
            <button
              key={value}
              type="button"
              onClick={() => setResult(value)}
              className={`min-h-[56px] rounded-card border-2 text-sm font-bold transition-opacity ${
                result === value ? RESULT_BUTTON_STYLES[value] : "bg-white text-brand-graphite border-slate-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap items-end gap-3 mb-3">
        <div className="flex-1 min-w-[200px]">
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

      <div className="bg-white rounded-card shadow-card p-6 mb-6">
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

      <SessionMediaCard sessionId={session.id} session={session} />
      {patient && <BehaviorEventsCard sessionId={session.id} patientId={patient.id} />}
      {patient && <SessionReinforcersCard sessionId={session.id} patientId={patient.id} />}

      {session.trainings.map((st) => {
        const training = trainings.find((t) => t.id === st.training_id);
        return (
          <TrainingTrialsCard key={st.id} sessionTrainingId={st.id} trainingTitle={training?.title || "Treino"} />
        );
      })}
    </div>
  );
}
