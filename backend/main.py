from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.db.mongodb import close_mongo_connection, connect_to_mongo
from backend.db.session import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    await connect_to_mongo()
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
# origens do frontend em dev; trocar/expandir quando houver domínio de produção.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "BITin API"}


from backend.api.bitins import router as bitins_router  # noqa: E402
from backend.api.sectors import router as sectors_router  # noqa: E402
from backend.api.users import router as users_router  # noqa: E402
from backend.auth.routes import router as auth_router  # noqa: E402

app.include_router(bitins_router, prefix=f"{settings.API_V1_STR}/bitins", tags=["bitins"])
app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users_router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(sectors_router, prefix=f"{settings.API_V1_STR}/sectors", tags=["sectors"])
