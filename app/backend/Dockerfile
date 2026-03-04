FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Install python dependencies
RUN pip install --no-cache-dir \
    fastapi uvicorn openai azure-identity faiss-cpu rapidfuzz \
    portalocker openpyxl python-dotenv pandas numpy

# Copy application code
COPY app /code/app
COPY engine-KB /code/engine-KB
COPY .env /code/.env

# Runtime directory will be mounted, but create structure just in case
RUN mkdir -p /code/runtime/index /code/runtime/leads /code/runtime/exports

# Set python path to root so imports work
ENV PYTHONPATH=/code

# Copy start script
COPY app/backend/start.sh /code/start.sh
RUN chmod +x /code/start.sh

EXPOSE 8000

CMD ["./start.sh"]
