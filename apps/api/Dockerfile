FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc curl \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/api/ ./apps/api/
COPY engine-KB/ ./engine-KB/
COPY scripts/ ./scripts/
COPY .env .env

# Runtime dirs (volumes will mount over these at runtime, creating them here ensures they exist)
RUN mkdir -p /app/runtime /app/indices

ENV PYTHONPATH=/app/apps/api

COPY apps/api/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
