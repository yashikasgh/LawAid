# LawAid

LawAid is a FastAPI, Next.js, and Python RAG project for FIR guidance and BNS
legal-information retrieval.

## Local setup

1. Copy `.env.example` to `.env` and set non-placeholder secrets.
2. Start PostgreSQL, MongoDB, and Redis:

   ```powershell
   docker compose -f shared/docker/docker-compose.yml up -d
   ```

3. Install backend dependencies and migrate PostgreSQL:

   ```powershell
   python -m pip install -r backend/requirements.txt
   cd backend
   alembic upgrade head
   uvicorn app.main:app --reload --port 8000
   ```

4. In another terminal, set up the frontend:

   ```powershell
   cd frontend
   Copy-Item .env.local.example .env.local
   npm install
   npm run dev
   ```

5. The AI pipeline has separate dependencies in `ai/requirements.txt`. It also
   requires Ollama with the `nomic-embed-text` embedding model and the spaCy
   `en_core_web_sm` model:

   ```powershell
   python -m pip install -r ai/requirements.txt
   python -m spacy download en_core_web_sm
   ```

## Lawyer document OCR

The Docker backend installs Tesseract OCR with English and Hindi trained data.
For host-based backend runs, install Tesseract and the `eng` and `hin` language
packs, then ensure `tesseract --list-langs` includes both values. Configure
`TESSERACT_LANGUAGES=eng+hin` and optionally `DOCUMENT_OCR_DPI=300` in `.env`.
Scanned or mixed PDFs are processed page-by-page; unavailable OCR produces a
failed document with an actionable error instead of a false parsed result.
