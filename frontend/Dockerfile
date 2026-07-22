# Build multi-stage: Node só pra compilar o bundle estático, Nginx só pra servir + fazer
# proxy reverso pro backend -- a imagem final não carrega Node/npm nenhum, só os arquivos
# estáticos + nginx (bem menor, sem superfície de ataque de ferramentas de build).
FROM node:24-slim AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# VITE_API_BASE_URL relativo (2026-07-21, ver docs/DEPLOY.md) -- em vez de apontar pra um
# host:porta fixo (o que exigiria rebuildar a imagem pra cada ambiente/teste vs produção),
# o frontend chama "/api/v1" relativo à própria origem, e o nginx.conf abaixo faz proxy
# reverso desse caminho pro serviço "backend" do Compose. Mesma imagem funciona em teste E
# produção, só o nginx.conf/rede do Compose muda de onde "backend" resolve.
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
