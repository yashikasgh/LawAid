FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt /app/backend-requirements.txt
COPY ai/requirements.txt /app/ai-requirements.txt

RUN pip install --no-cache-dir -r /app/backend-requirements.txt
RUN pip install --no-cache-dir pymupdf groq spacy chromadb ollama python-dotenv docxtpl
RUN python -m spacy download en_core_web_sm

# Copy full application
COPY . /app

WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
