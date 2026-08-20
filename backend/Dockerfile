FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a AS base

ARG PRODUCT_VERSION=0.2.0
ARG REPOSITORY_REVISION=unknown
ARG BUILD_TIME=unknown

LABEL org.opencontainers.image.title="Essentials+ Freelancer backend" \
      org.opencontainers.image.source="https://github.com/itmitalles-de/essentials-freelancer" \
      org.opencontainers.image.version="$PRODUCT_VERSION" \
      org.opencontainers.image.revision="$REPOSITORY_REVISION" \
      org.opencontainers.image.created="$BUILD_TIME"

ENV PRODUCT_VERSION="$PRODUCT_VERSION" \
    REPOSITORY_REVISION="$REPOSITORY_REVISION" \
    BUILD_TIME="$BUILD_TIME"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations

FROM base AS test

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY tests ./tests

CMD ["python", "-m", "pytest", "-q", "tests"]

FROM base AS runtime

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
