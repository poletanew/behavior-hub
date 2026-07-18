export type UserType = "clinic_admin" | "professional" | "individual" | "supervisor";

export interface User {
  id: string;
  email: string;
  name: string;
  user_type: UserType;
  specialty: string | null;
  status: string;
  clinic_id: string | null;
  subscription_plan: string | null;
}

export interface Patient {
  id: string;
  name: string;
  birth_date: string;
  guardian_name: string | null;
  diagnosis: string | null;
  notes: string | null;
  photo_url: string | null;
  status: string;
  clinic_id: string | null;
  individual_owner_id: string | null;
  deleted_at: string | null;
}

export interface TrainingCategory {
  id: string;
  name: string;
  description: string | null;
}

export interface Training {
  id: string;
  category_id: string;
  title: string;
  objective: string;
  discriminative_instruction: string | null;
  expected_response: string | null;
  prompt_hierarchy: string | null;
  mastery_criteria: string | null;
  notes: string | null;
  suggested_age_range: string | null;
  visibility: string;
}

export interface SessionTraining {
  id: string;
  training_id: string;
  sequence: number;
}

export interface ClinicalSession {
  id: string;
  patient_id: string;
  professional_id: string;
  occurred_at: string;
  notes: string | null;
  photo_url: string | null;
  deleted_at: string | null;
  trainings: SessionTraining[];
}

export interface Trial {
  id: string;
  session_training_id: string;
  attempt_number: number;
  result: "correct" | "incorrect" | "partial" | "no_response";
  prompt_level: "independent" | "gestural" | "verbal" | "modeling" | "partial_physical" | "full_physical";
  notes: string | null;
  recorded_at: string;
  deleted_at: string | null;
}

export interface SessionTrainingProgress {
  session_training_id: string;
  training_id: string;
  trials: Trial[];
  accuracy_pct: number | null;
  independence_pct: number | null;
}

export interface DashboardData {
  active_patients_count: number;
  sessions_today_count: number;
  recent_sessions: ClinicalSession[];
}

export type TreatmentArea =
  | "psicologia"
  | "aba"
  | "fonoaudiologia"
  | "terapia_ocupacional"
  | "psicopedagogia"
  | "fisioterapia"
  | "nutricao"
  | "outra";

export type ObjectiveStatus = "not_started" | "in_progress" | "mastered" | "paused" | "discontinued";
export type ObjectivePriority = "low" | "medium" | "high";

export interface Objective {
  id: string;
  plan_id: string;
  patient_id: string;
  area: TreatmentArea;
  title: string;
  description: string | null;
  criteria: string | null;
  strategies: string | null;
  status: ObjectiveStatus;
  priority: ObjectivePriority;
  author_id: string;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
  training_ids: string[];
}

export interface TreatmentPlan {
  id: string;
  patient_id: string;
  version: number;
  objectives: Objective[];
}

export interface DuplicateCandidate {
  id: string;
  title: string;
  area: TreatmentArea;
  status: ObjectiveStatus;
  author_id: string;
  similarity: number;
}

export interface ObjectiveComment {
  id: string;
  objective_id: string;
  author_id: string;
  body: string;
  created_at: string;
}

export interface ObjectiveHistoryEntry {
  action: string;
  actor_user_id: string | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  timestamp: string;
}

export interface LineSeries {
  training_id: string;
  training_title: string;
  points: { date: string; accuracy_pct: number | null; independence_pct: number | null }[];
}

export interface BarPoint {
  training_id: string;
  training_title: string;
  accuracy_pct: number | null;
  sample_size: number;
}

export interface StackedBarPoint {
  session_id: string;
  date: string;
  distribution_pct: Record<string, number>;
}

export interface PieData {
  correct: number;
  incorrect: number;
  partial: number;
  no_response: number;
}

export interface RadarPoint {
  area: string;
  accuracy_pct: number | null;
  sample_size: number;
  insufficient_data: boolean;
}

export interface CumulativePoint {
  date: string;
  cumulative_correct: number;
  cumulative_total: number;
  cumulative_independence_pct: number | null;
}

export type HeatmapIntensity = "baixa" | "media" | "alta" | "muito_alta";

export interface HeatmapAreaPoint {
  area: string;
  trial_count: number;
  intensity_pct: number;
  intensity_label: HeatmapIntensity;
}

export interface ReportData {
  patient_id: string;
  period_start: string | null;
  period_end: string | null;
  total_trials: number;
  line: LineSeries[];
  bar: BarPoint[];
  stacked_bar: StackedBarPoint[];
  pie: PieData;
  radar: RadarPoint[];
  cumulative: CumulativePoint[];
  heatmap: HeatmapAreaPoint[];
  comparison: {
    available: boolean;
    message?: string | null;
    period_a_accuracy_pct?: number | null;
    period_b_accuracy_pct?: number | null;
    delta_pct?: number | null;
  } | null;
}

export interface ReportSummary {
  id: string;
  patient_id: string;
  period_start: string;
  period_end: string;
  version: number;
  content: string;
  status: "draft" | "approved" | "discarded";
  generated_by: string;
  author_id: string | null;
}

export type ResourceType = "pdf" | "image" | "text";
export type ResourceVisibility = "private" | "clinic_shared";

export interface ResourceItem {
  id: string;
  title: string;
  description: string | null;
  category: string | null;
  suggested_age_range: string | null;
  resource_type: ResourceType;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  visibility: ResourceVisibility;
  uploaded_by_user_id: string;
  created_at: string;
  deleted_at: string | null;
}

export interface ResourceWithUrl extends ResourceItem {
  view_url: string;
}

export interface DeletedItem {
  entity_type: "patient" | "objective" | "resource";
  id: string;
  label: string;
  deleted_at: string;
  deleted_by: string | null;
  days_remaining: number;
}

export interface AppNotification {
  id: string;
  actor_user_id: string | null;
  type: "comment" | "mention";
  message: string;
  entity_type: string;
  entity_id: string;
  read_at: string | null;
  created_at: string;
}

export interface SessionTemplateTrainingRef {
  training_id: string;
  sequence: number;
}

export interface SessionTemplate {
  id: string;
  name: string;
  patient_id: string | null;
  created_by_user_id: string;
  created_at: string;
  trainings: SessionTemplateTrainingRef[];
}

export interface ClinicPermissionSettings {
  professionals_can_create_patients: boolean;
  supervisors_can_register_sessions: boolean;
  supervisors_can_edit_any_objective_area: boolean;
  admins_can_edit_any_objective_area: boolean;
  supervisors_can_restore_deleted_data: boolean;
  supervisors_can_generate_invitations: boolean;
  no_collection_days: number;
  regression_window_sessions: number;
  regression_drop_pp: number;
  stagnation_session_count: number;
  stagnation_band_pp: number;
  fading_session_count: number;
  fading_independence_pct: number;
}

export interface AuditLogEntry {
  id: string;
  actor_user_id: string | null;
  actor_name: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  before: unknown;
  after: unknown;
  timestamp: string;
}

export interface PatientImportRow {
  row_number: number;
  name: string | null;
  birth_date: string | null;
  guardian_name: string | null;
  diagnosis: string | null;
  valid: boolean;
  error: string | null;
}

export interface PatientImportPreview {
  detected_columns: Record<string, string>;
  missing_required_columns: string[];
  rows: PatientImportRow[];
  total_rows: number;
}

export interface PatientImportRejection {
  row_number: number;
  name: string | null;
  reason: string;
}

export interface PatientImportCommitResult {
  imported_count: number;
  rejected: PatientImportRejection[];
}

export type AppointmentStatus = "scheduled" | "confirmed" | "completed" | "cancelled" | "no_show";
export type CancellationReason = "patient" | "clinic" | "professional" | "force_majeure";

export interface Appointment {
  id: string;
  patient_id: string;
  patient_name: string;
  professional_id: string;
  professional_name: string;
  scheduled_start: string;
  scheduled_end: string;
  status: AppointmentStatus;
  cancellation_reason: CancellationReason | null;
  status_notes: string | null;
  notes: string | null;
  session_id: string | null;
  deleted_at: string | null;
  created_at: string;
}

export interface AttendanceRate {
  patient_id: string;
  completed_count: number;
  no_show_count: number;
  attendance_rate_pct: number | null;
}

export type PlanId = "free" | "basic" | "premium" | "enterprise";

export type ClinicalAlertType = "no_collection" | "regression" | "stagnation" | "fading_candidate";

export interface ClinicalAlert {
  id: string;
  patient_id: string;
  objective_id: string;
  objective_title: string;
  alert_type: ClinicalAlertType;
  message: string;
  detail: Record<string, unknown> | null;
  triggered_at: string;
  resolved_at: string | null;
}

export interface TimelineEntry {
  id: string;
  event_type: string;
  occurred_at: string;
  label: string;
  source_type: "session" | "objective" | "patient" | "report_summary";
  source_id: string;
}

export interface SupervisorDashboardTherapistRow {
  professional_id: string;
  professional_name: string;
  assigned_patients_count: number;
  completed_sessions_count: number;
  no_show_count: number;
  session_completion_pct: number | null;
  active_objectives_count: number;
  treatment_plan_adherence_pct: number | null;
  low_adherence_alert: boolean;
  no_recent_registration_alert: boolean;
}

export interface BillingStatus {
  subscription_plan: PlanId | null;
  subscription_status: string;
  subscription_current_period_end: string | null;
  has_paid_access: boolean;
  stripe_configured: boolean;
}
