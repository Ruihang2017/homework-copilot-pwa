"""
RAG Retriever Service

Queries the ChromaDB vector store at runtime to find curriculum chunks
that are semantically similar to the detected homework topic.

How retrieval works:
1. The topic_query string (e.g., "adding fractions with unlike denominators")
   is converted into a 1536-dim vector using OpenAI embeddings.
2. ChromaDB compares this vector against all stored curriculum chunk vectors
   using cosine similarity (how "close" the meanings are).
3. If a curriculum filter is provided (e.g., "NSW"), only chunks from that
   curriculum are searched — this uses ChromaDB's metadata filtering.
4. The top-K most similar chunk texts are concatenated and returned
   for injection into the LLM system prompt.
"""

import os
from functools import lru_cache

from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from app.core.config import get_settings


# ── Singleton Vector Store ───────────────────────────────────────────────────

_vector_store: Chroma | None = None


def _get_vector_store() -> Chroma | None:
    """
    Get or create the ChromaDB vector store connection (lazy singleton).

    Returns None if the ChromaDB directory doesn't exist yet
    (i.e., ingestion hasn't been run).
    """
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    settings = get_settings()
    persist_dir = settings.chroma_persist_dir

    if not os.path.exists(persist_dir):
        print("[RAG] ChromaDB directory not found — RAG disabled (run ingestion first)")
        return None

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.openai_api_key,
    )

    _vector_store = Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings,
        collection_name="curriculum",
    )

    count = _vector_store._collection.count()
    print(f"[RAG] ChromaDB loaded: {count} chunks available")
    return _vector_store


def get_vector_store_status() -> dict:
    """Return status info about the vector store for the /rag/status endpoint."""
    settings = get_settings()
    persist_dir = settings.chroma_persist_dir

    if not os.path.exists(persist_dir):
        return {
            "available": False,
            "chunk_count": 0,
            "persist_dir": os.path.abspath(persist_dir),
            "message": "ChromaDB not initialized. Run ingestion first.",
        }

    store = _get_vector_store()
    if store is None:
        return {
            "available": False,
            "chunk_count": 0,
            "persist_dir": os.path.abspath(persist_dir),
            "message": "Failed to load ChromaDB.",
        }

    collection = store._collection
    count = collection.count()

    # Get unique curricula from metadata
    try:
        all_meta = collection.get(include=["metadatas"])
        curricula = sorted(set(
            m.get("curriculum", "unknown")
            for m in all_meta["metadatas"]
        ))
    except Exception:
        curricula = []

    return {
        "available": True,
        "chunk_count": count,
        "curricula": curricula,
        "persist_dir": os.path.abspath(persist_dir),
    }


# ── Retrieval ────────────────────────────────────────────────────────────────

async def retrieve_curriculum_context(
    topic_query: str,
    grade: str,
    curriculum: str | None = None,
    top_k: int = 4,
) -> str | None:
    """
    Retrieve relevant curriculum chunks for a homework topic.

    Args:
        topic_query: Natural language description of the topic
                     (e.g., "adding fractions with unlike denominators")
        grade: The child's grade level (e.g., "year_5")
        curriculum: Optional curriculum code to filter by (e.g., "NSW")
        top_k: Number of chunks to retrieve (default 4)

    Returns:
        Concatenated text of the most relevant curriculum chunks,
        or None if RAG is not available.

    How it works:
        1. topic_query is embedded into a vector
        2. ChromaDB searches for the nearest vectors (by cosine similarity)
        3. Metadata filter restricts results to the specified curriculum
        4. Top-K chunk texts are joined with separators and returned
    """
    store = _get_vector_store()
    if store is None:
        return None

    # Build metadata filter
    where_filter = None
    if curriculum:
        where_filter = {"curriculum": curriculum}

    # Build a richer query by including grade context
    grade_readable = grade.replace("_", " ").title()  # "year_5" -> "Year 5"
    enriched_query = f"{grade_readable} {topic_query}"

    try:
        results = store.similarity_search(
            query=enriched_query,
            k=top_k,
            filter=where_filter,
        )
    except Exception as e:
        print(f"[RAG] Retrieval failed: {e}")
        return None

    if not results:
        print(f"[RAG] No results for query: {enriched_query}")
        return None

    # Format the retrieved chunks with their source info
    chunks = []
    for i, doc in enumerate(results, 1):
        source = doc.metadata.get("source_file", "unknown")
        cur = doc.metadata.get("curriculum", "unknown")
        chunks.append(
            f"[{cur} — {source}]\n{doc.page_content.strip()}"
        )

    context = "\n\n---\n\n".join(chunks)
    print(f"[RAG] Retrieved {len(results)} chunks for: {enriched_query}")
    return context
