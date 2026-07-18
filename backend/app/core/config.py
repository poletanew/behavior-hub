from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "postgresql+psycopg://behavior_hub:behavior_hub@localhost:5432/behavior_hub"

    JWT_SECRET_KEY: str = "change-me-in-env"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "behavior-hub"
    S3_REGION: str = "us-east-1"

    INVITATION_EXPIRATION_DAYS: int = 7
    DELETED_DATA_RETENTION_DAYS: int = 60
    FREE_PLAN_PATIENT_LIMIT: int = 3

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    FRONTEND_URL: str = "http://localhost:5173"

    # Seção 8.3 — nenhum valor de produção é inventado aqui: sem estas variáveis
    # configuradas, os endpoints de checkout/portal retornam um erro claro em
    # vez de tentar chamar a API do Stripe com uma chave inválida.
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    STRIPE_PRICE_ID_BASIC: str | None = None
    STRIPE_PRICE_ID_PREMIUM: str | None = None
    STRIPE_PRICE_ID_ENTERPRISE: str | None = None

    CELERY_TASK_ALWAYS_EAGER: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
