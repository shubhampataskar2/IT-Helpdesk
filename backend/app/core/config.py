from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI IT Helpdesk"
    api_prefix: str = "/api/v1"
    debug: bool = False

    database_url: str = "postgresql+psycopg2://helpdesk:helpdesk@localhost:5432/helpdesk"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14

    cors_origins: str = "http://localhost:3000"

    ai_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    duplicate_threshold: float = 0.80

    mail_enabled: bool = False
    mail_host: str = ""
    mail_port: int = 587
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = "it-helpdesk@example.com"

    frontend_url: str = "http://localhost:3000"

    use_celery: bool = False
    enable_rate_limit: bool = True
    rate_limit_storage: str = "memory://"
    seed_admin_email: str = "admin@helpdesk.io"
    seed_admin_password: str = "admin123!"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
