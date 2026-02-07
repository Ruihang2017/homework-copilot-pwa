"""
RAG Admin Router

Provides endpoints to check RAG status and trigger re-ingestion.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.rag.retriever import get_vector_store_status

router = APIRouter()


class RAGStatusResponse(BaseModel):
    available: bool
    chunk_count: int
    curricula: list[str] = []
    persist_dir: str
    message: str = ""


@router.get("/status", response_model=RAGStatusResponse)
async def rag_status():
    """Check the status of the RAG vector store."""
    info = get_vector_store_status()
    return RAGStatusResponse(**info)


@router.post("/ingest")
async def trigger_ingestion():
    """
    Trigger curriculum document re-ingestion.

    This re-processes all documents in curriculum_docs/ and rebuilds
    the ChromaDB vector store. Useful after adding new curriculum files.
    """
    try:
        from app.services.rag.ingest import run_ingestion
        run_ingestion()
        status_info = get_vector_store_status()
        return {
            "status": "success",
            "message": f"Ingestion complete. {status_info['chunk_count']} chunks stored.",
            "chunk_count": status_info["chunk_count"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}",
        )
