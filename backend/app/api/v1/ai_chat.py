from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.ai_chat import AIChatRequest, AIChatResponse
from app.services import ai_chat_service

router = APIRouter(tags=["ai-chat"])


@router.post("/ai/chat", response_model=AIChatResponse)
async def chat(payload: AIChatRequest, user: User = Depends(get_current_user)):
    """Seção 12.1/14.5 — botão flutuante "Fale com a IA do Behavior Hub". A chave
    da Anthropic fica só no servidor (ANTHROPIC_API_KEY); o frontend nunca a vê."""
    reply = await ai_chat_service.ask_chat(payload.messages)
    return AIChatResponse(reply=reply)
