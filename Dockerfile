# Image backend FastAPI — ClassroomObserv
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# ping (iputils) necessaire au service de supervision reseau
RUN apt-get update \
    && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && uv pip install --system --no-cache .

COPY app ./app
COPY scripts ./scripts
COPY alembic ./alembic
COPY alembic.ini ./

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
