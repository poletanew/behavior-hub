import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.checklist import ChecklistResponse, CustomChecklistTemplate
from app.models.enums import ChecklistAnswerType
from app.models.user import User
from app.schemas.checklist import ChecklistResponseCreateRequest, ChecklistTemplateCreateRequest
from app.services import audit_service, patient_service


def _tenant_scope_filter(model, user: User):
    if user.clinic_id is not None:
        return model.clinic_id == user.clinic_id
    return model.individual_owner_id == user.id


def create_template(db: Session, user: User, payload: ChecklistTemplateCreateRequest) -> CustomChecklistTemplate:
    """Addendum v3.0, RF-22 — o profissional monta o checklist uma vez
    (pergunta + tipo de resposta) para reaplicar em vários pacientes depois."""
    questions = [
        {"id": uuid.uuid4().hex, "text": q.text, "answer_type": q.answer_type.value} for q in payload.questions
    ]
    template = CustomChecklistTemplate(
        clinic_id=user.clinic_id,
        individual_owner_id=None if user.clinic_id else user.id,
        created_by_user_id=user.id,
        title=payload.title,
        questions=questions,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def list_templates(db: Session, user: User) -> list[CustomChecklistTemplate]:
    return (
        db.query(CustomChecklistTemplate)
        .filter(_tenant_scope_filter(CustomChecklistTemplate, user))
        .order_by(CustomChecklistTemplate.title)
        .all()
    )


def _get_template_or_404(db: Session, user: User, template_id: uuid.UUID) -> CustomChecklistTemplate:
    template = (
        db.query(CustomChecklistTemplate)
        .filter(CustomChecklistTemplate.id == template_id, _tenant_scope_filter(CustomChecklistTemplate, user))
        .first()
    )
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist template not found")
    return template


def _validate_answer_value(question: dict, value) -> None:
    answer_type = question["answer_type"]
    if answer_type == ChecklistAnswerType.YES_NO.value:
        if not isinstance(value, bool):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Question '{question['text']}' expects a yes/no value")
    elif answer_type == ChecklistAnswerType.SCALE.value:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not (1 <= value <= 5):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Question '{question['text']}' expects a scale value from 1 to 5")
    elif answer_type == ChecklistAnswerType.SHORT_TEXT.value:
        if not isinstance(value, str) or not value.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Question '{question['text']}' expects a short text value")


def apply_checklist(
    db: Session, user: User, patient_id: uuid.UUID, payload: ChecklistResponseCreateRequest
) -> ChecklistResponse:
    """Critério de aceite RF-22 — aplicar um checklist a um paciente."""
    patient = patient_service.get_patient_or_404(db, user, patient_id)
    template = _get_template_or_404(db, user, payload.template_id)

    questions_by_id = {q["id"]: q for q in template.questions}
    answered_ids = set()
    for answer in payload.answers:
        question = questions_by_id.get(answer.question_id)
        if question is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown question_id '{answer.question_id}' for this template")
        _validate_answer_value(question, answer.value)
        answered_ids.add(answer.question_id)

    if answered_ids != set(questions_by_id.keys()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="All questions in the template must be answered")

    response = ChecklistResponse(
        clinic_id=patient.clinic_id,
        individual_owner_id=patient.individual_owner_id,
        template_id=template.id,
        patient_id=patient.id,
        applied_by_user_id=user.id,
        answers=[a.model_dump() for a in payload.answers],
    )
    db.add(response)
    db.flush()

    audit_service.record(
        db,
        actor_user_id=user.id,
        action="checklist_applied",
        entity_type="checklist_response",
        entity_id=response.id,
        after={"patient_id": str(patient.id), "template_title": template.title},
    )
    db.commit()
    db.refresh(response)
    return response


def _build_response_detail(response: ChecklistResponse, template: CustomChecklistTemplate) -> dict:
    questions_by_id = {q["id"]: q for q in template.questions}
    items = []
    for answer in response.answers:
        question = questions_by_id.get(answer["question_id"], {})
        items.append(
            {
                "question_id": answer["question_id"],
                "question_text": question.get("text", "Pergunta removida"),
                "answer_type": question.get("answer_type", "short_text"),
                "value": answer["value"],
            }
        )
    return {
        "id": response.id,
        "template_id": response.template_id,
        "template_title": template.title,
        "patient_id": response.patient_id,
        "applied_by_user_id": response.applied_by_user_id,
        "applied_at": response.applied_at,
        "items": items,
    }


def list_patient_responses(db: Session, user: User, patient_id: uuid.UUID) -> list[dict]:
    patient_service.get_patient_or_404(db, user, patient_id)
    responses = (
        db.query(ChecklistResponse)
        .filter(ChecklistResponse.patient_id == patient_id)
        .order_by(ChecklistResponse.applied_at.desc())
        .all()
    )
    templates = {
        t.id: t
        for t in db.query(CustomChecklistTemplate)
        .filter(CustomChecklistTemplate.id.in_([r.template_id for r in responses]))
        .all()
    }
    return [_build_response_detail(r, templates[r.template_id]) for r in responses if r.template_id in templates]


def get_response_detail(db: Session, user: User, response_id: uuid.UUID) -> dict:
    response = db.get(ChecklistResponse, response_id)
    if response is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist response not found")
    patient_service.get_patient_or_404(db, user, response.patient_id)
    template = db.get(CustomChecklistTemplate, response.template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist template not found")
    return _build_response_detail(response, template)
