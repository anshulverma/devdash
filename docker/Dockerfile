# Standalone devdash runner image. Multi-stage: build the UI bundle, then run
# the FastAPI app serving the bundle as static assets. Fleshed out in M2/M5.
# syntax=docker/dockerfile:1
FROM python:3.12-slim AS runtime
WORKDIR /app
COPY packages/api /app/packages/api
RUN pip install --no-cache-dir -e /app/packages/api
EXPOSE 8000
ENTRYPOINT ["python", "-m", "devdash"]
