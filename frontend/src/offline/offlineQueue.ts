import { apiRequest, ApiError } from "../api/client";

/**
 * Seção 32.5 — Modo Offline/Coleta em Tablet sem Conexão.
 * Fila local de tentativas registradas offline, sincronizada automaticamente ao
 * restabelecer conexão. Como a criação de tentativa é sempre aditiva (próximo
 * attempt_number), não existe conflito de sobrescrita — cada item da fila vira
 * uma nova tentativa quando sincronizado, nunca substitui uma existente.
 */

export interface QueuedTrialPayload {
  result: string;
  prompt_level: string;
  notes: string | null;
}

interface QueuedTrial {
  localId: string;
  sessionTrainingId: string;
  payload: QueuedTrialPayload;
  queuedAt: string;
}

const STORAGE_KEY = "bh_offline_trial_queue";
const EVENT_NAME = "bh-offline-queue-changed";

function readQueue(): QueuedTrial[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}

function writeQueue(queue: QueuedTrial[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(queue));
  window.dispatchEvent(new Event(EVENT_NAME));
}

export function isNetworkError(err: unknown): boolean {
  // fetch() rejects with a TypeError when the request never reached a server
  // (offline, DNS failure, CORS). Server-side errors surface as ApiError instead.
  return !(err instanceof ApiError);
}

export function getQueuedTrials(sessionTrainingId: string): QueuedTrial[] {
  return readQueue().filter((q) => q.sessionTrainingId === sessionTrainingId);
}

export function hasPendingSync(): boolean {
  return readQueue().length > 0;
}

export function queueTrial(sessionTrainingId: string, payload: QueuedTrialPayload) {
  const queue = readQueue();
  queue.push({
    localId: crypto.randomUUID(),
    sessionTrainingId,
    payload,
    queuedAt: new Date().toISOString(),
  });
  writeQueue(queue);
}

export function subscribeQueueChanges(callback: () => void): () => void {
  window.addEventListener(EVENT_NAME, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(EVENT_NAME, callback);
    window.removeEventListener("storage", callback);
  };
}

let flushing = false;

export async function flushQueue(onItemSynced?: (sessionTrainingId: string) => void): Promise<void> {
  if (flushing || !navigator.onLine) return;
  flushing = true;
  try {
    const queue = readQueue();
    if (queue.length === 0) return;
    const remaining: QueuedTrial[] = [];
    for (const item of queue) {
      try {
        await apiRequest(`/session-trainings/${item.sessionTrainingId}/trials`, {
          method: "POST",
          body: item.payload,
        });
        onItemSynced?.(item.sessionTrainingId);
      } catch (err) {
        if (isNetworkError(err)) {
          remaining.push(item); // still offline — keep for the next retry
        }
        // A server-side rejection (ApiError) drops the item instead of retrying forever.
      }
    }
    writeQueue(remaining);
  } finally {
    flushing = false;
  }
}

export function initOfflineSync(onItemSynced?: (sessionTrainingId: string) => void): void {
  window.addEventListener("online", () => flushQueue(onItemSynced));
  if (navigator.onLine) flushQueue(onItemSynced);
}
