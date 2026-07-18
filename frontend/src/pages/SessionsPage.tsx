import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { apiRequest } from "../api/client";
import { ClinicalSession, Patient, Training, TrainingCategory } from "../types";
import { useAuth } from "../context/AuthContext";

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("pt-BR");
}

export default function SessionsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const prefillPatientId = searchParams.get("patient_id") ?? "";
  const prefillProfessionalId = searchParams.get("professional_id") ?? "";
  const prefillAppointmentId = searchParams.get("appointment_id");
  const prefillOccurredAt = searchParams.get("occurred_at") ?? "";

  const [sessions, setSessions] = useState<ClinicalSession[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [categories, setCategories] = useState<TrainingCategory[]>([]);
  const [trainings, setTrainings] = useState<Training[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(Boolean(prefillAppointmentId));
  const [patientId, setPatientId] = useState(prefillPatientId);
  const [occurredAt, setOccurredAt] = useState(prefillOccurredAt);
  const [notes, setNotes] = useState("");
  const [selectedTrainingIds, setSelectedTrainingIds] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<ClinicalSession[]>("/sessions")
      .then(setSessions)
      .finally(() => setLoading(false));
    apiRequest<Patient[]>("/patients").then(setPatients);
    apiRequest<TrainingCategory[]>("/training-categories").then(setCategories);
    apiRequest<Training[]>("/trainings").then(setTrainings);
  }, []);

  function toggleTraining(id: string) {
    setSelectedTrainingIds((prev) => (prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]));
  }

  async function handleCreateSession(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const session = await apiRequest<ClinicalSession>("/sessions", {
        method: "POST",
        body: {
          patient_id: patientId,
          professional_id: prefillProfessionalId || user?.id,
          occurred_at: new Date(occurredAt).toISOString(),
          notes: notes || null,
          training_ids: selectedTrainingIds,
          appointment_id: prefillAppointmentId || undefined,
        },
      });
      navigate(`/sessions/${session.id}`);
    } catch {
      setError("Não foi possível criar o atendimento. Selecione um paciente e ao menos um treino.");
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-brand-navy">Atendimentos</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium"
        >
          Novo Atendimento
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreateSession} className="bg-white rounded-card shadow-sm p-6 mb-6 space-y-4">
          {prefillAppointmentId && (
            <div className="bg-brand-grayLight border border-brand-blueLight rounded-btn p-3 text-sm">
              Concluindo o atendimento agendado na Agenda. Ao salvar, o compromisso será marcado como realizado.
            </div>
          )}
          <div>
            <label className="block text-sm font-medium mb-1">Paciente</label>
            <select
              required
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              className="w-full h-10 rounded-btn border border-slate-300 px-3"
            >
              <option value="">Selecione...</option>
              {patients.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Data e hora</label>
            <input
              type="datetime-local"
              required
              value={occurredAt}
              onChange={(e) => setOccurredAt(e.target.value)}
              className="w-full h-10 rounded-btn border border-slate-300 px-3"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Observações</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full rounded-btn border border-slate-300 px-3 py-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Treinos do dia</label>
            <div className="max-h-64 overflow-y-auto border border-slate-200 rounded-btn divide-y">
              {categories.map((category) => (
                <div key={category.id}>
                  <div className="bg-slate-50 px-3 py-1 text-xs font-semibold uppercase text-neutralState">
                    {category.name}
                  </div>
                  {trainings
                    .filter((t) => t.category_id === category.id)
                    .map((training) => (
                      <label key={training.id} className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-slate-50">
                        <input
                          type="checkbox"
                          checked={selectedTrainingIds.includes(training.id)}
                          onChange={() => toggleTraining(training.id)}
                        />
                        {training.title}
                      </label>
                    ))}
                </div>
              ))}
            </div>
          </div>
          {error && <p className="text-danger text-sm">{error}</p>}
          <div className="flex gap-3">
            <button type="submit" className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium">
              Iniciar atendimento
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-btn bg-white border border-slate-300 px-4 py-2 text-sm font-medium"
            >
              Cancelar
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="text-neutralState">Carregando...</p>
      ) : sessions.length === 0 ? (
        <div className="bg-white rounded-card shadow-sm p-10 text-center text-neutralState">
          Nenhuma sessão registrada ainda.
        </div>
      ) : (
        <div className="bg-white rounded-card shadow-sm divide-y divide-slate-100">
          {sessions.map((session) => {
            const patient = patients.find((p) => p.id === session.patient_id);
            return (
              <Link
                key={session.id}
                to={`/sessions/${session.id}`}
                className="flex justify-between px-4 py-3 hover:bg-slate-50"
              >
                <span>{patient?.name || session.patient_id}</span>
                <span className="text-neutralState text-sm">{formatDateTime(session.occurred_at)}</span>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
