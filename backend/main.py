import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.db.mongodb import close_mongo_connection, connect_to_mongo
from backend.db.session import Base, engine

# Sem logging nenhum configurado antes -- uma falha (Mongo fora do ar, JWT inválido, corrida
# de envio) não deixava rastro nenhum além da resposta HTTP. Config simples, nível INFO,
# suficiente pra diagnosticar sem precisar de infra de log estruturado ainda.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_SECRET_KEY = "dev-secret-troque-em-producao"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Antes disso, um deploy sem .env configurado subia silenciosamente com a SECRET_KEY
    # padrão -- qualquer um forjaria um token de admin válido. Falha alto e claro em vez de
    # silenciosamente inseguro; só se aplica quando ENVIRONMENT=production é setado de
    # propósito (dev local/testes nunca setam isso, então continuam passando sem .env).
    if settings.ENVIRONMENT == "production" and settings.SECRET_KEY == _DEFAULT_SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY não pode ser o valor padrão com ENVIRONMENT=production. "
            "Configure uma SECRET_KEY real via .env antes de subir em produção."
        )
    # Mantido como conveniência de dev/teste (adicionado o Alembic em 2026-07-15, ver
    # migrations/ e docs/BACKEND.md): tests/test_backend_*.py criam um SQLite em memória por
    # teste e chamam Base.metadata.create_all diretamente (não passam por este lifespan, nem
    # por migração nenhuma) -- então remover esta linha não afetaria os testes, mas
    # continuaria criando qualquer tabela nova automaticamente em dev local sem precisar
    # rodar `alembic upgrade head` toda hora. Idempotente (CREATE TABLE IF NOT EXISTS), então
    # não conflita com um banco já migrado via Alembic -- mas a partir de agora, Alembic é a
    # fonte de verdade pra mudança de schema (novas colunas/tabelas viram migração, não só
    # uma mudança em auth/models.py ou models_sql.py).
    Base.metadata.create_all(bind=engine)
    await connect_to_mongo()
    logger.info("BITin API iniciada (ambiente=%s)", settings.ENVIRONMENT)
    yield
    await close_mongo_connection()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# allow_origins=["*"] + allow_credentials=True é uma combinação inválida/insegura (achado da
# revisão do GPT_Engineering_authAPI, que tinha exatamente esse bug) -- lista explícita das
# origens permitidas. Vem de CORS_ORIGINS (.env, ver backend/config.py) -- default cobre só as
# portas de dev do Vite; qualquer deploy real (teste ou produção, ver docs/DEPLOY.md) precisa
# setar essa variável com a URL de verdade do frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "BITin API"}


from backend.api.bitins import router as bitins_router  # noqa: E402
from backend.api.subgrupos import router as subgrupos_router  # noqa: E402
from backend.api.users import router as users_router  # noqa: E402
from backend.auth.routes import router as auth_router  # noqa: E402

app.include_router(bitins_router, prefix=f"{settings.API_V1_STR}/bitins", tags=["bitins"])
app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users_router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(subgrupos_router, prefix=f"{settings.API_V1_STR}/subgrupos", tags=["subgrupos"])
