<div align="center">

# ⚖️ LawAid

**AI-powered legal assistance platform for Citizens, Police, and Lawyers**

FIR guidance • BNS legal retrieval (RAG) • Legal document OCR & analysis

![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-000000?logo=nextdotjs&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-47A248?logo=mongodb&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

</div>

---

## 📖 Table of Contents

- [About](#-about)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [Lawyer Document OCR](#-lawyer-document-ocr)
- [Running with Docker](#-running-with-docker)
- [API Overview](#-api-overview)
- [Evaluation](#-evaluation)

---

## 🧾 About

**LawAid** makes the Indian legal process easier to understand and navigate. It uses a Retrieval-Augmented Generation (RAG) pipeline over the **Bharatiya Nyaya Sanhita (BNS)** to give grounded legal information, helps file and draft **FIRs**, and gives lawyers tools to parse, summarize, and analyze case documents.

> ⚠️ **Disclaimer:** LawAid provides legal *information*, not legal advice. Always consult a qualified lawyer.

---

## ✨ Features

### 👤 Citizen
- AI legal chat grounded in BNS sections
- "Understand" module to explain legal situations in plain language
- Guided complaint / FIR drafting

### 🚓 Police
- Create and manage new FIRs
- AI-assisted FIR drafting and section suggestions
- Exportable FIR PDFs

### 🧑‍⚖️ Lawyer
- Upload case documents (PDF / DOCX / scanned images)
- Multilingual OCR (English + Hindi) with page-by-page processing
- Case summary, timeline, and analysis views

### 🔎 Platform
- BNS search
- Role-based authentication (JWT in HTTP cookies)
- Multi-provider LLM support with fallbacks (Groq, OpenRouter, Gemini, Cerebras)
- Speech and security modules in the AI pipeline

---

## 🛠 Tech Stack

| Layer      | Technologies |
|------------|--------------|
| Frontend   | Next.js 16, React 19, TypeScript, Tailwind CSS 4, React Query, React Hook Form, Zod, Axios |
| Backend    | FastAPI, SQLAlchemy, Alembic, Pydantic, python-jose, passlib/bcrypt |
| AI / RAG   | ChromaDB, Ollama (`nomic-embed-text`), spaCy, Groq LLM, RapidOCR, Tesseract |
| Databases  | PostgreSQL (SQLite fallback), MongoDB / GridFS, Redis (optional) |
| DevOps     | Docker, Docker Compose |

---

## 📂 Project Structure

```
LawAid/
├── ai/                 # AI pipeline
│   ├── chat/           #   Conversational legal assistant
│   ├── fir_engine/     #   FIR generation logic
│   ├── ocr/            #   OCR utilities
│   ├── rag/            #   BNS retrieval (RAG)
│   ├── security/       #   Safety / guardrails
│   └── speech/         #   Speech input
├── backend/            # FastAPI service
│   ├── app/
│   │   ├── core/       #   Config, settings
│   │   ├── middleware/
│   │   ├── models/     #   SQLAlchemy models
│   │   ├── routers/    #   auth, chat, fir, police, lawyer_*, complaints
│   │   └── services/   #   Business logic (e.g. document parsing)
│   ├── alembic/        #   DB migrations
│   └── tests/
├── frontend/           # Next.js app
│   ├── app/            #   citizen/, police/, lawyer/, bns-search/, login/, register/
│   ├── components/
│   └── lib/            #   API client
├── evaluation/         # Evaluation scripts
├── shared/             # Shared Docker configs
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- Docker (for PostgreSQL, MongoDB, Redis)
- [Ollama](https://ollama.com) with the `nomic-embed-text` model
- (Optional) Tesseract OCR with `eng` and `hin` language packs

### 1. Clone the repository
```bash
git clone https://github.com/yashikasgh/LawAid.git
cd LawAid
```

### 2. Configure environment
```powershell
Copy-Item .env.example .env      # Windows
# cp .env.example .env           # macOS / Linux
```
Set non-placeholder secrets (see [Environment Variables](#-environment-variables)).

### 3. Start databases
```bash
docker compose -f shared/docker/docker-compose.yml up -d
```

### 4. Run the backend
```bash
python -m pip install -r backend/requirements.txt
cd backend
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

### 5. Run the frontend
```powershell
cd frontend
Copy-Item .env.local.example .env.local
npm install
npm run dev
```
App: http://localhost:3000

### 6. Set up the AI pipeline
```bash
python -m pip install -r ai/requirements.txt
python -m spacy download en_core_web_sm
ollama pull nomic-embed-text
```

---

## 🔐 Environment Variables

Key variables from [`.env.example`](.env.example):

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (SQLite fallback locally) |
| `MONGO_URL` | MongoDB / GridFS for file storage |
| `REDIS_URL` | Redis (optional) |
| `JWT_SECRET` | Long random secret (32+ chars) |
| `JWT_EXPIRY_HOURS` | Token lifetime |
| `CORS_ORIGINS` | Allowed frontend origins |
| `GROQ_API_KEY` / `GROQ_MODEL` | Primary LLM provider |
| `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, `CEREBRAS_API_KEY` | Optional fallback providers |
| `TESSERACT_LANGUAGES` | OCR languages, e.g. `eng+hin` |
| `DOCUMENT_OCR_DPI` | OCR render DPI (e.g. `300`) |

> 🔒 **Never commit your real `.env` file or API keys.**

---

## 📄 Lawyer Document OCR

- The Docker backend installs Tesseract with English and Hindi trained data.
- For host-based runs, install Tesseract plus the `eng` and `hin` packs, and verify with `tesseract --list-langs`.
- Configure `TESSERACT_LANGUAGES=eng+hin` and optionally `DOCUMENT_OCR_DPI=300` in `.env`.
- Scanned or mixed PDFs are processed page-by-page. If OCR is unavailable, the document is marked **failed** with an actionable error instead of a false "parsed" result.

---

## 🐳 Running with Docker

The root [`docker-compose.yml`](docker-compose.yml) runs the full stack (PostgreSQL, MongoDB, backend, frontend).

```bash
cp .env.example .env
docker compose up --build
```

| Service    | URL / Port               |
|------------|--------------------------|
| Frontend   | http://localhost:3002    |
| Backend    | http://localhost:8000    |
| PostgreSQL | `localhost:5433`         |
| MongoDB    | `localhost:27018`        |

> The backend container reaches **Ollama on your host** via `http://host.docker.internal:11434`, so keep Ollama running locally.

---

## 🔌 API Overview

Routes are available both directly and under the `/api` prefix.

| Router | Purpose |
|--------|---------|
| `auth` | Register, login, `/auth/me` |
| `chat` | AI legal chat |
| `complaints` | Citizen complaints |
| `fir`, `fir_drafts` | FIR creation and drafts |
| `police` | Police workflows |
| `lawyer_documents`, `lawyer_workflow` | Case documents and analysis |

Health checks: `/health`, `/health/db`, `/health/mongo`. Interactive docs at `/docs`.

---

## 📊 Evaluation

The [`evaluation/`](evaluation) folder contains scripts, ground truth, predictions and reports to measure RAG / FIR section-prediction quality.

```bash
python evaluation/run_evaluation.py
python evaluation/evaluate_metrics.py
```

See [`evaluation_report.md`](evaluation/evaluation_report.md) for results.

---


