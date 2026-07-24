from pydantic import BaseModel, Field


class AIChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class AIChatRequest(BaseModel):
    messages: list[AIChatMessage]


class AIChatResponse(BaseModel):
    reply: str
