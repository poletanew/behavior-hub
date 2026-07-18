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
