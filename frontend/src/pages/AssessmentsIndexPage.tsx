import PatientPickerIndex from "../components/PatientPickerIndex";

export default function AssessmentsIndexPage() {
  return (
    <PatientPickerIndex
      title="Avaliações"
      description="Escolha um paciente para ver ou aplicar avaliações padronizadas."
      linkFor={(patientId) => `/patients/${patientId}/assessments`}
    />
  );
}
