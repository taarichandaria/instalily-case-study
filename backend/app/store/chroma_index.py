"""Chroma vector index for Part records.

Each Part becomes one document. Document text is a composite blob
(name + description + symptoms + appliance + brand) that we embed with
OpenAI `text-embedding-3-small`. Metadata is kept thin — full Part data
lives in SQLite.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterable

import chromadb
from chromadb.config import Settings

from app.schemas import Part

log = logging.getLogger(__name__)

CHROMA_DIR = Path(__file__).resolve().parents[2] / "data" / "chroma"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

COLLECTION = "parts"
EMBED_MODEL = "text-embedding-3-small"

_client: chromadb.ClientAPI | None = None
_openai = None


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def _get_openai():
    global _openai
    if _openai is None:
        from openai import OpenAI

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set — required for embeddings")
        _openai = OpenAI(api_key=api_key)
    return _openai


def _get_collection():
    client = _get_client()
    return client.get_or_create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def _document_text(part: Part) -> str:
    """Composite text used as the embedding target."""
    parts = [
        part.name,
        f"Appliance: {part.appliance_type}.",
    ]
    if part.brand:
        parts.append(f"Brand: {part.brand}.")
    if part.description:
        parts.append(part.description)
    if part.symptoms_fixed:
        parts.append("Fixes: " + "; ".join(part.symptoms_fixed))
    if part.oem_number:
        parts.append(f"OEM part number: {part.oem_number}.")
    return " ".join(parts)


def _metadata(part: Part) -> dict[str, str | float | bool]:
    md: dict[str, str | float | bool] = {
        "ps_number": part.ps_number,
        "appliance_type": part.appliance_type,
        "name": part.name,
    }
    if part.brand:
        md["brand"] = part.brand
    if part.price_usd is not None:
        md["price_usd"] = float(part.price_usd)
    return md


def embed_batch(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    client = _get_openai()
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [item.embedding for item in resp.data]


def upsert_parts(parts: Iterable[Part]) -> int:
    batch = list(parts)
    if not batch:
        return 0
    docs = [_document_text(p) for p in batch]
    embeddings = embed_batch(docs)
    coll = _get_collection()
    coll.upsert(
        ids=[p.ps_number for p in batch],
        documents=docs,
        metadatas=[_metadata(p) for p in batch],
        embeddings=embeddings,
    )
    return len(batch)


def search(
    query: str,
    *,
    n_results: int = 5,
    appliance_type: str | None = None,
    brand: str | None = None,
) -> list[dict]:
    coll = _get_collection()
    where: dict = {}
    if appliance_type:
        where["appliance_type"] = appliance_type
    if brand:
        where["brand"] = brand
    # Chroma requires a single key at top-level; wrap multi-field in $and
    w = None
    if len(where) == 1:
        w = where
    elif len(where) > 1:
        w = {"$and": [{k: v} for k, v in where.items()]}

    q_emb = embed_batch([query])[0]
    res = coll.query(
        query_embeddings=[q_emb],
        n_results=n_results,
        where=w,
    )
    out: list[dict] = []
    ids = (res.get("ids") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    distances = (res.get("distances") or [[]])[0]
    for i, ps_number in enumerate(ids):
        meta = metas[i] if i < len(metas) else {}
        dist = distances[i] if i < len(distances) else None
        out.append(
            {
                "ps_number": ps_number,
                "name": meta.get("name") if meta else None,
                "appliance_type": meta.get("appliance_type") if meta else None,
                "brand": meta.get("brand") if meta else None,
                "price_usd": meta.get("price_usd") if meta else None,
                "score": (1.0 - dist) if dist is not None else None,
            }
        )
    return out


def reset() -> None:
    """Delete the collection so we can re-index from scratch."""
    client = _get_client()
    try:
        client.delete_collection(COLLECTION)
    except Exception:  # noqa: BLE001
        pass


def size() -> int:
    return _get_collection().count()
