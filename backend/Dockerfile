# ============================================================
# Lentis Gallery — Backend Production Dockerfile
# ============================================================
# Multi-stage build:
#   Stage 1: Install Python dependencies
#   Stage 2: Production runtime (minimal image)
#
# Usage:
#   docker build -t lentis-backend ./backend
# ============================================================

# ---- Stage 1: Install dependencies ----
FROM python:3.13-slim AS builder

WORKDIR /app

# Install system dependencies required for building Python packages
# (needed for psycopg, argon2-cffi, Pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---- Stage 2: Production runtime ----
FROM python:3.13-slim AS production

# Install runtime-only system dependencies
# libpq5 is needed by psycopg at runtime
# libjpeg62-turbo and libpng for Pillow image processing
# libsm6/libxext6/libxrender1 for Pillow image handling
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libjpeg62-turbo \
    libpng16-16 \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Create non-root user for security
RUN groupadd -r lentis && useradd -r -g lentis -d /app -s /sbin/nologin lentis

# Copy application code
COPY alembic.ini .
COPY alembic/ ./alembic/
COPY app/ ./app/

# Create storage directory for local provider (if needed)
RUN mkdir -p /app/storage && chown -R lentis:lentis /app

# Switch to non-root user
USER lentis

# Expose the application port
EXPOSE 8000

# Liveness check — fast, no dependency checks
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Production command: uvicorn with appropriate settings
# - No --reload (production)
# - Workers based on CPU count (default 2 is reasonable for our workload)
# - Access logs for debugging
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--access-log", \
     "--log-level", "info"]
