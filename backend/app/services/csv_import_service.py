import csv
import datetime
import io
import unicodedata

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.patient import PatientCreateRequest
from app.services import patient_service

# Seção 32.7 — importação em lote de pacientes via CSV. Detecta colunas por
# alias comum (português/inglês) em vez de exigir uma UI de remapeamento
# manual de colunas — cobre o caso descrito no próprio exemplo do PRD (nome,
# data de nascimento, responsável, diagnóstico) sem a complexidade extra de um
# fluxo de mapeamento arbitrário coluna-a-coluna.
COLUMN_ALIASES: dict[str, list[str]] = {
    "name": ["nome", "name", "paciente"],
    "birth_date": ["data de nascimento", "data_nascimento", "nascimento", "birth_date", "data nascimento"],
    "guardian_name": ["responsavel", "responsável", "guardian_name", "responsavel_nome"],
    "diagnosis": ["diagnostico", "diagnóstico", "diagnosis", "informacoes_clinicas"],
}
REQUIRED_FIELDS = ["name", "birth_date"]
MAX_PREVIEW_ROWS = 500


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return text.strip().lower()


def _detect_columns(headers: list[str]) -> dict[str, str]:
    normalized_headers = {_normalize(h): h for h in headers}
    detected: dict[str, str] = {}
    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if _normalize(alias) in normalized_headers:
                detected[field] = normalized_headers[_normalize(alias)]
                break
    return detected


def _parse_date(value: str) -> datetime.date | None:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


async def _read_rows(file: UploadFile) -> tuple[list[str], list[dict]]:
    raw = await file.read()
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty or invalid CSV file")
    return list(reader.fieldnames), list(reader)


def _validate_row(row: dict, columns: dict[str, str], row_number: int) -> dict:
    name = (row.get(columns.get("name", ""), "") or "").strip() or None
    raw_birth_date = (row.get(columns.get("birth_date", ""), "") or "").strip()
    guardian_name = (row.get(columns.get("guardian_name", ""), "") or "").strip() or None
    diagnosis = (row.get(columns.get("diagnosis", ""), "") or "").strip() or None

    error = None
    parsed_date = _parse_date(raw_birth_date) if raw_birth_date else None
    if not name:
        error = "Nome ausente"
    elif not raw_birth_date:
        error = "Data de nascimento ausente"
    elif parsed_date is None:
        error = "Data de nascimento em formato inválido (use AAAA-MM-DD ou DD/MM/AAAA)"

    return {
        "row_number": row_number,
        "name": name,
        "birth_date": raw_birth_date or None,
        "guardian_name": guardian_name,
        "diagnosis": diagnosis,
        "valid": error is None,
        "error": error,
        "_parsed_date": parsed_date,
    }


async def preview_import(file: UploadFile) -> dict:
    headers, rows = await _read_rows(file)
    columns = _detect_columns(headers)
    missing = [f for f in REQUIRED_FIELDS if f not in columns]

    parsed_rows = []
    if not missing:
        for idx, row in enumerate(rows[:MAX_PREVIEW_ROWS], start=2):  # row 1 is the header
            parsed_rows.append(_validate_row(row, columns, idx))

    return {
        "detected_columns": columns,
        "missing_required_columns": missing,
        "rows": [{k: v for k, v in r.items() if not k.startswith("_")} for r in parsed_rows],
        "total_rows": len(rows),
    }


def commit_import(db: Session, user: User, headers: list[str], rows: list[dict]) -> dict:
    columns = _detect_columns(headers)
    missing = [f for f in REQUIRED_FIELDS if f not in columns]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns: {', '.join(missing)}",
        )

    imported_count = 0
    rejected = []
    for idx, row in enumerate(rows, start=2):
        parsed = _validate_row(row, columns, idx)
        if not parsed["valid"]:
            rejected.append({"row_number": idx, "name": parsed["name"], "reason": parsed["error"]})
            continue
        try:
            patient_service.create_patient(
                db,
                user,
                PatientCreateRequest(
                    name=parsed["name"],
                    birth_date=parsed["_parsed_date"],
                    guardian_name=parsed["guardian_name"],
                    diagnosis=parsed["diagnosis"],
                ),
            )
            imported_count += 1
        except HTTPException as exc:
            rejected.append({"row_number": idx, "name": parsed["name"], "reason": str(exc.detail)})

    return {"imported_count": imported_count, "rejected": rejected}


async def commit_import_from_file(db: Session, user: User, file: UploadFile) -> dict:
    headers, rows = await _read_rows(file)
    return commit_import(db, user, headers, rows)
