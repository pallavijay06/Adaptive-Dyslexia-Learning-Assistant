"""Simple FAISS-backed vector store for document chunks."""

from __future__ import annotations

import faiss
import numpy as np

from services import embedding_service


class VectorStoreError(RuntimeError):
    """Base error for vector store failures."""


class VectorStore:
    def __init__(self, embeddings: np.ndarray, metadata: list[dict[str, object]]):
        if embeddings.ndim != 2:
            raise VectorStoreError("Embeddings must be a 2D array.")
        if embeddings.shape[0] != len(metadata):
            raise VectorStoreError("Metadata length must match embeddings count.")

        self._index = faiss.IndexFlatIP(embeddings.shape[1])
        self._index.add(embeddings)
        self._metadata = list(metadata)

    def search(self, query_embedding: np.ndarray, top_k: int = 3) -> list[dict[str, object]]:
        if query_embedding.ndim == 1:
            query_embedding = query_embedding[np.newaxis, :]

        query_embedding = np.asarray(query_embedding, dtype=np.float32)
        if query_embedding.shape[1] != self._index.d:
            raise VectorStoreError("Query embedding dimension does not match index.")

        distances, ids = self._index.search(query_embedding, top_k)
        results: list[dict[str, object]] = []

        for score_list, id_list in zip(distances, ids):
            for score, idx in zip(score_list, id_list):
                if idx < 0:
                    continue
                result = dict(self._metadata[idx])
                result["score"] = float(score)
                results.append(result)

        return results

    def __getstate__(self) -> dict[str, object]:
        return {
            "index_bytes": faiss.serialize_index(self._index),
            "metadata": self._metadata,
        }

    def __setstate__(self, state: dict[str, object]) -> None:
        self._index = faiss.deserialize_index(state["index_bytes"])
        self._metadata = state["metadata"]


def build_index(chunks: list[dict[str, object]]) -> VectorStore:
    """Build a FAISS vector store from document chunks."""
    if not chunks:
        raise VectorStoreError("No chunks were provided to build the index.")

    texts = [chunk["text"] for chunk in chunks]
    embeddings = embedding_service.embed_texts(texts)
    return VectorStore(embeddings, chunks)


def retrieve_relevant_chunks(
    vector_store: VectorStore,
    query_embedding: np.ndarray,
    top_k: int = 3,
) -> list[dict[str, object]]:
    """Search the FAISS vector store using a query embedding."""
    if vector_store is None:
        raise VectorStoreError("Vector store is required for retrieval.")

    return vector_store.search(query_embedding, top_k=top_k)
