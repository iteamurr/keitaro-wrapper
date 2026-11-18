FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH"
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY alembic.ini ./
RUN uv sync --frozen --no-dev && useradd --create-home app
USER app
EXPOSE 8000
CMD ["uvicorn", "keitaro_wrapper.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
