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

    class Config:
        from_attributes = True


class ClinicPermissionSettingsUpdateRequest(BaseModel):
    professionals_can_create_patients: bool | None = None
    supervisors_can_register_sessions: bool | None = None
    supervisors_can_edit_any_objective_area: bool | None = None
    admins_can_edit_any_objective_area: bool | None = None
    supervisors_can_restore_deleted_data: bool | None = None
    supervisors_can_generate_invitations: bool | None = None
