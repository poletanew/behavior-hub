import datetime

from pydantic import BaseModel


class PatientImportRow(BaseModel):
    row_number: int
    name: str | None
    birth_date: str | None
    guardian_name: str | None
    diagnosis: str | None
    valid: bool
    error: str | None


class PatientImportPreviewResponse(BaseModel):
    detected_columns: dict[str, str]
    missing_required_columns: list[str]
    rows: list[PatientImportRow]
    total_rows: int


class PatientImportRejection(BaseModel):
    row_number: int
    name: str | None
    reason: str


class PatientImportCommitResponse(BaseModel):
    imported_count: int
    rejected: list[PatientImportRejection]
