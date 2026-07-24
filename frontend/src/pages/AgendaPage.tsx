import { FormEvent, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiDownload, apiRequest, ApiError } from "../api/client";
import ConfirmModal from "../components/ConfirmModal";
import { useAuth } from "../context/AuthContext";
import { Appointment, AttendanceRate, CancellationReason, Patient, Room, User as UserType } from "../types";

const STATUS_LABELS: Record<string, string> = {
  scheduled: "Agendada",
  confirmed: "Confirmada",
  completed: "Realizada",
  cancelled: "Cancelada",
  no_show: "Não compareceu",
};

const STATUS_COLORS: Record<string, string> = {
  scheduled: "bg-brand-blueLight text-brand-navy",
  confirmed: "bg-brand-turquoise/20 text-brand-navy",
  completed: "bg-success/20 text-success",
  cancelled: "bg-slate-200 text-neutralState",
  no_show: "bg-danger/10 text-danger",
};

const CANCELLATION_REASON_LABELS: Record<CancellationReason, string> = {
  patient: "Paciente",
  clinic: "Clínica",
  professional: "Profissional",
  force_majeure: "Força maior",
};

function startOfWeek(date: Date): Date {
  const d = new Date(date);
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day; // Monday as first day
  d.setDate(d.getDate() + diff);
  d.setHours(0, 0, 0, 0);
  return d;
}

function addDays(date: Date, days: number): Date {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}

function toDatetimeLocal(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  window.URL.revokeObjectURL(url);
}

const WEEKDAY_LABELS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];

export default function AgendaPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isClinic = Boolean(user?.clinic_id);

  const [referenceDate, setReferenceDate] = useState(() => new Date());
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [professionals, setProfessionals] = useState<UserType[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [professionalFilter, setProfessionalFilter] = useState("");
  const [patientFilter, setPatientFilter] = useState("");
  const [attendanceRate, setAttendanceRate] = useState<AttendanceRate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<string | null>(null);
  const [dragError, setDragError] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [formPatientId, setFormPatientId] = useState("");
  const [formProfessionalId, setFormProfessionalId] = useState("");
  const [formRoomId, setFormRoomId] = useState("");
  const [formStart, setFormStart] = useState("");
  const [formEnd, setFormEnd] = useState("");
  const [formNotes, setFormNotes] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const [actionTarget, setActionTarget] = useState<{ id: string; action: "cancel" | "no_show" } | null>(null);
  const [actionReason, setActionReason] = useState<CancellationReason>("patient");
  const [actionNotes, setActionNotes] = useState("");

  const weekStart = useMemo(() => startOfWeek(referenceDate), [referenceDate]);
  const weekDays = useMemo(() => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)), [weekStart]);

  function load() {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams();
    params.set("date_from", weekStart.toISOString());
    params.set("date_to", addDays(weekStart, 7).toISOString());
    if (professionalFilter) params.set("professional_id", professionalFilter);
    if (patientFilter) params.set("patient_id", patientFilter);
    apiRequest<Appointment[]>(`/appointments?${params.toString()}`)
      .then(setAppointments)
      .catch(() => setError("Não foi possível carregar a agenda."))
      .finally(() => setLoading(false));
  }

  useEffect(load, [weekStart, professionalFilter, patientFilter]);

  useEffect(() => {
    apiRequest<Patient[]>("/patients").then(setPatients);
    apiRequest<Room[]>("/rooms").then(setRooms);
    if (isClinic) {
      apiRequest<UserType[]>("/professionals").then(setProfessionals);
    }
  }, [isClinic]);

  useEffect(() => {
    if (!patientFilter) {
      setAttendanceRate(null);
      return;
    }
    apiRequest<AttendanceRate>(`/appointments/attendance-rate/${patientFilter}`).then(setAttendanceRate);
  }, [patientFilter, appointments]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    try {
      await apiRequest("/appointments", {
        method: "POST",
        body: {
          patient_id: formPatientId,
          professional_id: formProfessionalId || user?.id,
          scheduled_start: new Date(formStart).toISOString(),
          scheduled_end: new Date(formEnd).toISOString(),
          notes: formNotes || null,
          room_id: formRoomId || null,
        },
      });
      setShowForm(false);
      setFormPatientId("");
      setFormProfessionalId("");
      setFormRoomId("");
      setFormStart("");
      setFormEnd("");
      setFormNotes("");
      load();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setFormError("Este profissional (ou sala) já tem um atendimento nesse horário.");
      } else {
        setFormError("Não foi possível agendar. Verifique os dados informados.");
      }
    }
  }

  async function handleDropOnDay(appointmentId: string, targetDay: Date) {
    setDragError(null);
    const appointment = appointments.find((a) => a.id === appointmentId);
    if (!appointment) return;
    const start = new Date(appointment.scheduled_start);
    const end = new Date(appointment.scheduled_end);
    const newStart = new Date(targetDay);
    newStart.setHours(start.getHours(), start.getMinutes(), 0, 0);
    const durationMs = end.getTime() - start.getTime();
    const newEnd = new Date(newStart.getTime() + durationMs);
    if (newStart.toDateString() === start.toDateString()) return;

    try {
      await apiRequest(`/appointments/${appointmentId}`, {
        method: "PATCH",
        body: { scheduled_start: newStart.toISOString(), scheduled_end: newEnd.toISOString() },
      });
      load();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setDragError("Não foi possível reagendar: já existe um atendimento nesse novo horário.");
      } else {
        setDragError("Não foi possível reagendar este atendimento.");
      }
    }
  }

  async function handleConfirm(id: string) {
    await apiRequest(`/appointments/${id}/confirm`, { method: "POST" });
    load();
  }

  function openActionForm(id: string, action: "cancel" | "no_show") {
    setActionTarget({ id, action });
    setActionReason("patient");
    setActionNotes("");
  }

  async function submitAction() {
    if (!actionTarget) return;
    const path = actionTarget.action === "cancel" ? "cancel" : "no-show";
    await apiRequest(`/appointments/${actionTarget.id}/${path}`, {
      method: "POST",
      body: { reason: actionReason, notes: actionNotes || null },
    });
    setActionTarget(null);
    load();
  }

  async function handleDelete(id: string) {
    await apiRequest(`/appointments/${id}`, { method: "DELETE" });
    load();
  }

  function handleMarkCompleted(appointment: Appointment) {
    const params = new URLSearchParams();
    params.set("patient_id", appointment.patient_id);
    params.set("professional_id", appointment.professional_id);
    params.set("appointment_id", appointment.id);
    params.set("occurred_at", toDatetimeLocal(appointment.scheduled_start));
    navigate(`/sessions?${params.toString()}`);
  }

  async function handleExportIcs() {
    const params = new URLSearchParams();
    params.set("date_from", weekStart.toISOString());
    params.set("date_to", addDays(weekStart, 7).toISOString());
    if (professionalFilter) params.set("professional_id", professionalFilter);
    if (patientFilter) params.set("patient_id", patientFilter);
    const blob = await apiDownload(`/appointments/export.ics?${params.toString()}`);
    downloadBlob(blob, "agenda.ics");
  }

  const appointmentsByDay = weekDays.map((day) => {
    const dayStr = day.toDateString();
    return appointments
      .filter((a) => new Date(a.scheduled_start).toDateString() === dayStr)
      .sort((a, b) => a.scheduled_start.localeCompare(b.scheduled_start));
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-brand-navy">Agenda</h1>
        <div className="flex gap-3">
          <button
            onClick={handleExportIcs}
            className="rounded-btn border border-brand-navy text-brand-navy px-4 py-2 text-sm font-medium"
          >
            Exportar (.ics)
          </button>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium"
          >
            + Agendar
          </button>
        </div>
      </div>
      <p className="text-xs text-neutralState -mt-4 mb-6">
        Dica: arraste um atendimento agendado/confirmado para outro dia da semana para reagendar.
      </p>

      {showForm && (
        <form onSubmit={handleCreate} className="bg-white rounded-card shadow-card p-6 mb-6 space-y-4 max-w-2xl">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Paciente</label>
              <select
                required
                value={formPatientId}
                onChange={(e) => setFormPatientId(e.target.value)}
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
            {isClinic && (
              <div>
                <label className="block text-sm font-medium mb-1">Profissional</label>
                <select
                  value={formProfessionalId}
                  onChange={(e) => setFormProfessionalId(e.target.value)}
                  className="w-full h-10 rounded-btn border border-slate-300 px-3"
                >
                  <option value="">Eu mesmo</option>
                  {professionals.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
          {rooms.length > 0 && (
            <div>
              <label className="block text-sm font-medium mb-1">Sala (opcional)</label>
              <select
                value={formRoomId}
                onChange={(e) => setFormRoomId(e.target.value)}
                className="w-full h-10 rounded-btn border border-slate-300 px-3"
              >
                <option value="">Sem sala definida</option>
                {rooms.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Início</label>
              <input
                type="datetime-local"
                required
                value={formStart}
                onChange={(e) => setFormStart(e.target.value)}
                className="w-full h-10 rounded-btn border border-slate-300 px-3"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Fim</label>
              <input
                type="datetime-local"
                required
                value={formEnd}
                onChange={(e) => setFormEnd(e.target.value)}
                className="w-full h-10 rounded-btn border border-slate-300 px-3"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Observações</label>
            <textarea
              value={formNotes}
              onChange={(e) => setFormNotes(e.target.value)}
              className="w-full rounded-btn border border-slate-300 px-3 py-2"
            />
          </div>
          {formError && <p className="text-danger text-sm">{formError}</p>}
          <div className="flex gap-3">
            <button type="submit" className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium">
              Agendar
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

      <div className="bg-white rounded-card shadow-card p-4 mb-6 flex flex-wrap gap-4 items-end">
        <div className="flex gap-2 items-center">
          <button
            onClick={() => setReferenceDate((d) => addDays(d, -7))}
            className="h-9 px-3 rounded-btn border border-slate-300 text-sm"
          >
            ← Semana anterior
          </button>
          <button
            onClick={() => setReferenceDate(new Date())}
            className="h-9 px-3 rounded-btn border border-slate-300 text-sm"
          >
            Hoje
          </button>
          <button
            onClick={() => setReferenceDate((d) => addDays(d, 7))}
            className="h-9 px-3 rounded-btn border border-slate-300 text-sm"
          >
            Próxima semana →
          </button>
        </div>
        {isClinic && (
          <div>
            <label className="block text-xs font-medium mb-1">Profissional</label>
            <select
              value={professionalFilter}
              onChange={(e) => setProfessionalFilter(e.target.value)}
              className="h-9 rounded-btn border border-slate-300 px-2 text-sm"
            >
              <option value="">Todos</option>
              {professionals.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        )}
        <div>
          <label className="block text-xs font-medium mb-1">Paciente</label>
          <select
            value={patientFilter}
            onChange={(e) => setPatientFilter(e.target.value)}
            className="h-9 rounded-btn border border-slate-300 px-2 text-sm"
          >
            <option value="">Todos</option>
            {patients.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        {attendanceRate && (
          <div className="text-sm text-neutralState">
            Taxa de comparecimento:{" "}
            <span className="font-semibold text-brand-navy">
              {attendanceRate.attendance_rate_pct !== null ? `${attendanceRate.attendance_rate_pct}%` : "—"}
            </span>{" "}
            ({attendanceRate.completed_count} realizadas, {attendanceRate.no_show_count} faltas)
          </div>
        )}
      </div>

      {error && <p className="text-danger text-sm mb-4">{error}</p>}
      {dragError && <p className="text-danger text-sm mb-4">{dragError}</p>}

      {loading ? (
        <p className="text-neutralState">Carregando...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-7 gap-3">
          {weekDays.map((day, idx) => (
            <div
              key={day.toISOString()}
              className="bg-white rounded-card shadow-card overflow-hidden"
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const appointmentId = e.dataTransfer.getData("text/appointment-id");
                if (appointmentId) handleDropOnDay(appointmentId, day);
              }}
            >
              <div className="bg-brand-navy text-white px-3 py-2 text-xs font-semibold">
                {WEEKDAY_LABELS[idx]}
                <div className="text-[10px] font-normal opacity-80">
                  {day.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })}
                </div>
              </div>
              <div className="divide-y divide-slate-100 min-h-[80px]">
                {appointmentsByDay[idx].length === 0 && (
                  <div className="px-3 py-4 text-xs text-neutralState text-center">Sem atendimentos</div>
                )}
                {appointmentsByDay[idx].map((appointment) => (
                  <div
                    key={appointment.id}
                    className={`px-3 py-2 text-xs space-y-1 ${
                      appointment.status === "scheduled" || appointment.status === "confirmed"
                        ? "cursor-move"
                        : ""
                    }`}
                    draggable={appointment.status === "scheduled" || appointment.status === "confirmed"}
                    onDragStart={(e) => e.dataTransfer.setData("text/appointment-id", appointment.id)}
                    title="Arraste para outro dia da semana para reagendar"
                  >
                    <div className="font-medium">
                      {new Date(appointment.scheduled_start).toLocaleTimeString("pt-BR", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                      {" – "}
                      {new Date(appointment.scheduled_end).toLocaleTimeString("pt-BR", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </div>
                    <div>{appointment.patient_name}</div>
                    {isClinic && <div className="text-neutralState">{appointment.professional_name}</div>}
                    {appointment.room_name && <div className="text-neutralState">Sala: {appointment.room_name}</div>}
                    <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] ${STATUS_COLORS[appointment.status]}`}>
                      {STATUS_LABELS[appointment.status]}
                    </span>
                    {appointment.cancellation_reason && (
                      <div className="text-[10px] text-neutralState">
                        Motivo: {CANCELLATION_REASON_LABELS[appointment.cancellation_reason]}
                      </div>
                    )}
                    {(appointment.status === "scheduled" || appointment.status === "confirmed") && (
                      <div className="flex flex-wrap gap-1 pt-1">
                        {appointment.status === "scheduled" && (
                          <button
                            onClick={() => handleConfirm(appointment.id)}
                            className="text-brand-blue hover:underline"
                          >
                            Confirmar
                          </button>
                        )}
                        <button
                          onClick={() => handleMarkCompleted(appointment)}
                          className="text-success hover:underline"
                        >
                          Realizada
                        </button>
                        <button
                          onClick={() => openActionForm(appointment.id, "no_show")}
                          className="text-danger hover:underline"
                        >
                          Faltou
                        </button>
                        <button
                          onClick={() => openActionForm(appointment.id, "cancel")}
                          className="text-neutralState hover:underline"
                        >
                          Cancelar
                        </button>
                      </div>
                    )}
                    <div>
                      <button onClick={() => setConfirmingDeleteId(appointment.id)} className="text-neutralState hover:underline">
                        Excluir
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {confirmingDeleteId && (
        <ConfirmModal
          title="Excluir compromisso"
          message="Excluir este compromisso da agenda? Ele ficará em Dados Excluídos por 60 dias."
          confirmLabel="Excluir"
          onClose={() => setConfirmingDeleteId(null)}
          onConfirm={() => {
            const id = confirmingDeleteId;
            setConfirmingDeleteId(null);
            handleDelete(id);
          }}
        />
      )}

      {actionTarget && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-card shadow-lg p-6 w-full max-w-sm space-y-4">
            <h2 className="font-semibold text-brand-navy">
              {actionTarget.action === "cancel" ? "Cancelar atendimento" : "Registrar falta"}
            </h2>
            <div>
              <label className="block text-sm font-medium mb-1">Motivo</label>
              <select
                value={actionReason}
                onChange={(e) => setActionReason(e.target.value as CancellationReason)}
                className="w-full h-10 rounded-btn border border-slate-300 px-3"
              >
                {Object.entries(CANCELLATION_REASON_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Observações (opcional)</label>
              <textarea
                value={actionNotes}
                onChange={(e) => setActionNotes(e.target.value)}
                className="w-full rounded-btn border border-slate-300 px-3 py-2"
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={submitAction}
                className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium"
              >
                Confirmar
              </button>
              <button
                onClick={() => setActionTarget(null)}
                className="rounded-btn bg-white border border-slate-300 px-4 py-2 text-sm font-medium"
              >
                Voltar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
