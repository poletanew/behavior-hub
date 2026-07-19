from pydantic import BaseModel, field_validator

HEX_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"


class WhiteLabelUpdateRequest(BaseModel):
    logo_url: str | None = None
    brand_color: str | None = None
    display_name: str | None = None

    @field_validator("brand_color")
    @classmethod
    def _validate_hex_color(cls, value: str | None) -> str | None:
        import re

        if value is not None and not re.match(HEX_COLOR_PATTERN, value):
            raise ValueError("brand_color must be a hex color like #1D4ED8")
        return value


class WhiteLabelResponse(BaseModel):
    enabled: bool
    logo_url: str | None
    brand_color: str | None
    display_name: str | None


class PublicBrandingResponse(BaseModel):
    """Retornado ao Family Portal (contas `family`) e usado internamente pela
    exportação de Reports — nunca expõe dados administrativos da clínica,
    apenas os três campos de marca."""

    enabled: bool
    logo_url: str | None
    brand_color: str | None
    display_name: str | None
