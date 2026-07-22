import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest } from "../../api/client";
import EmptyState from "../../components/EmptyState";
import { ATPatient } from "../../types";
import { calculateAge } from "../../utils/patient";

export default function ATPatientsPage() {
  const [patients, setPatients] = useState<ATPatient[] | null>(null);

  useEffect(() => {
    apiRequest<ATPatient[]>("/at-portal/patients").then(setPatients);
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-navy mb-2">Meus pacientes</h1>
      <p className="text-sm text-neutralState mb-6">
        Pacientes atribuídos a você. Abra um paciente para ver os treinos prescritos e registrar
        tentativas.
      </p>

      {patients === null ? (
        <p className="text-neutralState">Carregando...</p>
      ) : patients.length === 0 ? (
        <EmptyState
          icon="🧑‍🤝‍🧑"
          message="Nenhum paciente atribuído a você ainda. Peça ao supervisor para atribuir na aba ABA."
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {patients.map((patient) => (
            <Link
              key={patient.id}
              to={`/at/patients/${patient.id}`}
              className="bg-white rounded-card shadow-sm p-5 hover:ring-2 hover:ring-brand-turquoise transition"
            >
              <div className="font-semibold text-brand-navy">{patient.name}</div>
              <div className="text-xs text-neutralState mt-1">{calculateAge(patient.birth_date)} anos</div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
