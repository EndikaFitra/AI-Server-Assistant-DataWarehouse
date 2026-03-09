"""
RAG Retriever — AIOps
Mencari dokumen SOP/Runbook yang relevan dari ChromaDB
berdasarkan query pengguna menggunakan semantic search.
"""

import os
import sys

import requests
import chromadb

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp_server.config import (
    OLLAMA_BASE_URL,
    OLLAMA_EMBED_MODEL,
    CHROMA_PERSIST_DIR,
    CHROMA_COLLECTION_NAME,
)


def get_ollama_embedding(text: str) -> list[float]:
    """Generate embedding via Ollama API."""
    resp = requests.post(
        f"{OLLAMA_BASE_URL}/api/embed",
        json={"model": OLLAMA_EMBED_MODEL, "input": text},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["embeddings"][0]


class RAGRetriever:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        """
        Cari dokumen paling relevan berdasarkan query.

        Returns:
            List of dicts dengan keys: document, source, score, chunk_index
        """
        query_embedding = get_ollama_embedding(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        retrieved = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0.0

                retrieved.append({
                    "document": doc,
                    "source": metadata.get("source", "unknown"),
                    "doc_type": metadata.get("doc_type", "unknown"),
                    "chunk_index": metadata.get("chunk_index", -1),
                    "similarity_score": round(1 - distance, 4),  # cosine: distance → similarity
                })

        return retrieved

    def format_context(self, results: list[dict]) -> str:
        """Format retrieved documents menjadi konteks untuk LLM."""
        if not results:
            return "Tidak ditemukan dokumen SOP/Runbook yang relevan."

        context_parts = []
        for i, r in enumerate(results, 1):
            context_parts.append(
                f"--- Dokumen {i} (Sumber: {r['source']}, "
                f"Tipe: {r['doc_type']}, "
                f"Relevansi: {r['similarity_score']}) ---\n"
                f"{r['document']}"
            )

        return "\n\n".join(context_parts)


# Quick test
if __name__ == "__main__":
    retriever = RAGRetriever()
    query = "bagaimana cara menangani CPU usage yang tinggi?"
    print(f"Query: {query}\n")

    results = retriever.retrieve(query, top_k=3)
    for r in results:
        print(f"📄 [{r['source']}] (score: {r['similarity_score']})")
        print(f"   {r['document'][:150]}...\n")

    print("\n📋 Formatted context:")
    print(retriever.format_context(results))
