FROM python:3.13-slim

WORKDIR /app

# Install build dependencies for Python packages that require compilation
RUN apt-get update && apt-get install -y \
    git \
    g++ \
    gcc \
    make \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/

# Copy all required files for editable install
COPY predibench-backend/pyproject.toml ./
COPY predibench-core/pyproject.toml ./predibench-core/pyproject.toml
COPY predibench-core/README.md ./predibench-core/README.md
COPY predibench-core/src/predibench/__init__.py ./predibench-core/src/predibench/__init__.py
RUN uv sync --no-dev

# Copy application code and predibench-core source
COPY predibench-backend/main.py ./
COPY predibench-core/src/ ./predibench-core/src/

# Create user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
RUN mkdir -p /home/appuser/.cache/uv && chown -R appuser:appuser /home/appuser/.cache
USER appuser

# Expose port
EXPOSE 8080

# Run the application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]