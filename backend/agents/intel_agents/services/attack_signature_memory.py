from __future__ import annotations

from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models

from ..tools import build_dedup_text, generate_embedding


class AttackSignatureMemory:
    """Persistent semantic memory for stable attack signatures.

    Uses local embedded Qdrant storage so semantic recall is separated from the
    final adjudication logic. No Docker or standalone Qdrant server is required.
    The index is rebuilt from stable records for consistency.
    """

    def __init__(
        self,
        *,
        base_dir: str | None = None,
        collection_name: str = "wp11_attack_signature_memory",
        vector_size: int = 32,
    ) -> None:
        self.base_dir = Path(base_dir or ".runtime/wp11/vector_memory")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.client = QdrantClient(path=str(self.base_dir))
        self._ensure_collection()

    def rebuild_index(self, stable_records: list[dict[str, Any]]) -> None:
        self.client.delete_collection(self.collection_name)
        self._ensure_collection()
        if not stable_records:
            return
        points = []
        for offset, record in enumerate(stable_records):
            stable_attack_id = str(record.get("stable_attack_id", f"stable_{offset}"))
            points.append(
                models.PointStruct(
                    id=offset + 1,
                    vector=generate_embedding(build_dedup_text(record)),
                    payload={
                        "stable_attack_id": stable_attack_id,
                        "stable_attack_code": record.get("stable_attack_code"),
                        "canonical_name": record.get("canonical_name"),
                        "attack_family": record.get("attack_family"),
                        "source_coverage": record.get("source_coverage", []),
                    },
                )
            )
        self.client.upsert(collection_name=self.collection_name, points=points)

    def semantic_recall(
        self,
        candidate: dict[str, Any],
        *,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        query_vector = generate_embedding(build_dedup_text(candidate))
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=max(1, top_k),
            with_payload=True,
        )
        recalled: list[dict[str, Any]] = []
        for row in response.points:
            payload = row.payload or {}
            recalled.append(
                {
                    "stable_attack_id": payload.get("stable_attack_id"),
                    "stable_attack_code": payload.get("stable_attack_code"),
                    "canonical_name": payload.get("canonical_name"),
                    "attack_family": payload.get("attack_family"),
                    "semantic_score": float(row.score),
                    "source_coverage": payload.get("source_coverage", []),
                }
            )
        return recalled

    def _ensure_collection(self) -> None:
        existing = [item.name for item in self.client.get_collections().collections]
        if self.collection_name in existing:
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.vector_size,
                distance=models.Distance.COSINE,
            ),
        )

    def close(self) -> None:
        self.client.close()
