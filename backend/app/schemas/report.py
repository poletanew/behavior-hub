import datetime
import uuid

from pydantic import BaseModel, Field


class LinePoint(BaseModel):
    date: datetime.date
    accuracy_pct: float | None
    independence_pct: float | None


class LineSeries(BaseModel):
    training_id: uuid.UUID
    training_title: str
    points: list[LinePoint]


class BarPoint(BaseModel):
    training_id: uuid.UUID
    training_title: str
    accuracy_pct: float | None
    sample_size: int


class StackedBarPoint(BaseModel):
    session_id: uuid.UUID
    date: datetime.date
    distribution_pct: dict[str, float]


class PieData(BaseModel):
    correct: int
    incorrect: int
    partial: int
    no_response: int


class RadarPoint(BaseModel):
    area: str
    accuracy_pct: float | None
    sample_size: int
    insufficient_data: bool


class HeatmapAreaPoint(BaseModel):
    area: str
    trial_count: int
    intensity_pct: float
    intensity_label: str


class CumulativePoint(BaseModel):
    date: datetime.date
    cumulative_correct: int
    cumulative_total: int
    cumulative_independence_pct: float | None


class PeriodComparison(BaseModel):
    available: bool
    message: str | None = None
    period_a_accuracy_pct: float | None = None
    period_b_accuracy_pct: float | None = None
    delta_pct: float | None = None


class ReportDataResponse(BaseModel):
    patient_id: uuid.UUID
    period_start: datetime.date | None
    period_end: datetime.date | None
    total_trials: int
    line: list[LineSeries]
    bar: list[BarPoint]
    stacked_bar: list[StackedBarPoint]
    pie: PieData
    radar: list[RadarPoint]
    cumulative: list[CumulativePoint]
    heatmap: list[HeatmapAreaPoint]
    comparison: PeriodComparison | None = None


class ReportSummaryGenerateRequest(BaseModel):
    period_start: datetime.date
    period_end: datetime.date
    training_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    professional_id: uuid.UUID | None = None


class ReportSummaryUpdateRequest(BaseModel):
    content: str | None = None
    status: str | None = Field(default=None, pattern="^(draft|approved|discarded)$")


class ReportSummaryResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    period_start: datetime.date
    period_end: datetime.date
    version: int
    content: str
    status: str
    generated_by: str
    author_id: uuid.UUID | None

    class Config:
        from_attributes = True
