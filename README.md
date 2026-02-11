# Homework Copilot PWA

AI-powered homework assistant that helps parents guide their children through homework with curriculum-aligned, step-by-step explanations and real syllabus context via RAG.

## Features

- **Photo capture/upload** - Snap or upload homework questions
- **AI analysis** - Understands what the question is testing and provides step-by-step solutions
- **Curriculum RAG** - Retrieves real syllabus outcomes (NSW, VIC, QLD, AU/ACARA) to align explanations with what students are expected to learn
- **Multi-model selection** - Choose between GPT-5.2, GPT-5 Mini, GPT-4o, and GPT-4o Mini with speed/quality trade-off guidance
- **Math rendering** - LaTeX/KaTeX rendering for proper display of fractions, exponents, and equations
- **Personalization** - Adapts to each child's topic-level strengths/weaknesses via a three-layer state model
- **Interactive diagrams** - Auto-generated SVG diagrams for geometry questions, linked to solution steps
- **PWA support** - Works offline, add to home screen on iOS/Android

## Tech Stack

- **Frontend**: React + TypeScript + Vite + Tailwind CSS + shadcn/ui + KaTeX
- **Backend**: FastAPI (Python) + async PostgreSQL + Alembic
- **AI**: OpenAI GPT-4o / GPT-4o-mini / GPT-5.x (multi-provider abstraction)
- **RAG**: LangChain + ChromaDB + OpenAI Embeddings
- **Auth**: Google OAuth, GitHub OAuth, Email/Password (JWT)
- **Infrastructure**: Docker Compose + Nginx reverse proxy + Certbot (HTTPS)

## Architecture Overview

```mermaid
graph TB
    subgraph frontend [Frontend - React PWA]
        UI[Mobile-First UI]
        Camera[Camera Capture]
        MathRender[KaTeX Math Rendering]
        ModelSelect[Model Selector]
    end

    subgraph backend [Backend - FastAPI]
        API[REST API]
        AuthService[Auth Service]
        PolicyCompiler[Policy Compiler]
        Orchestrator[LLM Orchestrator]
        StateReducer[State Reducer]
    end

    subgraph rag [RAG Pipeline]
        Classifier[Topic Classifier]
        Retriever[Curriculum Retriever]
        ChromaDB[(ChromaDB)]
    end

    subgraph llm [LLM Providers]
        ChatAPI[OpenAI Chat API]
        ResponsesAPI[OpenAI Responses API]
    end

    subgraph database [PostgreSQL]
        Users[(users)]
        Profiles[(child_profiles)]
        GlobalState[(user_global_state)]
        TopicState[(child_topic_state)]
        Questions[(questions)]
        Feedback[(feedback_events)]
    end

    subgraph curriculum [Curriculum Docs]
        ACARA[AU ACARA]
        NESA[NSW NESA]
        QCAA[QLD QCAA]
        VCAA[VIC VCAA]
    end

    UI --> API
    Camera --> API
    ModelSelect --> API
    API --> Classifier
    Classifier -->|topic query| Retriever
    Retriever --> ChromaDB
    ChromaDB -.->|ingested from| curriculum
    Retriever -->|curriculum context| PolicyCompiler
    PolicyCompiler --> Orchestrator
    Orchestrator --> ChatAPI
    Orchestrator --> ResponsesAPI
    API --> StateReducer
    StateReducer --> TopicState
    StateReducer --> GlobalState
    API --> Questions
    API --> Feedback
```

### RAG Data Flow

When a homework image is submitted:

1. **Classify** - gpt-4o-mini identifies the topic in ~2-3s (e.g., "adding fractions with unlike denominators")
2. **Retrieve** - ChromaDB finds the 4 most relevant curriculum chunks, filtered by the child's curriculum (e.g., NSW)
3. **Compile** - The policy compiler injects the retrieved syllabus text into the system prompt
4. **Analyze** - The main LLM generates a curriculum-aligned response with real outcome references

## Quick Start (Docker)

### Prerequisites

- Docker & Docker Compose

### Local vs production (nginx)

- **Production (e.g. EC2):** Uses `nginx/nginx.conf` with HTTPS and Let’s Encrypt certs. No override file.
- **Local (e.g. your Mac):** The main nginx config expects certs that don’t exist locally, so nginx would fail. Use the **local override** so nginx runs HTTP-only:
  1. Create `docker-compose.override.yml` in the project root with:
     ```yaml
     services:
       nginx:
         volumes:
           - ./nginx/nginx.local.conf:/etc/nginx/conf.d/default.conf:ro
     ```
  2. This file is in `.gitignore` — do not commit it. That way EC2 never sees it and keeps using the production config and certs.
  3. The repo includes `nginx/nginx.local.conf` (HTTP on port 80, no SSL) for local use.

### 1. Create environment file

Create a `.env` file in the project root with your API key(s):

```bash
cat > .env << 'EOF'
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4o
SECRET_KEY=your-super-secret-key
EOF
```

Optional OAuth (only if you plan to use Google/GitHub login):

```
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
```

### 2. Build and start the stack

```bash
docker compose build
docker compose up -d
```

### 3. Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### 4. Ingest curriculum documents (RAG)

```bash
docker compose exec backend python -m app.services.rag.ingest
```

This processes the curriculum PDFs/DOCX files into ChromaDB embeddings. Only needs to be run once, or after adding new curriculum documents.

### 5. Open the app

Visit http://localhost (or https://your-domain if running in production with certs).

You can also check the backend health endpoint at:

```
http://localhost/health
```

Check RAG status:

```
http://localhost/rag/status
```

## Local Development (Non-Docker)

### Prerequisites

- Node.js 18+
- Python 3.11+
- Docker (for Postgres) or local Postgres install

### 1. Start the database

```bash
docker compose up -d postgres
```

### 2. Set up the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env and add your API keys
# Example:
# OPENAI_API_KEY=sk-your-key

# Run migrations
alembic upgrade head

# Ingest curriculum documents into ChromaDB
python -m app.services.rag.ingest

# Start the server
uvicorn app.main:app --reload
```

### 3. Set up the frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Open the app

Visit http://localhost:5173

## Environment Variables

### Docker (.env at project root)

```
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o
SECRET_KEY=your-secret-key-here
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

### Backend (.env)

```
DATABASE_URL=postgresql+asyncpg://homework_user:homework_pass@localhost:5432/homework_copilot
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000
```

### Frontend (.env)

```
VITE_API_URL=http://localhost:8000
```

## Project Structure

```
homework-copilot-pwa/
├── docker-compose.yml
├── curriculum_docs/            # Raw curriculum documents for RAG
│   ├── AU_ACARA/               # Australian Curriculum (ACARA)
│   ├── NSW_NESA/               # NSW syllabus (NESA)
│   ├── QLD_QCAA/               # Queensland curriculum (QCAA)
│   └── VIC_VCAA/               # Victorian curriculum (VCAA)
├── frontend/
│   ├── src/
│   │   ├── components/         # UI components (MathText, DiagramRenderer, Layout)
│   │   ├── contexts/           # React contexts (AuthContext)
│   │   ├── hooks/              # Custom hooks
│   │   ├── lib/                # Utilities (api client with auto token refresh)
│   │   ├── pages/              # Page components (Dashboard, Capture, Analysis, Settings)
│   │   └── types/              # TypeScript types
│   └── public/
├── nginx/
│   ├── nginx.conf              # Production: HTTPS + Let’s Encrypt (used on EC2)
│   └── nginx.local.conf        # Local: HTTP only (used via docker-compose.override.yml)
└── backend/
    ├── alembic/                # Database migrations
    ├── chroma_data/            # ChromaDB vector store (auto-generated)
    └── app/
        ├── core/               # Config, security, database
        ├── models/             # SQLAlchemy models
        ├── routers/            # API endpoints (auth, profiles, questions, models, rag)
        └── services/
            ├── llm/            # Multi-provider LLM abstraction
            │   ├── base.py             # Abstract LLMProvider
            │   ├── openai_chat.py      # GPT-4o / 4o-mini (Chat Completions API)
            │   ├── openai_responses.py # GPT-5.x (Responses API)
            │   ├── registry.py         # Model registry + provider factory
            │   ├── orchestrator.py     # Shared JSON parsing + retry logic
            │   └── models.py           # Pydantic response models
            ├── rag/            # Curriculum RAG pipeline
            │   ├── ingest.py           # Document loading, chunking, embedding
            │   ├── retriever.py        # ChromaDB query service
            │   └── classifier.py       # Quick topic classification
            ├── policy_compiler.py      # Three-layer state -> LLM prompt
            └── state_reducer.py        # Feedback -> state updates
```

## Adding Curriculum Documents

To add new curriculum documents:

1. Place PDF or DOCX files in the appropriate `curriculum_docs/` subfolder
2. Name files descriptively (e.g., `NSW_NESA_Math_K-10_2022.docx`)
3. Re-run ingestion:
   ```bash
   # Docker
   docker compose exec backend python -m app.services.rag.ingest

   # Local
   cd backend && python -m app.services.rag.ingest
   ```
4. Verify with `GET /rag/status` to check chunk count and curricula

## License

MIT
