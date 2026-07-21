import uuid

from pydantic import BaseModel


class ClinicPermissionSettingsResponse(BaseModel):
    clinic_id: uuid.UUID
    professionals_can_create_patients: bool
    supervisors_can_register_sessions: bool
    supervisors_can_edit_any_objective_area: bool
    admins_can_edit_any_objective_area: bool
    supervisors_can_restore_deleted_data: bool
    supervisors_can_generate_invitations: bool
    bulk_import_enabled: bool
    no_collection_days: int
    regression_window_sessions: int
    regression_drop_pp: int
    stagnation_session_count: int
    stagnation_band_pp: int
    fading_session_count: int
    fading_independence_pct: int
    mastery_suggestion_session_count: int
    mastery_suggestion_accuracy_pct: int

    class Config:
        from_attributes = True


class ClinicPermissionSettingsUpdateRequest(BaseModel):
    professionals_can_create_patients: bool | None = None
    supervisors_can_register_sessions: bool | None = None
    supervisors_can_edit_any_objective_area: bool | None = None
    admins_can_edit_any_objective_area: bool | None = None
    supervisors_can_restore_deleted_data: bool | None = None
    supervisors_can_generate_invitations: bool | None = None


class BulkImportToggleRequest(BaseModel):
    enabled: bool
