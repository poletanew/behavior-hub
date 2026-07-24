import PatientPickerIndex from "../components/PatientPickerIndex";

export default function TreatmentPlansIndexPage() {
  return (
    <PatientPickerIndex
      title="Treatment Plans"
      description="Abra a ficha de um paciente para ver e editar o plano de tratamento dele."
      linkFor={(patientId) => `/patients/${patientId}/treatment-plan`}
    />
  );
}
