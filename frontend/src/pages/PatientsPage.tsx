import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest, ApiError } from "../api/client";
import { Patient, SchoolShift } from "../types";
import { calculateAge, formatPhoneInput, initials, schoolShiftLabel } from "../utils/patient";

const SCHOOL_SHIFT_OPTIONS: { value: SchoolShift; label: string }[] = [
  { value: "manha", label: "Manhã" },
  { value: "tarde", label: "Tarde" },
  { value: "integral", label: "Integral" },
  { value: "nao_frequenta", label: "Não frequenta" },
];

function PatientCard({ patient, onDelete }: { patient: Patient; onDelete: (id: string) => void }) {
  const [showContact, setShowContact] = useState(false);
  const shiftLabel = schoolShiftLabel(patient.school_shift);
  const hasContactInfo = Boolean(patient.phone || patient.address);

  return (
    <div className="bg-white rounded-card shadow-sm p-5 flex flex-col gap-3">
      <div className="flex items-start gap-3">
        <div className="w-11 h-11 shrink-0 rounded-full bg-brand-turquoise/15 text-brand-turquoise font-bold flex items-center justify-center">
          {initials(patient.name)}
        </div>
        <div className="min-w-0 flex-1">
          <Link to={`/patients/${patient.id}`} className="font-semibold text-brand-navy hover:underline truncate block">
            {patient.name}
          </Link>
          <div className="text-xs text-neutralState mt-0.5">{calculateAge(patient.birth_date)} anos</div>
        </div>
        <span
          className={`shrink-0 rounded px-2 py-0.5 text-xs font-medium ${
            patient.status === "active" ? "bg-success/10 text-success" : "bg-slate-200 text-neutralState"
          }`}
        >
          {patient.status === "active" ? "Ativo" : "Inativo"}
        </span>
      </div>

      <p className="text-sm text-neutralState line-clamp-2">{patient.diagnosis || "Sem diagnóstico registrado"}</p>

      {patient.school_name && (
        <p className="text-xs text-neutralState">
          {patient.school_name}
          {shiftLabel ? ` · ${shiftLabel}` : ""}
        </p>
      )}

      {hasContactInfo && (
        <div>
          <button
            type="button"
            onClick={() => setShowContact((v) => !v)}
            className="text-xs text-brand-blue underline"
          >
            {showContact ? "Ocultar contato" : "Ver contato"}
          </button>
          {showContact && (
            <div className="mt-2 text-xs text-neutralState space-y-1">
              {patient.phone && <div>Telefone: {patient.phone}</div>}
              {patient.address && <div>Endereço: {patient.address}</div>}
            </div>
          )}
        </div>
      )}

      <div className="flex justify-end mt-auto pt-2 border-t border-slate-100">
        <button onClick={() => onDelete(patient.id)} className="text-danger text-xs hover:underline">
          Excluir
        </button>
      </div>
    </div>
  );
}

export default function PatientsPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [guardianName, setGuardianName] = useState("");
  const [diagnosis, setDiagnosis] = useState("");
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");
  const [schoolName, setSchoolName] = useState("");
  const [schoolShift, setSchoolShift] = useState<SchoolShift | "">("");

  function loadPatients() {
    setLoading(true);
    apiRequest<Patient[]>("/patients")
      .then(setPatients)
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadPatients();
  }, []);

  function resetForm() {
    setName("");
    setBirthDate("");
    setGuardianName("");
    setDiagnosis("");
    setAddress("");
    setPhone("");
    setSchoolName("");
    setSchoolShift("");
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    try {
      await apiRequest("/patients", {
        method: "POST",
        body: {
          name,
          birth_date: birthDate,
          guardian_name: guardianName || null,
          diagnosis: diagnosis || null,
          address: address || null,
          phone: phone || null,
          school_name: schoolName || null,
          school_shift: schoolShift || null,
        },
      });
      setShowForm(false);
      resetForm();
      loadPatients();
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setFormError("Você atingiu o limite de 3 pacientes do plano gratuito. Conheça os planos para adicionar mais.");
      } else {
        setFormError("Não foi possível cadastrar o paciente.");
      }
    }
  }

  async function handleDelete(patientId: string) {
    if (!confirm("Este paciente e todos os dados relacionados serão movidos para Dados Excluídos por 60 dias. Deseja continuar?")) {
      return;
    }
    await apiRequest(`/patients/${patientId}`, { method: "DELETE" });
    loadPatients();
  }

  const filtered = patients.filter((p) => p.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-brand-navy">Pacientes</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium"
        >
          + Adicionar paciente
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="bg-white rounded-card shadow-sm p-6 mb-6 space-y-4 max-w-lg">
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
            <label className="block text-sm font-medium mb-1">Data de nascimento</label>
            <input
              type="date"
              required
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
          <div>
            <label className="block text-sm font-medium mb-1">Diagnóstico / informações clínicas</label>
            <textarea
              value={diagnosis}
              onChange={(e) => setDiagnosis(e.target.value)}
              className="w-full rounded-btn border border-slate-300 px-3 py-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Endereço</label>
            <input
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="Rua, número, bairro, cidade, CEP"
              className="w-full h-10 rounded-btn border border-slate-300 px-3"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Telefone</label>
            <input
              value={phone}
              onChange={(e) => setPhone(formatPhoneInput(e.target.value))}
              placeholder="(11) 91234-5678"
              className="w-full h-10 rounded-btn border border-slate-300 px-3"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Nome da escola</label>
            <input
              value={schoolName}
              onChange={(e) => setSchoolName(e.target.value)}
              className="w-full h-10 rounded-btn border border-slate-300 px-3"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Turno escolar</label>
            <select
              value={schoolShift}
              onChange={(e) => setSchoolShift(e.target.value as SchoolShift | "")}
              className="w-full h-10 rounded-btn border border-slate-300 px-3"
            >
              <option value="">Selecione...</option>
              {SCHOOL_SHIFT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          {formError && <p className="text-danger text-sm">{formError}</p>}
          <div className="flex gap-3">
            <button type="submit" className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium">
              Salvar
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

      <input
        placeholder="Buscar por nome..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full max-w-sm h-10 rounded-btn border border-slate-300 px-3 mb-4"
      />

      {loading ? (
        <p className="text-neutralState">Carregando...</p>
      ) : filtered.length === 0 ? (
        <div className="bg-white rounded-card shadow-sm p-10 text-center text-neutralState">
          Nenhum paciente adicionado. Clique em Adicionar paciente para começar.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((patient) => (
            <PatientCard key={patient.id} patient={patient} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
}
