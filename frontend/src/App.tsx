import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import PatientsPage from "./pages/PatientsPage";
import PatientDetailPage from "./pages/PatientDetailPage";
import SessionsPage from "./pages/SessionsPage";
import SessionDetailPage from "./pages/SessionDetailPage";
import TrainingLibraryPage from "./pages/TrainingLibraryPage";
import InvitationsPage from "./pages/InvitationsPage";
import AcceptInvitationPage from "./pages/AcceptInvitationPage";
import TreatmentPlanPage from "./pages/TreatmentPlanPage";
import ReportsPage from "./pages/ReportsPage";
import TimelinePage from "./pages/TimelinePage";
import ResourcesPage from "./pages/ResourcesPage";
import DeletedDataPage from "./pages/DeletedDataPage";
import ClinicSettingsPage from "./pages/ClinicSettingsPage";
import AuditLogPage from "./pages/AuditLogPage";
import PatientImportPage from "./pages/PatientImportPage";
import AgendaPage from "./pages/AgendaPage";
import SecurityPage from "./pages/SecurityPage";
import SupervisorDashboardPage from "./pages/SupervisorDashboardPage";
import PlansPage from "./pages/PlansPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/invitations/:token/accept" element={<AcceptInvitationPage />} />

      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/patients" element={<PatientsPage />} />
        <Route path="/patients/:patientId" element={<PatientDetailPage />} />
        <Route path="/patients/:patientId/treatment-plan" element={<TreatmentPlanPage />} />
        <Route path="/patients/:patientId/reports" element={<ReportsPage />} />
        <Route path="/patients/:patientId/timeline" element={<TimelinePage />} />
        <Route path="/agenda" element={<AgendaPage />} />
        <Route path="/sessions" element={<SessionsPage />} />
        <Route path="/sessions/:sessionId" element={<SessionDetailPage />} />
        <Route path="/training-library" element={<TrainingLibraryPage />} />
        <Route path="/resources" element={<ResourcesPage />} />
        <Route path="/deleted-data" element={<DeletedDataPage />} />
        <Route path="/invitations" element={<InvitationsPage />} />
        <Route path="/clinic-settings" element={<ClinicSettingsPage />} />
        <Route path="/audit-log" element={<AuditLogPage />} />
        <Route path="/patients/import" element={<PatientImportPage />} />
        <Route path="/security" element={<SecurityPage />} />
        <Route path="/supervisor-dashboard" element={<SupervisorDashboardPage />} />
        <Route path="/plans" element={<PlansPage />} />
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
