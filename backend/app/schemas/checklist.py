import datetime
import uuid

from pydantic import BaseModel, Field

from app.models.enums import ChecklistAnswerType


class ChecklistQuestionInput(BaseModel):
    text: str = Field(min_length=1)
    answer_type: ChecklistAnswerType


class ChecklistTemplateCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    questions: list[ChecklistQuestionInput] = Field(min_length=1)


class ChecklistQuestionResponse(BaseModel):
    id: str
    text: str
    answer_type: ChecklistAnswerType


class ChecklistTemplateResponse(BaseModel):
    id: uuid.UUID
    title: str
    questions: list[ChecklistQuestionResponse]
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class ChecklistAnswerInput(BaseModel):
    question_id: str
    value: bool | float | str


class ChecklistResponseCreateRequest(BaseModel):
    template_id: uuid.UUID
    answers: list[ChecklistAnswerInput] = Field(min_length=1)


class ChecklistAnswerItem(BaseModel):
    question_id: str
    question_text: str
    answer_type: ChecklistAnswerType
    value: bool | float | str


class ChecklistResponseDetail(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    template_title: str
    patient_id: uuid.UUID
    applied_by_user_id: uuid.UUID
    applied_at: datetime.datetime
    items: list[ChecklistAnswerItem]
