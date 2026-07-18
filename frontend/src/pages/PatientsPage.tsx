import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest, ApiError } from "../api/client";
import { Patient } from "../types";

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

  function loadPatients() {
    setLoading(true);
    apiRequest<Patient[]>("/patients")
      .then(setPatients)
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadPatients();
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    try {
      await apiRequest("/patients", {
        method: "POST",
        body: { name, birth_date: birthDate, guardian_name: guardianName || null, diagnosis: diagnosis || null },
      });
      setShowForm(false);
      setName("");
      setBirthDate("");
      setGuardianName("");
      setDiagnosis("");
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
        <div className="bg-white rounded-card shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-brand-navy text-white">
              <tr>
                <th className="text-left px-4 py-3">Nome</th>
                <th className="text-left px-4 py-3">Data de nascimento</th>
                <th className="text-left px-4 py-3">Diagnóstico</th>
                <th className="text-right px-4 py-3">Ações</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((patient, idx) => (
                <tr key={patient.id} className={idx % 2 === 1 ? "bg-slate-50" : undefined}>
                  <td className="px-4 py-3">
                    <Link to={`/patients/${patient.id}`} className="text-brand-blue hover:underline">
                      {patient.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{patient.birth_date}</td>
                  <td className="px-4 py-3">{patient.diagnosis || "-"}</td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => handleDelete(patient.id)} className="text-danger hover:underline">
                      Excluir
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
