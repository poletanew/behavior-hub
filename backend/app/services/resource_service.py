import datetime
import io
import uuid

from fastapi import HTTPException, UploadFile, status
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.enums import ResourceType, ResourceVisibility, UserType
from app.models.resource import Resource
from app.models.user import User
from app.schemas.resource import AIResourceKind, ResourceAIDraftResponse, ResourceAIPublishRequest
from app.services import audit_service, file_service, rbac_service

# Seção 34 — "regras de armazenamento e tamanho de arquivos" fica marcada como
# pendente de confirmação do Product Owner; usamos um padrão conservador de
# engenharia até essa decisão de produto ser confirmada.
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES: dict[str, ResourceType] = {
    "application/pdf": ResourceType.PDF,
    "image/png": ResourceType.IMAGE,
    "image/jpeg": ResourceType.IMAGE,
    "image/webp": ResourceType.IMAGE,
    "text/plain": ResourceType.TEXT,
}


def _tenant_scope_filter(user: User):
    if user.clinic_id is not None:
        return or_(
            Resource.clinic_id == user.clinic_id,
            Resource.individual_owner_id == user.id,
        )
    return Resource.individual_owner_id == user.id


def _tenant_key(user: User) -> str:
    return f"clinic-{user.clinic_id}" if user.clinic_id else f"user-{user.id}"


def list_resources(
    db: Session, user: User, *, category: str | None = None, search: str | None = None
) -> list[Resource]:
    """Seção 15 — biblioteca com busca e filtros; recursos privados só aparecem para o autor."""
    query = db.query(Resource).filter(_tenant_scope_filter(user), Resource.deleted_at.is_(None))
    if user.clinic_id is not None:
        # Dentro da clínica, só mostra privados de outros profissionais se forem próprios.
        query = query.filter(
            or_(
                Resource.visibility == ResourceVisibility.CLINIC_SHARED,
                Resource.uploaded_by_user_id == user.id,
            )
        )
    if category:
        query = query.filter(Resource.category == category)
    if search:
        like = f"%{search.lower()}%"
        query = query.filter(Resource.title.ilike(like))
    return query.order_by(Resource.title).all()


def get_resource_or_404(db: Session, user: User, resource_id: uuid.UUID, *, include_deleted: bool = False) -> Resource:
    query = db.query(Resource).filter(Resource.id == resource_id, _tenant_scope_filter(user))
    if not include_deleted:
        query = query.filter(Resource.deleted_at.is_(None))
    resource = query.first()
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    if (
        user.clinic_id is not None
        and resource.visibility == ResourceVisibility.PRIVATE
        and resource.uploaded_by_user_id != user.id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return resource


async def upload_resource(
    db: Session,
    user: User,
    *,
    title: str,
    description: str | None,
    category: str | None,
    suggested_age_range: str | None,
    visibility: ResourceVisibility,
    file: UploadFile,
) -> Resource:
    """Seção 15 — permitir upload de PDFs, imagens e atividades textuais."""
    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {content_type}",
        )

    body = await file.read()
    if len(body) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds size limit")

    if visibility == ResourceVisibility.CLINIC_SHARED and user.clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Individual accounts cannot share resources with a clinic")

    key = f"resources/{_tenant_key(user)}/{uuid.uuid4()}-{file.filename}"
    file_service.upload_object(key, body, content_type)

    resource = Resource(
        clinic_id=user.clinic_id,
        individual_owner_id=user.id if user.clinic_id is None else None,
        title=title,
        description=description,
        category=category,
        suggested_age_range=suggested_age_range,
        resource_type=ALLOWED_CONTENT_TYPES[content_type],
        file_key=key,
        original_filename=file.filename or "arquivo",
        content_type=content_type,
        size_bytes=len(body),
        visibility=visibility,
        uploaded_by_user_id=user.id,
    )
    db.add(resource)
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="resource_uploaded",
        entity_type="resource",
        entity_id=resource.id,
        after={"title": title},
    )
    db.commit()
    db.refresh(resource)
    return resource


def get_view_url(resource: Resource) -> str:
    return file_service.generate_presigned_url(resource.file_key)


def soft_delete_resource(db: Session, user: User, resource_id: uuid.UUID) -> Resource:
    resource = get_resource_or_404(db, user, resource_id)
    if user.user_type not in (UserType.CLINIC_ADMIN, UserType.INDIVIDUAL) and resource.uploaded_by_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to remove this resource")

    resource.deleted_at = datetime.datetime.now(datetime.timezone.utc)
    resource.deleted_by = user.id
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="resource_deleted",
        entity_type="resource",
        entity_id=resource.id,
    )
    db.commit()
    db.refresh(resource)
    return resource


def restore_resource(db: Session, user: User, resource_id: uuid.UUID) -> Resource:
    resource = get_resource_or_404(db, user, resource_id, include_deleted=True)
    if resource.deleted_at is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Resource is not deleted")
    if user.user_type not in (UserType.CLINIC_ADMIN, UserType.INDIVIDUAL) and not rbac_service.can_restore_deleted_data(
        db, user
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to restore resources")

    resource.deleted_at = None
    resource.deleted_by = None
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="resource_restored",
        entity_type="resource",
        entity_id=resource.id,
    )
    db.commit()
    db.refresh(resource)
    return resource


_AI_KIND_LABELS: dict[AIResourceKind, str] = {
    "historia_social": "História Social",
    "rotina_visual": "Rotina Visual",
    "cartao_comunicacao": "Cartão de Comunicação",
}


def _ai_draft_content(kind: AIResourceKind, theme: str, age_range: str) -> tuple[str, str, str]:
    """RF-12 — "gera um rascunho de recurso terapêutico... que o profissional
    revisa, edita e só então publica". Texto-modelo determinístico por tipo de
    recurso, sem chamada a nenhuma API de IA externa (mesmo princípio já usado
    em report_summary_service/assessment_service/treatment_plan_service).
    Retorna (title, description, content_text)."""
    label = _AI_KIND_LABELS[kind]
    title = f"{label}: {theme}"
    description = f"{label} sobre \"{theme}\", sugerida para a faixa etária {age_range}."

    if kind == "historia_social":
        content_text = (
            f"O que é {theme}?\n"
            f"[Descreva de forma simples e concreta o que é \"{theme}\", adequado para {age_range}.]\n\n"
            f"Por que isso é importante?\n"
            f"[Explique em 1-2 frases por que essa situação importa para a criança/pessoa.]\n\n"
            f"O que eu posso fazer?\n"
            f"[Liste 2-3 comportamentos esperados, em passos simples e positivos.]\n\n"
            f"Como isso me faz sentir?\n"
            f"[Espaço para nomear sentimentos relacionados a \"{theme}\".]"
        )
    elif kind == "rotina_visual":
        content_text = (
            f"Rotina: {theme}\n"
            "1. [Primeiro passo]\n"
            "2. [Segundo passo]\n"
            "3. [Terceiro passo]\n"
            "4. [Quarto passo]\n"
            f"[Ajuste a quantidade e o nível de detalhe dos passos para {age_range}.]"
        )
    else:
        content_text = (
            f"{theme}\n"
            f"[Frase curta ou imagem representando \"{theme}\", em linguagem adequada para {age_range}.]"
        )

    return title, description, content_text


def generate_ai_draft(kind: AIResourceKind, theme: str, age_range: str) -> ResourceAIDraftResponse:
    title, description, content_text = _ai_draft_content(kind, theme, age_range)
    return ResourceAIDraftResponse(
        kind=kind, theme=theme, age_range=age_range, title=title, description=description, content_text=content_text
    )


def _render_ai_resource_pdf(title: str, content_text: str) -> bytes:
    """Cada bloco separado por linha em branco vira um parágrafo (primeira
    linha em destaque, se houver mais de uma) — layout simples o bastante para
    qualquer um dos três tipos de recurso (texto corrido, passos numerados ou
    frase curta)."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    elements = [Paragraph(title, styles["Title"]), Spacer(1, 12)]

    for block in content_text.split("\n\n"):
        lines = [line for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        elements.append(Paragraph(lines[0], styles["Heading3"] if len(lines) > 1 else styles["Normal"]))
        for line in lines[1:]:
            elements.append(Paragraph(line, styles["Normal"]))
        elements.append(Spacer(1, 10))

    elements.append(Paragraph("Gerado por IA — revisado antes da publicação.", styles["Italic"]))
    doc.build(elements)
    return buffer.getvalue()


def publish_ai_resource(db: Session, user: User, payload: ResourceAIPublishRequest) -> Resource:
    """RF-12 — cria o Resource real só quando o profissional confirma
    explicitamente a publicação; o rascunho (gerado por `generate_ai_draft`)
    nunca é salvo sozinho."""
    if payload.visibility == ResourceVisibility.CLINIC_SHARED and user.clinic_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Individual accounts cannot share resources with a clinic"
        )

    pdf_bytes = _render_ai_resource_pdf(payload.title, payload.content_text)
    key = f"resources/{_tenant_key(user)}/{uuid.uuid4()}-{payload.title}.pdf"
    file_service.upload_object(key, pdf_bytes, "application/pdf")

    resource = Resource(
        clinic_id=user.clinic_id,
        individual_owner_id=user.id if user.clinic_id is None else None,
        title=payload.title,
        description=payload.description,
        category=payload.category or _AI_KIND_LABELS[payload.kind],
        suggested_age_range=payload.age_range,
        resource_type=ResourceType.PDF,
        file_key=key,
        original_filename=f"{payload.title}.pdf",
        content_type="application/pdf",
        size_bytes=len(pdf_bytes),
        visibility=payload.visibility,
        uploaded_by_user_id=user.id,
        ai_generated=True,
        ai_reviewed_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(resource)
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="resource_ai_published",
        entity_type="resource",
        entity_id=resource.id,
        after={"title": resource.title, "kind": payload.kind},
    )
    db.commit()
    db.refresh(resource)
    return resource
