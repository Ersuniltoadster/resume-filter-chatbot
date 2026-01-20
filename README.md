 # Resume Filter Chatbot
 
 A FastAPI backend that helps you ingest resumes, extract structured profiles, store resume vectors in Pinecone, and query candidates using a single chat endpoint.
 
 ## Features
 
 - **Google Drive ingestion** (fetch resumes from a folder)
 - **Text extraction** for PDFs / Docs
 - **LLM-based resume profile extraction** (Groq)
 - **Embeddings + semantic search** using Pinecone (resume-level vectors)
 - **Single chat API** (`/chat/ask`) that can:
   - filter by **skill / years**
   - handle **JD-like text** and return best matching resumes
 
 ## Tech Stack
 
 - **API**: FastAPI
 - **Database**: PostgreSQL (metadata + structured resume profiles + job/file status)
 - **Vectors**: Pinecone (resume vectors)
 - **LLM**: Groq
 - **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
 - **Async processing**: Celery + Redis
 - **Migrations**: Alembic
 
 ---
 
 ## Repo Safety (Important)
 
 Do **NOT** commit any of these to GitHub:
 
 - `.env`
 - `keys/*.json` (Google service account keys)
 - `resume_folder/` (any resume PDFs / outputs)
 - `*.llm.json` (generated outputs)
 - any files containing real API keys
 
 Use `.env.example` as a template and keep real secrets only in your local `.env`.
 
 If a secret was ever committed, rotate/revoke it immediately.
 
 ---
 
 ## Setup
 
 ### 1) Prerequisites
 
 - Python (see `.python-version`)
 - PostgreSQL
 - Redis
 - Pinecone index:
   - **dimension**: `384`
   - **metric**: `cosine`
 - Groq API key
 - Google Drive Service Account JSON key (keep locally, never commit)
 
 ### 2) Install dependencies
 
 This repo uses `pyproject.toml` + `uv.lock`.
 
 If you use `uv`:
 
 ```bash
 uv sync
 ```
 
 If you use `pip`, install dependencies using your preferred method (for example, export requirements from your lockfile or install from `pyproject.toml` tooling).
 
 ### 3) Configure environment variables
 
 Copy `.env.example` to `.env`:
 
 ```bash
 cp .env.example .env
 ```
 
 Update values in `.env`.
 
 Typical required variables:
 
 - `APP_ENV`
 - `DATABASE_URL`
 - `REDIS_URL`
 - `GROQ_API_KEY`
 - `PINECONE_API_KEY`
 - `PINECONE_INDEX_HOST`
 - `PINECONE_NAMESPACE`
 - `GDRIVE_SERVICE_ACCOUNT_JSON_PATH`
 - `EMBEDDING_MODEL_NAME`
 
 ---
 
 ## Database migrations
 
 Run migrations:
 
 ```bash
 alembic upgrade head
 ```
 
 ---
 
 ## Run the API
 
 From the repo root:
 
 ```bash
 python -m uvicorn app.main:app --reload
 ```
 
 Open:
 
 - Swagger UI: `http://127.0.0.1:8000/docs`
 
 Main routes:
 
 - `GET /health/...`
 - `POST /ingest/...`
 - `GET /jobs/...`
 - `POST /chat/ask`
 
 ---
 
 ## Run the worker (Celery)
 
 Start Redis first (how you run Redis depends on your OS).
 
 Then start the Celery worker:
 
 ```bash
 python -m celery -A app.celery_app.celery_app worker -Q ingest -l info
 ```
 
 ---
 
 ## Notes
 
 - Resume vectors are stored in **Pinecone**.
 - Postgres stores:
   - resume metadata
   - structured `resume_profile`
   - ingestion job/file status
 - Chat uses intent classification to decide whether to:
   - do structured filtering (skill/years)
   - do semantic matching (JD-like text) using Pinecone
 
 ---
 
 ## License
 
 Add a license if you want this project to be open-source.
