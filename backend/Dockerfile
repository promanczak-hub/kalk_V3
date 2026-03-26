# ── Stage 1: Install dependencies ──
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system deps for psycopg2 etc
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* ./

# Install deps (using pip for simplicity in Docker)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir poetry poetry-plugin-export && \
    poetry config virtualenvs.create false && \
    poetry export --without-hashes -f requirements.txt --output requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# ── Stage 2: Runtime ──
FROM python:3.12-slim

WORKDIR /app

# Runtime deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY --from=builder /app/ /app/

# Remove temp/debug scripts that shouldn't be in prod
RUN find /app -maxdepth 1 -name "check_*.py" -delete 2>/dev/null; \
    find /app -maxdepth 1 -name "tmp_*" -delete 2>/dev/null; \
    find /app -maxdepth 1 -name "diag_*" -delete 2>/dev/null; \
    true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
