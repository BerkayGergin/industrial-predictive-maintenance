FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy only runtime application code. Local .env files, Git metadata,
# tests and documentation never enter image layers.
COPY --chown=appuser:appuser analytics ./analytics
COPY --chown=appuser:appuser backend ./backend
COPY --chown=appuser:appuser collector ./collector
COPY --chown=appuser:appuser common ./common
COPY --chown=appuser:appuser dashboard ./dashboard
COPY --chown=appuser:appuser simulator ./simulator

USER appuser

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
