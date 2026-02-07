"""
RAG (Retrieval-Augmented Generation) Pipeline

Provides curriculum-aligned context to the LLM by:
1. Ingesting curriculum documents into a ChromaDB vector store
2. Retrieving relevant chunks at query time based on topic + grade + curriculum
3. Injecting those chunks into the system prompt for curriculum-aligned responses
"""

from app.services.rag.retriever import retrieve_curriculum_context
from app.services.rag.classifier import classify_topic

__all__ = [
    "retrieve_curriculum_context",
    "classify_topic",
]
