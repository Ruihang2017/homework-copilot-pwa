"""
RAG Retriever Service

Queries the ChromaDB vector store at runtime to find curriculum chunks
that are semantically similar to the detected homework topic.

Uses the chromadb client directly (not langchain_chroma) to avoid
LangChain Document deserialization that can raise KeyError('_type').

How retrieval works:
1. The topic_query string is converted into a vector using OpenAI embeddings.
2. ChromaDB compares this vector against stored chunk vectors (cosine similarity).
3. If a curriculum filter is provided, only chunks from that curriculum are searched.
4. The top-K chunk texts are concatenated and returned for the LLM system prompt.
"""

import os
from types import SimpleNamespace

import chromadb
from langchain_openai import OpenAIEmbeddings

from app.core.config import get_settings


# ── Singleton: chromadb client + collection + embeddings ──────────────────────

_rag_store: SimpleNamespace | None = None


def _get_vector_store() -> SimpleNamespace | None:
    """
    Get or create ChromaDB connection using chromadb client directly
    (avoids langchain_chroma so we never touch Document/_type deserialization).
    """
    global _rag_store
    if _rag_store is not None:
        return _rag_store

    settings = get_settings()
    persist_dir = settings.chroma_persist_dir

    if not os.path.exists(persist_dir):
        print("[RAG] ChromaDB directory not found — RAG disabled (run ingestion first)")
        return None

    try:
        client = chromadb.PersistentClient(path=persist_dir)
        collection = client.get_or_create_collection("curriculum")
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=settings.openai_api_key,
        )
    except Exception as e:
        if str(e) == "'_type'":
            print(
                "[RAG] Failed to load ChromaDB index: incompatible persisted format "
                "(missing '_type'). Re-run ingestion to rebuild index."
            )
        else:
            print(f"[RAG] Failed to load ChromaDB: {e}")
        return None

    count = collection.count()
    print(f"[RAG] ChromaDB loaded: {count} chunks available")
    _rag_store = SimpleNamespace(
        collection=collection,
        embedding_function=embeddings,
    )
    return _rag_store


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

    collection = store.collection
    count = collection.count()

    try:
        all_meta = collection.get(include=["metadatas"])
        curricula = sorted(set(
            (m or {}).get("curriculum", "unknown")
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
        coll = store.collection
        embed_fn = store.embedding_function
        query_embedding = embed_fn.embed_query(enriched_query)
        result = coll.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas"],
        )
        # result["documents"] = [[doc1, doc2, ...]], result["metadatas"] = [[meta1, ...]]
        docs_list = result["documents"][0] if result["documents"] else []
        metas_list = result["metadatas"][0] if result["metadatas"] else []
    except Exception as e:
        print(f"[RAG] Retrieval failed: {e}")
        return None

    if not docs_list:
        print(f"[RAG] No results for query: {enriched_query}")
        return None

    # Format the retrieved chunks with their source info (raw dicts, no Document)
    chunks = []
    for i, (text, meta) in enumerate(zip(docs_list, metas_list)):
        meta = meta or {}
        source = meta.get("source_file", "unknown")
        cur = meta.get("curriculum", "unknown")
        chunks.append(
            f"[{cur} — {source}]\n{(text or '').strip()}"
        )

    context = "\n\n---\n\n".join(chunks)
    print(f"[RAG] Retrieved {len(chunks)} chunks for: {enriched_query}")
    return context
