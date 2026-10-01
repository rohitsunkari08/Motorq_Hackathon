"""Retrieval-Augmented Generation (RAG) and pgvector Knowledge Base Service.

Per NOTE.md §4 / §6.6:
- pgvector HNSW, 384-dim
- embeddings 'all-MiniLM-L6-v2' local
- RAG over docs/kb/*.md synthetic docs
"""

import os
import glob
import math
import hashlib
from typing import List, Dict, Any, Optional
import asyncpg
import numpy as np

_EMBEDDER = None


def get_embedder():
    global _EMBEDDER
    if _EMBEDDER is None:
        try:
            from sentence_transformers import SentenceTransformer
            _EMBEDDER = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
        except Exception:
            # Fallback to deterministic projection
            pass
    return _EMBEDDER


def embed_text(text: str) -> List[float]:
    """Generate 384-dimensional dense embedding vector."""
    embedder = get_embedder()
    if embedder is not None:
        try:
            vec = embedder.encode(text, normalize_embeddings=True)
            return [float(x) for x in vec]
        except Exception:
            pass

    # Deterministic 384-dimensional unit vector projection fallback
    # Uses SHA-512 + sha-256 rolling hash to populate 384 floats, normalized to L2 norm 1.0
    dim = 384
    words = text.lower().split()
    vec = np.zeros(dim, dtype=np.float32)

    for i, w in enumerate(words):
        h = hashlib.sha256(w.encode("utf-8")).digest()
        for j in range(min(len(h), 32)):
            idx = (int(h[j]) * 31 + j + i) % dim
            vec[idx] += (float(h[j]) / 128.0 - 1.0)

    # Add whole text hash
    h_full = hashlib.sha512(text.encode("utf-8")).digest()
    for k in range(len(h_full)):
        vec[k % dim] += (float(h_full[k]) / 128.0 - 1.0)

    norm = np.linalg.norm(vec)
    if norm > 1e-6:
        vec = vec / norm
    else:
        vec[0] = 1.0

    return [float(x) for x in vec]


def get_query_embedding(query: str) -> List[float]:
    return embed_text(query)


async def index_kb_documents(postgres_url: str, kb_dir: str = "docs/kb") -> int:
    """Read all markdown docs in kb_dir, chunk them, embed, and store in doc_chunk."""
    md_files = glob.glob(os.path.join(kb_dir, "*.md"))
    if not md_files:
        return 0

    chunks_to_insert = []
    for fpath in md_files:
        src = os.path.basename(fpath)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        # Split by section / paragraphs
        raw_paras = content.split("\n\n")
        current_chunk = []
        current_len = 0

        for p in raw_paras:
            clean_p = p.strip()
            if not clean_p:
                continue
            if current_len + len(clean_p) > 600 and current_chunk:
                chunks_to_insert.append((src, "\n\n".join(current_chunk)))
                current_chunk = [clean_p]
                current_len = len(clean_p)
            else:
                current_chunk.append(clean_p)
                current_len += len(clean_p)

        if current_chunk:
            chunks_to_insert.append((src, "\n\n".join(current_chunk)))

    if not chunks_to_insert:
        return 0

    conn = await asyncpg.connect(postgres_url)
    try:
        # Clear existing doc chunks for idempotency
        await conn.execute("DELETE FROM doc_chunk;")

        for src, chunk_text in chunks_to_insert:
            emb = embed_text(chunk_text)
            emb_str = f"[{','.join(f'{x:.6f}' for x in emb)}]"
            await conn.execute(
                """
                INSERT INTO doc_chunk (source, content, embedding)
                VALUES ($1, $2, $3::vector);
                """,
                src,
                chunk_text,
                emb_str,
            )

        count = await conn.fetchval("SELECT count(*) FROM doc_chunk;")
        return count
    finally:
        await conn.close()
