"""
RAG Ingest — AIOps SOP/Runbook Ingestion
Membaca dokumen markdown dari folder documents/,
memecahnya menjadi chunks, generate embeddings via Ollama
(nomic-embed-text-v2-moe), dan menyimpannya ke ChromaDB.

Usage:
    python -m rag.ingest
    python -m rag.ingest --docs-dir ./documents --reset
"""

import os
import argparse
import hashlib

import requests
import chromadb

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp_server.config import (
    OLLAMA_BASE_URL,
    OLLAMA_EMBED_MODEL,
    CHROMA_PERSIST_DIR,
    CHROMA_COLLECTION_NAME,
    DOCUMENTS_DIR,
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
    # Ollama /api/embed returns {"embeddings": [[...]]}
    return data["embeddings"][0]


def chunk_markdown(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Pecah teks markdown menjadi chunks berdasarkan heading (##)
    atau berdasarkan panjang karakter jika tidak ada heading.
    """
    chunks = []

    # Coba split berdasarkan heading level 2
    sections = text.split("\n## ")
    if len(sections) > 1:
        for i, section in enumerate(sections):
            if i > 0:
                section = "## " + section
            section = section.strip()
            if len(section) > chunk_size:
                # Sub-split berdasarkan panjang
                for j in range(0, len(section), chunk_size - overlap):
                    chunk = section[j : j + chunk_size]
                    if chunk.strip():
                        chunks.append(chunk.strip())
            elif section:
                chunks.append(section)
    else:
        # Tidak ada heading, split berdasarkan panjang
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i : i + chunk_size]
            if chunk.strip():
                chunks.append(chunk.strip())

    return chunks


def generate_chunk_id(filename: str, chunk_index: int) -> str:
    """Generate deterministic ID untuk chunk."""
    raw = f"{filename}::chunk::{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()


def ingest_documents(docs_dir: str, reset: bool = False):
    """Ingest semua dokumen markdown ke ChromaDB."""
    print("=" * 60)
    print("  AIOps RAG — Document Ingestion")
    print("=" * 60)

    # Init ChromaDB
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    if reset:
        try:
            client.delete_collection(CHROMA_COLLECTION_NAME)
            print("🗑️  Collection reset.")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # Scan documents
    if not os.path.exists(docs_dir):
        print(f"❌ Documents directory not found: {docs_dir}")
        return

    md_files = [f for f in os.listdir(docs_dir) if f.endswith(".md")]
    if not md_files:
        print(f"⚠️  No markdown files found in: {docs_dir}")
        return

    print(f"\n📂 Found {len(md_files)} document(s) in {docs_dir}")

    total_chunks = 0

    for filename in md_files:
        filepath = os.path.join(docs_dir, filename)
        print(f"\n📄 Processing: {filename}")

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Chunk document
        chunks = chunk_markdown(content)
        print(f"   ✂️  Split into {len(chunks)} chunks")

        # Generate embeddings dan insert
        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = generate_chunk_id(filename, i)
            print(f"   🧠 Embedding chunk {i+1}/{len(chunks)}...", end=" ")

            try:
                embedding = get_ollama_embedding(chunk)
                ids.append(chunk_id)
                embeddings.append(embedding)
                documents.append(chunk)
                metadatas.append({
                    "source": filename,
                    "chunk_index": i,
                    "doc_type": "sop" if "sop" in filename.lower() else "runbook",
                })
                print("✅")
            except Exception as e:
                print(f"❌ Error: {e}")

        # Upsert ke ChromaDB
        if ids:
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            total_chunks += len(ids)
            print(f"   📦 Stored {len(ids)} chunks to ChromaDB")

    print(f"\n{'=' * 60}")
    print(f"✅ Ingestion complete: {total_chunks} total chunks from {len(md_files)} documents")
    print(f"   Collection: {CHROMA_COLLECTION_NAME}")
    print(f"   Storage: {CHROMA_PERSIST_DIR}")


def main():
    parser = argparse.ArgumentParser(description="AIOps RAG - Ingest SOP/Runbook documents")
    parser.add_argument("--docs-dir", type=str, default=DOCUMENTS_DIR,
                        help=f"Path to documents directory (default: {DOCUMENTS_DIR})")
    parser.add_argument("--reset", action="store_true",
                        help="Reset ChromaDB collection before ingesting")
    args = parser.parse_args()

    ingest_documents(args.docs_dir, args.reset)


if __name__ == "__main__":
    main()
