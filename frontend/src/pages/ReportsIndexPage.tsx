import PatientPickerIndex from "../components/PatientPickerIndex";

export default function ReportsIndexPage() {
  return (
    <PatientPickerIndex
      title="Reports"
      description="Escolha um paciente para ver os relatórios e gráficos calculados a partir dos atendimentos dele."
      linkFor={(patientId) => `/patients/${patientId}/reports`}
    />
  );
}
