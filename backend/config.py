from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "BITin API"
    VERSION: str = "0.8.5"
    API_V1_STR: str = "/api/v1"

    # "production" liga checagens de segurança na subida do app (ver main.py::lifespan) --
    # default "development" pra não quebrar dev local/testes, que nunca setam isso via .env.
    ENVIRONMENT: str = "development"

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

    # Origens permitidas pro CORS (2026-07-21, achado ao preparar o deploy de teste/produção,
    # ver docs/DEPLOY.md) -- string separada por vírgula em vez de list[str] direto porque
    # variável de ambiente é sempre string; pydantic-settings parseia list[str] como JSON por
    # padrão, o que exigiria escrever `["a","b"]` no .env (chato de digitar/errar). Default
    # cobre só as portas de dev do Vite -- QUALQUER deploy real (teste ou produção) precisa
    # definir CORS_ORIGINS explicitamente com a URL de verdade do frontend, senão o navegador
    # bloqueia toda chamada à API.
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")


settings = Settings()
