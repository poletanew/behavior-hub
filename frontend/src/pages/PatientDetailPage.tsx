import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { apiRequest } from "../api/client";
import { ClinicalSession, Patient, Training, TrainingCategory } from "../types";
import { useAuth } from "../context/AuthContext";

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("pt-BR");
}

export default function PatientDetailPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [patient, setPatient] = useState<Patient | null>(null);
  const [sessions, setSessions] = useState<ClinicalSession[]>([]);
  const [categories, setCategories] = useState<TrainingCategory[]>([]);
  const [trainings, setTrainings] = useState<Training[]>([]);
  const [showNewSession, setShowNewSession] = useState(false);
  const [occurredAt, setOccurredAt] = useState("");
  const [notes, setNotes] = useState("");
  const [selectedTrainingIds, setSelectedTrainingIds] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  function load() {
    if (!patientId) return;
    apiRequest<Patient>(`/patients/${patientId}`).then(setPatient);
    apiRequest<ClinicalSession[]>(`/sessions?patient_id=${patientId}`).then(setSessions);
  }

  useEffect(load, [patientId]);

  useEffect(() => {
    apiRequest<TrainingCategory[]>("/training-categories").then(setCategories);
    apiRequest<Training[]>("/trainings").then(setTrainings);
  }, []);

  async function handleCreateSession(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const session = await apiRequest<ClinicalSession>("/sessions", {
        method: "POST",
        body: {
          patient_id: patientId,
          professional_id: user?.id,
          occurred_at: new Date(occurredAt).toISOString(),
          notes: notes || null,
          training_ids: selectedTrainingIds,
        },
      });
      navigate(`/sessions/${session.id}`);
    } catch {
      setError("Não foi possível criar o atendimento. Selecione ao menos um treino.");
    }
  }

  function toggleTraining(id: string) {
    setSelectedTrainingIds((prev) => (prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]));
  }

  if (!patient) return <p className="text-neutralState">Carregando...</p>;

  return (
    <div>
      <Link to="/patients" className="text-sm text-brand-blue underline mb-4 inline-block">
        ← Voltar para Pacientes
      </Link>

      <div className="bg-white rounded-card shadow-sm p-6 mb-6">
        <h1 className="text-2xl font-bold text-brand-navy">{patient.name}</h1>
        <p className="text-neutralState text-sm mt-1">Nascimento: {patient.birth_date}</p>
        {patient.guardian_name && <p className="text-sm mt-1">Responsável: {patient.guardian_name}</p>}
        {patient.diagnosis && <p className="text-sm mt-1">Diagnóstico: {patient.diagnosis}</p>}
        <div className="flex gap-4 mt-3 text-sm">
          <Link to={`/patients/${patientId}/treatment-plan`} className="text-brand-blue underline">
            Plano de Tratamento
          </Link>
          <Link to={`/patients/${patientId}/reports`} className="text-brand-blue underline">
            Reports
          </Link>
        </div>
      </div>

      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-brand-navy">Histórico de sessões</h2>
        <button
          onClick={() => setShowNewSession((v) => !v)}
          className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium"
        >
          Novo Atendimento
        </button>
      </div>

      {showNewSession && (
        <form onSubmit={handleCreateSession} className="bg-white rounded-card shadow-sm p-6 mb-6 space-y-4">
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
              onClick={() => setShowNewSession(false)}
              className="rounded-btn bg-white border border-slate-300 px-4 py-2 text-sm font-medium"
            >
              Cancelar
            </button>
          </div>
        </form>
      )}

      {sessions.length === 0 ? (
        <div className="bg-white rounded-card shadow-sm p-10 text-center text-neutralState">
          Nenhuma sessão registrada ainda.
        </div>
      ) : (
        <div className="bg-white rounded-card shadow-sm divide-y divide-slate-100">
          {sessions.map((session) => (
            <Link
              key={session.id}
              to={`/sessions/${session.id}`}
              className="flex justify-between px-4 py-3 hover:bg-slate-50"
            >
              <span>{formatDateTime(session.occurred_at)}</span>
              <span className="text-neutralState text-sm">{session.trainings.length} treino(s)</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
