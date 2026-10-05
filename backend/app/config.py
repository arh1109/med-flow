from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:password@127.0.0.1:5432/medflow"
    secret_key: str
    frontend_origin: str = "http://localhost:5173"
    diagnostics_bucket_name: str = "medflow-diagnostics-ah1109"

    access_token_expire_minutes: int = 1
    refresh_token_expire_days: int = 7

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()