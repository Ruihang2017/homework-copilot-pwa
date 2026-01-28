# Homework Copilot PWA

AI-powered homework assistant that helps parents guide their children through homework with curriculum-aligned, progressive hints.

## Features

- **Photo capture/upload** - Snap or upload homework questions
- **AI analysis** - Understands what the question is testing
- **Progressive hints** - Step-by-step guidance without giving answers
- **Personalization** - Adapts to each child's topic-level strengths/weaknesses
- **PWA support** - Works offline, add to home screen on iOS/Android

## Tech Stack

- **Frontend**: React + TypeScript + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI (Python) + async PostgreSQL
- **AI**: OpenAI GPT-4o-mini with vision
- **Auth**: Google OAuth, GitHub OAuth, Email/Password

## Architecture Overview

```mermaid
graph TB
    subgraph frontend [Frontend - React PWA]
        UI[Mobile-First UI]
        Camera[Camera Capture]
        Auth_UI[Auth Components]
        PWA[Service Worker]
    end
    
    subgraph backend [Backend - FastAPI]
        API[REST API]
        AuthService[Auth Service]
        PolicyCompiler[Policy Compiler]
        TopicClassifier[Topic Classifier]
        StateManager[State Manager]
    end
    
    subgraph external [External Services]
        OpenAI[OpenAI GPT-4o-mini]
        GoogleOAuth[Google OAuth]
        GitHubOAuth[GitHub OAuth]
    end
    
    subgraph database [PostgreSQL]
        Users[(users)]
        Profiles[(child_profiles)]
        GlobalState[(user_global_state)]
        TopicState[(child_topic_state)]
        Questions[(questions)]
        Feedback[(feedback_events)]
    end
    
    UI --> API
    Camera --> API
    Auth_UI --> AuthService
    API --> PolicyCompiler
    API --> TopicClassifier
    API --> StateManager
    PolicyCompiler --> OpenAI
    AuthService --> GoogleOAuth
    AuthService --> GitHubOAuth
    StateManager --> TopicState
    StateManager --> GlobalState
    API --> Questions
    API --> Feedback
```

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- Docker & Docker Compose

### 1. Start the database

```bash
docker-compose up -d
```

### 2. Set up the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys

# Run migrations
alembic upgrade head

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
├── frontend/
│   ├── src/
│   │   ├── components/    # UI components
│   │   ├── contexts/      # React contexts
│   │   ├── hooks/         # Custom hooks
│   │   ├── lib/           # Utilities
│   │   ├── pages/         # Page components
│   │   └── types/         # TypeScript types
│   └── public/
└── backend/
    ├── alembic/           # Database migrations
    └── app/
        ├── core/          # Config, security, database
        ├── models/        # SQLAlchemy models
        ├── routers/       # API endpoints
        └── services/      # Business logic
```

## License

MIT
