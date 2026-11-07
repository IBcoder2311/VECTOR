# ---------- Build dependencies ----------
FROM python:3.13-slim-bookworm AS builder

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /build

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project


# ---------- Runtime image ----------
FROM python:3.13-slim-bookworm AS runtime

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN groupadd --system --gid 10001 vector \
    && useradd --system --uid 10001 --gid vector --home-dir /app vector

COPY --from=builder /opt/venv /opt/venv
COPY --chown=vector:vector . .

# Каталог для загружаемых изображений мероприятий.
RUN mkdir -p /app/frontend/static/uploads/events \
    && chown -R vector:vector /app/frontend/static/uploads

USER vector

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
