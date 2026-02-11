from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import os

from app.core.config import get_settings
from app.routers import auth, profiles, questions, models, rag


settings = get_settings()

# Create upload directory if it doesn't exist (needed before mounting static files)
os.makedirs(settings.upload_dir, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: nothing needed here anymore (directory created above)
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="Homework Copilot API",
    description="AI-powered homework assistant for parents",
    version="1.0.0",
    lifespan=lifespan,
)
# Avoid 307 redirects for trailing slash (e.g. /profiles/ -> /profiles) that can cause redirect loops behind nginx
app.router.redirect_slashes = False

# Session middleware (required for OAuth)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://localhost",
        "http://127.0.0.1",
        "http://0.0.0.0",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(profiles.router, prefix="/profiles", tags=["Child Profiles"])
app.include_router(questions.router, prefix="/questions", tags=["Questions"])
app.include_router(models.router, prefix="/models", tags=["Models"])
app.include_router(rag.router, prefix="/rag", tags=["RAG"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
