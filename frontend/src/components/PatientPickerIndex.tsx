import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest } from "../api/client";
import EmptyState from "../components/EmptyState";
import { Patient } from "../types";
import { calculateAge, initials } from "../utils/patient";

interface PatientPickerIndexProps {
  title: string;
  description: string;
  linkFor: (patientId: string) => string;
  emptyMessage?: string;
}

// Index compartilhado por Treatment Plans / Avaliações / Reports: cada uma
// dessas telas trabalha sobre o contexto de um paciente específico (rota
// /patients/:id/...), então a navegação principal primeiro lista os
// pacientes e leva à ficha certa — mesmo padrão do protótipo de referência.
export default function PatientPickerIndex({ title, description, linkFor, emptyMessage }: PatientPickerIndexProps) {
  const [patients, setPatients] = useState<Patient[] | null>(null);

  useEffect(() => {
    apiRequest<Patient[]>("/patients").then(setPatients);
  }, []);

  return (
    <div>
      <h1 className="text-[22px] font-bold text-brand-navy mb-1">{title}</h1>
      <p className="text-neutralState text-[13px] mb-4">{description}</p>

      {patients === null ? (
        <p className="text-neutralState text-sm">Carregando...</p>
      ) : patients.length === 0 ? (
        <EmptyState message={emptyMessage ?? "Nenhum paciente cadastrado ainda."} />
      ) : (
        <div className="grid grid-cols-3 gap-3.5">
          {patients.map((p) => (
            <Link
              key={p.id}
              to={linkFor(p.id)}
              className="bg-white rounded-card shadow-card p-5 flex items-center gap-3 hover:shadow-md transition-shadow"
            >
              <div className="w-10 h-10 shrink-0 rounded-full bg-brand-turquoise/15 text-brand-turquoise font-bold flex items-center justify-center text-sm">
                {initials(p.name)}
              </div>
              <div className="min-w-0">
                <div className="font-semibold text-sm text-brand-graphite truncate">{p.name}</div>
                <div className="text-xs text-neutralState">{calculateAge(p.birth_date)} anos</div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
