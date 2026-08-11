FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NEUROVI_TOOLS_ROOT=/opt/neurovi
ENV NEUROVI_REPO_ROOT=/repository

WORKDIR /opt/neurovi

COPY pyproject.toml README.md AGENTS.md ./
COPY src ./src
COPY scripts ./scripts
COPY .codex ./.codex

RUN pip install --no-cache-dir ".[discord]" \
    && useradd --create-home --uid 10001 neurovi

USER neurovi
WORKDIR /repository

CMD ["neurovi-discord"]
