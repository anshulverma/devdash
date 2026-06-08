# devdash standalone runner — multi-stage: build the UI bundle, then serve it
# from the FastAPI app. Build context is the repo root:
#   docker build -f docker/Dockerfile -t devdash .
# syntax=docker/dockerfile:1

# --- Stage 1: build the standalone UI bundle ------------------------------
FROM node:24-slim AS ui
ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
RUN corepack enable
WORKDIR /src
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.base.json ./
COPY packages/ui ./packages/ui
COPY standalone-ui ./standalone-ui
RUN pnpm install --frozen-lockfile \
 && pnpm -C packages/ui build \
 && pnpm -C standalone-ui build

# --- Stage 2: python runtime ----------------------------------------------
FROM python:3.12-slim AS runtime
WORKDIR /app
COPY packages/api /app/packages/api
# Drop in the freshly built UI bundle (replaces the dev placeholder).
RUN rm -rf /app/packages/api/src/devdash/static/* || true
COPY --from=ui /src/standalone-ui/dist/ /app/packages/api/src/devdash/static/
RUN pip install --no-cache-dir /app/packages/api
EXPOSE 8000
ENV DEVDASH_DATABASE_URL=sqlite+aiosqlite:////data/devdash.db
VOLUME ["/data"]
ENTRYPOINT ["python", "-m", "devdash", "serve", "--host", "0.0.0.0", "--port", "8000"]
