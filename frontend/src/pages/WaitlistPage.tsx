import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiRequest, ApiError } from "../api/client";
import EmptyState from "../components/EmptyState";
import { WaitlistEntry } from "../types";

const STATUS_LABELS: Record<string, string> = {
  waiting: "Aguardando",
  converted: "Convertido",
  discarded: "Descartado",
};

const STATUS_COLORS: Record<string, string> = {
  waiting: "bg-amber-100 text-amber-700",
  converted: "bg-success/10 text-success",
  discarded: "bg-slate-200 text-neutralState",
};

export default function WaitlistPage() {
  const navigate = useNavigate();
  const [entries, setEntries] = useState<WaitlistEntry[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [guardianName, setGuardianName] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [convertingId, setConvertingId] = useState<string | null>(null);
  const [convertBirthDate, setConvertBirthDate] = useState("");
  const [convertDiagnosis, setConvertDiagnosis] = useState("");
  const [convertError, setConvertError] = useState<string | null>(null);

  function load() {
    apiRequest<WaitlistEntry[]>("/waitlist").then(setEntries);
  }

  useEffect(load, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiRequest("/waitlist", {
        method: "POST",
        body: {
          name,
          birth_date: birthDate || null,
          guardian_name: guardianName || null,
          contact_phone: contactPhone || null,
          contact_email: contactEmail || null,
          notes: notes || null,
        },
      });
      setShowForm(false);
      setName("");
      setBirthDate("");
      setGuardianName("");
      setContactPhone("");
      setContactEmail("");
      setNotes("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? String(err.detail) : "Não foi possível adicionar à lista de espera.");
    }
  }

  async function handleDiscard(id: string) {
    await apiRequest(`/waitlist/${id}/discard`, { method: "POST" });
    load();
  }

  function startConvert(entry: WaitlistEntry) {
    setConvertingId(entry.id);
    setConvertBirthDate(entry.birth_date ?? "");
    setConvertDiagnosis("");
    setConvertError(null);
  }

  async function handleConvert(e: FormEvent) {
    e.preventDefault();
    if (!convertingId) return;
    setConvertError(null);
    try {
      const result = await apiRequest<WaitlistEntry>(`/waitlist/${convertingId}/convert`, {
        method: "POST",
        body: { birth_date: convertBirthDate || null, diagnosis: convertDiagnosis || null },
      });
      setConvertingId(null);
      if (result.converted_patient_id) {
        navigate(`/patients/${result.converted_patient_id}`);
      } else {
        load();
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        setConvertError("Informe a data de nascimento para converter em paciente.");
      } else {
        setConvertError("Não foi possível converter em paciente.");
      }
    }
  }

  const waiting = entries.filter((e) => e.status === "waiting");
  const others = entries.filter((e) => e.status !== "waiting");

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-brand-navy">Lista de Espera</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium"
        >
          + Adicionar à lista
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="bg-white rounded-card shadow-card p-6 mb-6 space-y-4 max-w-lg">
          <div>
            <label className="block text-sm font-medium mb-1">Nome</label>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full h-10 rounded-btn border border-slate-300 px-3"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Data de nascimento (se já souber)</label>
            <input
              type="date"
              value={birthDate}
              onChange={(e) => setBirthDate(e.target.value)}
              className="w-full h-10 rounded-btn border border-slate-300 px-3"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Responsável</label>
            <input
              value={guardianName}
              onChange={(e) => setGuardianName(e.target.value)}
              className="w-full h-10 rounded-btn border border-slate-300 px-3"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium mb-1">Telefone de contato</label>
              <input
                value={contactPhone}
                onChange={(e) => setContactPhone(e.target.value)}
                className="w-full h-10 rounded-btn border border-slate-300 px-3"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">E-mail de contato</label>
              <input
                type="email"
                value={contactEmail}
                onChange={(e) => setContactEmail(e.target.value)}
                className="w-full h-10 rounded-btn border border-slate-300 px-3"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Observações / motivo do encaminhamento</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full rounded-btn border border-slate-300 px-3 py-2"
            />
          </div>
          {error && <p className="text-danger text-sm">{error}</p>}
          <button type="submit" className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium">
            Salvar
          </button>
        </form>
      )}

      {waiting.length === 0 && others.length === 0 ? (
        <EmptyState icon="🗓️" message="Nenhum paciente na lista de espera." />
      ) : (
        <div className="space-y-3">
          {[...waiting, ...others].map((entry) => (
            <div key={entry.id} className="bg-white rounded-card shadow-card p-4">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-semibold text-brand-navy">{entry.name}</span>
                  {entry.guardian_name && (
                    <span className="text-neutralState text-sm"> — responsável: {entry.guardian_name}</span>
                  )}
                </div>
                <span className={`rounded px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[entry.status]}`}>
                  {STATUS_LABELS[entry.status]}
                </span>
              </div>
              {(entry.contact_phone || entry.contact_email) && (
                <p className="text-xs text-neutralState mt-1">
                  {[entry.contact_phone, entry.contact_email].filter(Boolean).join(" · ")}
                </p>
              )}
              {entry.notes && <p className="text-sm mt-2">{entry.notes}</p>}

              {entry.status === "waiting" && (
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={() => startConvert(entry)}
                    className="rounded-btn bg-success text-white px-3 py-1.5 text-xs font-medium"
                  >
                    Converter em paciente
                  </button>
                  <button
                    onClick={() => handleDiscard(entry.id)}
                    className="rounded-btn bg-white border border-slate-300 px-3 py-1.5 text-xs font-medium"
                  >
                    Descartar
                  </button>
                </div>
              )}

              {convertingId === entry.id && (
                <form onSubmit={handleConvert} className="flex gap-2 items-end mt-3 border-t border-slate-100 pt-3">
                  {!entry.birth_date && (
                    <div>
                      <label className="block text-xs font-medium mb-1">Data de nascimento</label>
                      <input
                        type="date"
                        required
                        value={convertBirthDate}
                        onChange={(e) => setConvertBirthDate(e.target.value)}
                        className="h-9 rounded-btn border border-slate-300 px-2 text-sm"
                      />
                    </div>
                  )}
                  <div className="flex-1">
                    <label className="block text-xs font-medium mb-1">Diagnóstico (opcional)</label>
                    <input
                      value={convertDiagnosis}
                      onChange={(e) => setConvertDiagnosis(e.target.value)}
                      className="w-full h-9 rounded-btn border border-slate-300 px-2 text-sm"
                    />
                  </div>
                  <button type="submit" className="h-9 rounded-btn bg-brand-turquoise text-white px-4 text-sm font-medium">
                    Confirmar conversão
                  </button>
                  {convertError && <p className="text-danger text-xs">{convertError}</p>}
                </form>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
