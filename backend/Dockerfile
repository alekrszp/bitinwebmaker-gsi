# Imagem do backend (FastAPI) -- built context é a RAIZ do repo, não backend/ (ver
# docker-compose.yml, `build: {context: ., dockerfile: backend/Dockerfile}`), porque
# backend/ importa direto de scripts/ e config/ (mesmo padrão de sys.path usado em
# tests/, ver backend/scripts_path.py) -- as 3 pastas precisam estar juntas na imagem,
# na mesma estrutura relativa que já existe no repo.
FROM python:3.14-slim AS base

WORKDIR /app

# Camada de dependências separada da camada de código -- rebuild de código não reinstala
# tudo de novo, só quando requirements.txt muda.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Só o necessário em runtime -- não copia tests/, frontend/src, node_modules, .venv (ver
# .dockerignore na raiz).
COPY backend/ backend/
COPY scripts/ scripts/
COPY config/ config/
COPY migrations/ migrations/
COPY alembic.ini alembic.ini
# scripts/bitin_pdf.py lê a logo daqui (frontend/public/brand/gpt-color.png) -- só essa
# subpasta, não o frontend inteiro (que tem seu próprio Dockerfile/imagem).
COPY frontend/public/brand/ frontend/public/brand/

EXPOSE 8000

# --proxy-headers (2026-07-21, deploy atrás de nginx/reverse proxy, ver frontend/nginx.conf)
# -- sem isso, o FastAPI vê toda requisição como vinda do proxy (X-Forwarded-* ignorado),
# o que quebra client IP/scheme em qualquer log ou lógica que dependa disso no futuro.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
