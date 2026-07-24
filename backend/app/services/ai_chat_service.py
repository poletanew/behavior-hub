import json

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.schemas.ai_chat import AIChatMessage

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MAX_TOKENS = 1000

# Seção 12.1/14.5 do PRD — botão flutuante "Fale com a IA do Behavior Hub":
# nunca emite diagnóstico, nunca afirma causalidade clínica definitiva, e
# deixa claro que sugestões precisam de revisão profissional antes de serem
# aplicadas a um paciente real.
CHAT_SYSTEM_PROMPT = (
    "Você é a IA do Behavior Hub, assistente virtual dentro do sistema para "
    "profissionais de terapia infantil (ABA, Psicologia, Fonoaudiologia, Terapia "
    "Ocupacional, Psicopedagogia e áreas afins). Ajude com dúvidas sobre como usar "
    "o sistema, sugestões de estratégias e treinos, e dúvidas gerais sobre análise "
    "do comportamento aplicada. Responda em português do Brasil, de forma objetiva "
    "e acolhedora. Nunca emita diagnóstico, nunca afirme causalidade clínica "
    "definitiva, e deixe claro quando uma sugestão precisa de revisão do "
    "profissional antes de ser aplicada a um paciente real."
)


async def _call_anthropic(system_prompt: str, messages: list[dict]) -> str:
    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="IA não configurada neste servidor. Defina ANTHROPIC_API_KEY para habilitar este recurso.",
        )

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.ANTHROPIC_MODEL,
                "max_tokens": MAX_TOKENS,
                "system": system_prompt,
                "messages": messages,
            },
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível falar com a IA agora. Tente novamente em instantes.",
        )

    data = response.json()
    block = next((b for b in data.get("content", []) if b.get("type") == "text"), None)
    if not block:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Resposta vazia da IA.")
    return block["text"]


async def ask_chat(messages: list[AIChatMessage]) -> str:
    return await _call_anthropic(CHAT_SYSTEM_PROMPT, [{"role": m.role, "content": m.content} for m in messages])


async def generate_json(system_prompt: str, user_prompt: str) -> dict:
    """Geração estruturada de um único turno (Seção 12.1/14.5) — usada pelos
    botões "Preencher com IA" que produzem um rascunho em JSON a partir de um
    prompt curto (ex.: título do treino), sempre revisável antes de salvar."""
    text = await _call_anthropic(system_prompt, [{"role": "user", "content": user_prompt}])
    cleaned = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Resposta da IA em formato inesperado."
        ) from exc
