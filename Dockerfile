# syntax=docker/dockerfile:1
FROM python:3.11-slim

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    tini \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DB_PATH=/app/data/entries.db

WORKDIR /app

COPY app/requirements.txt /app/app/requirements.txt
RUN pip install --no-cache-dir -r /app/app/requirements.txt

COPY app /app/app

RUN mkdir -p /app/data

RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "app.bot"]
