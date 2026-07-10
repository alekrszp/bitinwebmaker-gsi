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

    # Autenticação -- serviço separado (GPT_Engineering_authAPI), não roda dentro deste
    # backend. AUTH_SECRET_KEY/AUTH_ALGORITHM precisam ser IDÊNTICOS ao SECRET_KEY/ALGORITHM
    # do .env do serviço de auth (mesma chave em dois arquivos .env distintos, mantida em
    # sincronia manualmente) -- é assim que este backend valida a assinatura do JWT sem
    # nenhuma chamada de rede. Ver docs/BACKEND.md, seção "Autenticação".
    AUTH_SECRET_KEY: str = "secret"
    AUTH_ALGORITHM: str = "HS256"
    AUTH_API_URL: str = "http://localhost:8001"

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")


settings = Settings()
