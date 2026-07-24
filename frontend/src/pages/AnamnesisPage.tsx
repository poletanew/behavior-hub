import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiRequest, ApiError } from "../api/client";
import { Anamnesis, Patient } from "../types";

const FIELD_LABELS: Record<keyof Omit<Anamnesis, "id" | "patient_id" | "created_by_user_id" | "created_at" | "updated_at">, string> = {
  chief_complaint: "Queixa principal",
  birth_history: "Informações de nascimento",
  developmental_history: "Histórico de desenvolvimento",
  developmental_milestones: "Marcos de desenvolvimento",
  family_history: "Histórico familiar relevante à intervenção",
};

export default function AnamnesisPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [form, setForm] = useState<Record<string, string>>({
    chief_complaint: "",
    birth_history: "",
    developmental_history: "",
    developmental_milestones: "",
    family_history: "",
  });
  const [existing, setExisting] = useState<Anamnesis | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);

  useEffect(() => {
    if (!patientId) return;
    apiRequest<Patient>(`/patients/${patientId}`).then(setPatient);
    apiRequest<Anamnesis>(`/patients/${patientId}/anamnesis`)
      .then((data) => {
        setExisting(data);
        setForm({
          chief_complaint: data.chief_complaint ?? "",
          birth_history: data.birth_history ?? "",
          developmental_history: data.developmental_history ?? "",
          developmental_milestones: data.developmental_milestones ?? "",
          family_history: data.family_history ?? "",
        });
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) setForbidden(true);
      });
  }, [patientId]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!patientId) return;
    setSaving(true);
    setMessage(null);
    try {
      const saved = await apiRequest<Anamnesis>(`/patients/${patientId}/anamnesis`, { method: "PUT", body: form });
      setExisting(saved);
      setMessage(existing ? "Anamnese atualizada com sucesso." : "Anamnese registrada com sucesso.");
    } finally {
      setSaving(false);
    }
  }

  if (forbidden) {
    return <p className="text-danger">Você não tem permissão para acessar a anamnese deste paciente.</p>;
  }
  if (!patient) return <p className="text-neutralState">Carregando...</p>;

  return (
    <div>
      <Link to={`/patients/${patientId}`} className="text-sm text-brand-blue underline mb-4 inline-block">
        ← Voltar para {patient.name}
      </Link>

      <h1 className="text-2xl font-bold text-brand-navy mb-2">Anamnese — {patient.name}</h1>
      <p className="text-sm text-neutralState mb-6">
        Formulário de admissão: histórico de desenvolvimento, queixa principal, informações de nascimento,
        marcos de desenvolvimento e histórico familiar relevante à intervenção.
      </p>

      {message && <p className="text-success text-sm mb-4 animate-pop-in">{message}</p>}

      <form onSubmit={handleSubmit} className="bg-white rounded-card shadow-card p-6 space-y-4">
        {(Object.keys(FIELD_LABELS) as (keyof typeof FIELD_LABELS)[]).map((field) => (
          <div key={field}>
            <label className="block text-sm font-medium mb-1">{FIELD_LABELS[field]}</label>
            <textarea
              value={form[field]}
              onChange={(e) => setForm((prev) => ({ ...prev, [field]: e.target.value }))}
              className="w-full rounded-btn border border-slate-300 px-3 py-2 text-sm"
              rows={3}
            />
          </div>
        ))}
        <button
          type="submit"
          disabled={saving}
          className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          {saving ? "Salvando..." : existing ? "Salvar alterações" : "Registrar anamnese"}
        </button>
      </form>
    </div>
  );
}
