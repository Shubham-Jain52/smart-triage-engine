FROM python:3.10-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Cloud Run sets the PORT environment variable dynamically (defaults to 8080)
ENV PORT=7860
EXPOSE $PORT

CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT}
