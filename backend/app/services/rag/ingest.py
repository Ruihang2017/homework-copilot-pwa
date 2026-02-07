"""
Curriculum Document Ingestion Script

Loads curriculum documents (PDF, DOCX) from the curriculum_docs/ directory,
splits them into chunks, embeds them using OpenAI, and stores them in ChromaDB.

How it works:
1. LOAD   – LangChain document loaders read raw files into Document objects
2. TAG    – Metadata (curriculum, grade_range, subject) extracted from folder/filename
3. SPLIT  – RecursiveCharacterTextSplitter breaks docs into ~500-char chunks
           (Embeddings work best on focused, paragraph-sized text — not entire docs)
4. EMBED  – OpenAI text-embedding-3-small converts each chunk to a 1536-dim vector
           (These vectors encode semantic meaning: "fractions" ≈ "common fractions")
5. STORE  – Chroma.from_documents() saves vectors + text + metadata to disk
           (Persisted to chroma_data/ so it survives restarts)

Usage:
    cd backend
    python -m app.services.rag.ingest
"""

import os
import re
import sys
from pathlib import Path

from langchain_community.document_loaders import Docx2txtLoader, PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma


# ── Metadata Extraction ──────────────────────────────────────────────────────

# Map folder names to curriculum codes used in the app
FOLDER_TO_CURRICULUM = {
    "AU_ACARA": "AU",
    "NSW_NESA": "NSW",
    "QLD_QCAA": "QLD",
    "VIC_VCAA": "VIC",
}

# Try to extract grade range from filename patterns like "F-10", "K-10", "7-10", "F-6"
GRADE_RANGE_PATTERN = re.compile(r"[FK]?-?\d+[-–]\d+[A-Za-z]?")


def extract_metadata_from_path(file_path: str) -> dict:
    """
    Extract curriculum and grade metadata from the file's directory and name.

    For example:
        curriculum_docs/NSW_NESA/NSW_NESA_Math_K-10_2022.docx
        → curriculum="NSW", grade_range="K-10", subject="math"
    """
    p = Path(file_path)
    folder = p.parent.name  # e.g., "NSW_NESA"
    filename = p.stem        # e.g., "NSW_NESA_Math_K-10_2022"

    curriculum = FOLDER_TO_CURRICULUM.get(folder, folder)

    # Extract grade range
    grade_match = GRADE_RANGE_PATTERN.search(filename)
    grade_range = grade_match.group(0) if grade_match else "unknown"

    # Subject is always math for now
    subject = "math" if "math" in filename.lower() else "unknown"

    return {
        "curriculum": curriculum,
        "grade_range": grade_range,
        "subject": subject,
        "source_file": p.name,
    }


# ── Document Loading ─────────────────────────────────────────────────────────

def load_documents(docs_dir: str) -> list:
    """
    Walk the curriculum_docs directory and load all PDF/DOCX files.

    LangChain loaders handle the file format differences:
    - Docx2txtLoader: extracts text from .docx files
    - PyMuPDFLoader: extracts text from .pdf files (fast, no system deps)

    Each loader returns a list of Document objects with .page_content (text)
    and .metadata (source path, page number, etc).
    """
    documents = []
    docs_path = Path(docs_dir)

    if not docs_path.exists():
        print(f"[Ingest] Directory not found: {docs_dir}")
        return documents

    for file_path in sorted(docs_path.rglob("*")):
        if file_path.suffix.lower() == ".docx":
            print(f"[Ingest] Loading DOCX: {file_path.name}")
            loader = Docx2txtLoader(str(file_path))
        elif file_path.suffix.lower() == ".pdf":
            print(f"[Ingest] Loading PDF:  {file_path.name}")
            loader = PyMuPDFLoader(str(file_path))
        else:
            continue

        try:
            docs = loader.load()
            # Enrich each document with our curriculum metadata
            file_meta = extract_metadata_from_path(str(file_path))
            for doc in docs:
                doc.metadata.update(file_meta)
            documents.extend(docs)
            print(f"  → {len(docs)} page(s) loaded")
        except Exception as e:
            print(f"  → ERROR loading {file_path.name}: {e}")

    return documents


# ── Chunking ─────────────────────────────────────────────────────────────────

def split_documents(documents: list) -> list:
    """
    Split documents into smaller chunks for embedding.

    WHY chunk?
    - An embedding of an entire 50-page document captures its overall theme,
      but is too vague to match a specific topic like "adding fractions".
    - Smaller chunks (~500 chars) produce embeddings that are focused on
      one concept, making retrieval much more accurate.

    HOW RecursiveCharacterTextSplitter works:
    - Tries to split at paragraph boundaries (\\n\\n) first
    - Falls back to sentence boundaries (. ! ?) then words
    - chunk_overlap=100 means chunks share ~100 chars of context at edges,
      preventing content from being cut in half
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    chunks = splitter.split_documents(documents)
    return chunks


# ── Embedding & Storage ──────────────────────────────────────────────────────

def create_vector_store(chunks: list, persist_dir: str, openai_api_key: str) -> Chroma:
    """
    Embed chunks and store them in ChromaDB.

    HOW embeddings work:
    - OpenAI's text-embedding-3-small model converts each chunk into
      a vector of 1536 floating-point numbers.
    - These numbers encode semantic meaning: chunks about "fractions"
      will have vectors that are close to each other in this 1536-dim space.

    HOW ChromaDB stores them:
    - Each entry has: (vector, original_text, metadata)
    - The vectors are indexed for fast cosine-similarity search
    - Data is persisted to `persist_dir` on disk (survives restarts)
    """
    print(f"\n[Ingest] Creating embeddings with OpenAI text-embedding-3-small...")
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=openai_api_key,
    )

    # Remove old data if it exists (full re-ingest)
    if os.path.exists(persist_dir):
        import shutil
        print(f"[Ingest] Removing old ChromaDB data at {persist_dir}")
        shutil.rmtree(persist_dir)

    print(f"[Ingest] Storing {len(chunks)} chunks in ChromaDB at {persist_dir}...")
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_dir,
        collection_name="curriculum",
    )

    return vector_store


# ── Main ─────────────────────────────────────────────────────────────────────

def run_ingestion(docs_dir: str | None = None, persist_dir: str | None = None):
    """Run the full ingestion pipeline."""
    # Resolve paths
    from app.core.config import get_settings
    settings = get_settings()

    if not docs_dir:
        docs_dir = settings.curriculum_docs_dir
    if not persist_dir:
        persist_dir = settings.chroma_persist_dir

    if not settings.openai_api_key:
        print("[Ingest] ERROR: OPENAI_API_KEY is not set. Cannot create embeddings.")
        sys.exit(1)

    print("=" * 60)
    print("Curriculum RAG Ingestion Pipeline")
    print("=" * 60)
    print(f"  Documents dir: {os.path.abspath(docs_dir)}")
    print(f"  ChromaDB dir:  {os.path.abspath(persist_dir)}")
    print()

    # Step 1: Load documents
    print("[Step 1] Loading curriculum documents...")
    documents = load_documents(docs_dir)
    if not documents:
        print("[Ingest] No documents found. Exiting.")
        sys.exit(1)
    print(f"\n  Total pages loaded: {len(documents)}")

    # Step 2: Split into chunks
    print(f"\n[Step 2] Splitting into chunks (size=500, overlap=100)...")
    chunks = split_documents(documents)
    print(f"  Total chunks created: {len(chunks)}")

    # Show sample metadata
    curricula = set(c.metadata.get("curriculum", "?") for c in chunks)
    print(f"  Curricula found: {', '.join(sorted(curricula))}")

    # Step 3: Embed and store
    print(f"\n[Step 3] Embedding and storing in ChromaDB...")
    vector_store = create_vector_store(chunks, persist_dir, settings.openai_api_key)

    # Verify
    collection = vector_store._collection
    count = collection.count()
    print(f"\n{'=' * 60}")
    print(f"Ingestion complete! {count} chunks stored in ChromaDB.")
    print(f"{'=' * 60}")

    return vector_store


if __name__ == "__main__":
    run_ingestion()
