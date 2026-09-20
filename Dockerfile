FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Etapa de desarrollo
FROM base AS development

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


# Etapa de formateo
FROM base AS formatter

RUN pip install --no-cache-dir black==24.1.0 ruff==0.1.14

COPY . .

CMD ["sh", "-c", "black --config .black . && ruff check --fix"]


# Etapa de produccion
FROM base AS production

RUN useradd --create-home --uid 1000 appuser

COPY app ./app

USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
