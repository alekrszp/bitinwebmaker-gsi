from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "BITin API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Postgres (metadado: código, status) -- SQLite em teste, ver docs/BACKEND.md
    DATABASE_URL: str = "sqlite:///./bitin_backend.db"

    # MongoDB (conteúdo completo do BITin)
    MONGO_URL: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "bitin_db"

    # Autenticação -- unificada neste backend (ver docs/BACKEND.md, seção "Autenticação").
    # SECRET_KEY tem que ser trocada por um valor real via .env em qualquer ambiente que não
    # seja dev local -- o default aqui existe só pra não quebrar sqlite/testes sem .env.
    SECRET_KEY: str = "dev-secret-troque-em-producao"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")


settings = Settings()
