"""
J.A.R.V.I.S. 3.0 — Module 7: Company Knowledge (RAG)
Retrieval-Augmented Generation using Pinecone + OpenAI embeddings + Claude.
"""

import hashlib
from typing import Optional

import tiktoken
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

from config.settings import settings
from utils.helpers import get_logger, retry
from llm.claude import chat

logger = get_logger("knowledge")

_oai = OpenAI(api_key=settings.OPENAI_API_KEY)
_pc = Pinecone(api_key=settings.PINECONE_API_KEY)

EMBED_DIM = 1536  # text-embedding-3-small dimension
CHUNK_SIZE = 500  # tokens per chunk
CHUNK_OVERLAP = 50
TOP_K = 5


# ─────────────────── Pinecone Index ───────────────────────────

def get_index():
    """Get or create the Pinecone index."""
    existing = [i.name for i in _pc.list_indexes()]
    if settings.PINECONE_INDEX not in existing:
        logger.info(f"Creating Pinecone index: {settings.PINECONE_INDEX}")
        _pc.create_index(
            name=settings.PINECONE_INDEX,
            dimension=EMBED_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    return _pc.Index(settings.PINECONE_INDEX)


# ─────────────────── Embeddings ───────────────────────────────

@retry(max_attempts=2)
def embed(text: str) -> list[float]:
    """Embed a string using OpenAI text-embedding-3-small."""
    response = _oai.embeddings.create(
        model=settings.EMBED_MODEL,
        input=text[:8000],  # safety limit
    )
    return response.data[0].embedding


# ─────────────────── Chunking ─────────────────────────────────

def chunk_text(text: str) -> list[str]:
    """Split text into overlapping token chunks."""
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    chunks = []
    i = 0
    while i < len(tokens):
        chunk_tokens = tokens[i: i + CHUNK_SIZE]
        chunks.append(enc.decode(chunk_tokens))
        i += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


# ─────────────────── Ingestion ────────────────────────────────

def ingest_document(
    text: str,
    doc_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> int:
    """
    Ingest a document into the knowledge base.

    Args:
        text: Raw document text.
        doc_id: Unique document identifier (auto-generated if None).
        metadata: Extra metadata to store with each chunk.

    Returns:
        Number of chunks ingested.
    """
    index = get_index()
    doc_id = doc_id or hashlib.md5(text[:200].encode()).hexdigest()
    chunks = chunk_text(text)
    meta = metadata or {}

    vectors = []
    for i, chunk in enumerate(chunks):
        vector_id = f"{doc_id}_chunk_{i}"
        embedding = embed(chunk)
        vectors.append({
            "id": vector_id,
            "values": embedding,
            "metadata": {**meta, "text": chunk, "doc_id": doc_id, "chunk_index": i},
        })

    # Upsert in batches of 100
    batch_size = 100
    for j in range(0, len(vectors), batch_size):
        index.upsert(
            vectors=vectors[j: j + batch_size],
            namespace=settings.PINECONE_NAMESPACE,
        )

    logger.info(f"Ingested {len(chunks)} chunks for doc_id={doc_id}")
    return len(chunks)


def delete_document(doc_id: str):
    """Delete all chunks for a document."""
    index = get_index()
    index.delete(
        filter={"doc_id": {"$eq": doc_id}},
        namespace=settings.PINECONE_NAMESPACE,
    )
    logger.info(f"Deleted document: {doc_id}")


# ─────────────────── Retrieval ────────────────────────────────

@retry(max_attempts=2)
def retrieve(query: str, top_k: int = TOP_K) -> list[dict]:
    """Retrieve the most relevant chunks for a query."""
    index = get_index()
    query_embedding = embed(query)
    result = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        namespace=settings.PINECONE_NAMESPACE,
    )
    matches = []
    for match in result.get("matches", []):
        if match.get("score", 0) > 0.3:  # relevance threshold
            matches.append({
                "text": match["metadata"].get("text", ""),
                "score": match["score"],
                "doc_id": match["metadata"].get("doc_id", ""),
                "source": match["metadata"].get("source", "Company KB"),
            })
    return matches


# ─────────────────── RAG Answer Generation ────────────────────

_RAG_SYSTEM = """You are J.A.R.V.I.S., answering questions using the provided company knowledge.
Rules:
- Answer ONLY from the context provided below.
- If the answer is not in the context, say: "I don't have information about that in the knowledge base."
- Be concise and factual.
- Format nicely for Telegram (use *bold* and bullet points).

Context:
{context}"""


def answer_with_rag(question: str) -> tuple[str, list[dict]]:
    """
    Answer a question using RAG.

    Returns:
        (answer_text, list_of_source_chunks)
    """
    chunks = retrieve(question)
    if not chunks:
        return (
            "❓ I couldn't find relevant information in the knowledge base for that question.",
            [],
        )

    context = "\n\n---\n\n".join(
        f"[Source: {c['source']}]\n{c['text']}" for c in chunks
    )
    system = _RAG_SYSTEM.format(context=context)
    answer = chat(question, system=system, max_tokens=600)
    return answer, chunks


# ─────────────────── Natural Language Handler ─────────────────

async def handle_knowledge(user_message: str) -> str:
    """Main entrypoint called by the Telegram router."""
    import re
    query = re.sub(r"^/(knowledge|faq)\s*", "", user_message, flags=re.IGNORECASE).strip()

    if not query:
        return "❓ What would you like to know? Ask me anything about company knowledge or policies."

    try:
        answer, sources = answer_with_rag(query)
        if sources:
            source_names = list({c["source"] for c in sources})
            footer = f"\n\n_Sources: {', '.join(source_names)}_"
            return answer + footer
        return answer
    except Exception as e:
        logger.error(f"Knowledge error: {e}", exc_info=True)
        return f"⚠️ Knowledge base error: {e}"


# ─────────────────── CLI Ingestion Utility ────────────────────

if __name__ == "__main__":
    """
    Run directly to ingest a document:
    python -m knowledge.rag --file path/to/doc.txt --id my_doc
    """
    import argparse

    parser = argparse.ArgumentParser(description="Ingest a document into JARVIS knowledge base")
    parser.add_argument("--file", required=True, help="Path to text file to ingest")
    parser.add_argument("--id", help="Document ID (optional)")
    parser.add_argument("--source", default="Company KB", help="Source label")
    args = parser.parse_args()

    with open(args.file, "r", encoding="utf-8") as f:
        content = f.read()

    n = ingest_document(content, doc_id=args.id, metadata={"source": args.source})
    print(f"✅ Ingested {n} chunks from {args.file}")
