import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { apiRequest } from "../api/client";
import { ClinicalSession, Patient, Training, TrainingCategory, User } from "../types";
import { useAuth } from "../context/AuthContext";
import { professionalDisplayName } from "../utils/specialty";

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
  const [professionals, setProfessionals] = useState<User[]>([]);
  const [categories, setCategories] = useState<TrainingCategory[]>([]);
  const [trainings, setTrainings] = useState<Training[]>([]);
  const [loading, setLoading] = useState(true);
  const [professionalId, setProfessionalId] = useState(prefillProfessionalId);
  const [occurredAt, setOccurredAt] = useState(prefillOccurredAt);
  const [notes, setNotes] = useState("");
  const [selectedTrainingIds, setSelectedTrainingIds] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const showForm = Boolean(prefillPatientId);
  const contextPatient = patients.find((p) => p.id === prefillPatientId);

  useEffect(() => {
    apiRequest<ClinicalSession[]>("/sessions")
      .then(setSessions)
      .finally(() => setLoading(false));
    apiRequest<Patient[]>("/patients").then(setPatients);
    apiRequest<TrainingCategory[]>("/training-categories").then(setCategories);
    apiRequest<Training[]>("/trainings").then(setTrainings);
    apiRequest<User[]>("/professionals").then((list) => {
      setProfessionals(list.filter((p) => p.user_type !== "family"));
    });
  }, []);

  useEffect(() => {
    if (user?.id && !professionalId) setProfessionalId(user.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

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
          patient_id: prefillPatientId,
          professional_id: professionalId || user?.id,
          occurred_at: new Date(occurredAt).toISOString(),
          notes: notes || null,
          training_ids: selectedTrainingIds,
          appointment_id: prefillAppointmentId || undefined,
        },
      });
      navigate(`/sessions/${session.id}`);
    } catch {
      setError("Não foi possível criar o atendimento. Selecione o profissional responsável e ao menos um treino.");
    }
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-brand-navy">Atendimentos</h1>
        {!showForm && (
          <p className="text-sm text-neutralState mt-1">
            Esta é a visão administrativa de todos os atendimentos da clínica. Para iniciar um novo
            atendimento, acesse a{" "}
            <Link to="/patients" className="text-brand-blue underline">
              ficha do paciente
            </Link>{" "}
            ou conclua um compromisso pela Agenda.
          </p>
        )}
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
            <div className="w-full h-10 rounded-btn border border-slate-200 bg-slate-50 px-3 flex items-center text-neutralState">
              {contextPatient?.name ?? "..."}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Profissional / Terapeuta responsável</label>
            <select
              required
              value={professionalId}
              onChange={(e) => setProfessionalId(e.target.value)}
              className="w-full h-10 rounded-btn border border-slate-300 px-3"
            >
              <option value="">Selecione...</option>
              {professionals.map((p) => (
                <option key={p.id} value={p.id}>
                  {professionalDisplayName(p)}
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
              onClick={() => navigate("/sessions")}
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
