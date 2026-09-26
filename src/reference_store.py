"""
ASI Perception System — Asset Reference Store
Spec: PER-REID-006 → 010

Stores known asset embedding fingerprints on disk and matches
incoming embeddings against them using cosine similarity.

Storage format: one .npz file per asset in data/reference_db/
"""

import json
import numpy as np
import yaml
from pathlib import Path
from datetime import datetime, timezone


class ReferenceStore:
    """
    Persistent database of known asset embedding fingerprints.

    Each registered asset has:
      - A unique asset_id (e.g., "EXC-024")
      - An asset class name (e.g., "Excavator")
      - One or more 512D reference embeddings (multiple photos = better matching)

    On query, every stored asset is compared against the incoming
    embedding using cosine similarity, and a structured match result
    is returned with an identity status (CONFIRMED / PROBABLE /
    AMBIGUOUS / UNKNOWN).
    """

    def __init__(self, config_path: str = "config/reid_config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        # Thresholds (calibrated from validation data — see reid_config.yaml)
        thresholds = self.config.get("thresholds", {})
        self.t_high   = thresholds.get("t_high",   0.85)
        self.t_low    = thresholds.get("t_low",    0.65)
        self.t_margin = thresholds.get("t_margin", 0.15)
        self.t_min    = thresholds.get("t_min",    0.40)

        self.max_refs = self.config.get("max_references_per_asset", 10)
        self.aggregation = self.config.get("embedding_aggregation", "mean")
        self.max_candidates = self.config.get("max_candidates", 5)

        # Storage directory
        self.db_dir = Path("data/reference_db")
        self.db_dir.mkdir(parents=True, exist_ok=True)

        # In-memory store: {asset_id: {"class_name": str, "embeddings": np.ndarray (N, 512)}}
        self._store: dict = {}
        self.load()

    # ------------------------------------------------------------------
    # Write Operations
    # ------------------------------------------------------------------

    def add_reference(
        self,
        asset_id: str,
        class_name: str,
        embedding: np.ndarray,
        auto_save: bool = True
    ) -> bool:
        """
        Add a reference embedding for a known asset.

        If the asset already exists, the new embedding is appended
        (up to max_references_per_asset). Older embeddings are dropped
        if the cap is exceeded.

        Args:
            asset_id:   Unique identifier (e.g., "EXC-024").
            class_name: Asset class (e.g., "Excavator").
            embedding:  512D float32 L2-normalised numpy array.
            auto_save:  If True, immediately persist to disk.

        Returns:
            True on success, False if embedding is invalid.
        """
        if embedding is None or embedding.shape != (512,):
            print(f"[ReferenceStore] Invalid embedding for '{asset_id}' — skipping.")
            return False

        embedding = embedding.astype(np.float32)

        if asset_id in self._store:
            existing = self._store[asset_id]["embeddings"]
            updated = np.vstack([existing, embedding])
            # Keep only the most recent max_refs embeddings
            if len(updated) > self.max_refs:
                updated = updated[-self.max_refs:]
            self._store[asset_id]["embeddings"] = updated
            self._store[asset_id]["class_name"] = class_name
        else:
            self._store[asset_id] = {
                "class_name": class_name,
                "embeddings": embedding.reshape(1, 512),
                "added_at": datetime.now(timezone.utc).isoformat()
            }

        if auto_save:
            self._save_asset(asset_id)

        return True

    def remove_asset(self, asset_id: str) -> bool:
        """
        Remove an asset and its embeddings from the store.

        Returns True if the asset existed and was removed.
        """
        if asset_id not in self._store:
            return False
        del self._store[asset_id]
        asset_file = self.db_dir / f"{asset_id}.npz"
        if asset_file.exists():
            asset_file.unlink()
        return True

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(self, embedding: np.ndarray, class_filter: str | None = None) -> dict:
        """
        Find the closest matching asset in the store.

        Args:
            embedding:    512D float32 L2-normalised numpy array from ReIDEngine.
            class_filter: If provided, only compare against assets of this class.
                          Prevents cross-class false matches (e.g., generator vs excavator).

        Returns:
            Match result dict:
            {
                "asset_id":        str | None,
                "class_name":      str | None,
                "similarity_score": float,
                "identity_status": "CONFIRMED" | "PROBABLE" | "AMBIGUOUS" | "UNKNOWN",
                "margin":          float,        # gap between top-1 and top-2 scores
                "candidates":      list of dicts # top-N matches
            }
        """
        if not self._store:
            return self._no_match_result("UNKNOWN", "Reference database is empty.")

        if embedding is None or embedding.shape != (512,):
            return self._no_match_result("UNKNOWN", "Invalid query embedding.")

        # Build candidate list
        candidates = []
        for asset_id, data in self._store.items():
            if class_filter and data["class_name"] != class_filter:
                continue

            representative = self._aggregate(data["embeddings"])
            score = float(self.cosine_similarity(embedding, representative))
            candidates.append({
                "asset_id":   asset_id,
                "class_name": data["class_name"],
                "score":      round(score, 4)
            })

        if not candidates:
            return self._no_match_result("UNKNOWN", "No candidates after class filter.")

        # Sort by score descending
        candidates.sort(key=lambda x: x["score"], reverse=True)
        top = candidates[0]
        top_score = top["score"]
        second_score = candidates[1]["score"] if len(candidates) > 1 else 0.0
        margin = round(top_score - second_score, 4)

        # Determine identity status
        status = self._decide_status(top_score, margin)

        return {
            "asset_id":         top["asset_id"] if status != "UNKNOWN" else None,
            "class_name":       top["class_name"] if status != "UNKNOWN" else None,
            "similarity_score": top_score,
            "identity_status":  status,
            "margin":           margin,
            "candidates":       candidates[:self.max_candidates]
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self):
        """Persist all assets in the in-memory store to disk."""
        for asset_id in self._store:
            self._save_asset(asset_id)

    def load(self):
        """Load all .npz files from the database directory into memory."""
        self._store = {}
        npz_files = list(self.db_dir.glob("*.npz"))
        for f in npz_files:
            try:
                data = np.load(f, allow_pickle=True)
                asset_id = f.stem
                self._store[asset_id] = {
                    "class_name": str(data["class_name"]),
                    "embeddings": data["embeddings"],
                    "added_at":   str(data.get("added_at", "unknown"))
                }
            except Exception as e:
                print(f"[ReferenceStore] Failed to load '{f.name}': {e}")

        if self._store:
            print(f"[ReferenceStore] Loaded {len(self._store)} asset(s) from '{self.db_dir}'.")
        else:
            print(f"[ReferenceStore] Empty database at '{self.db_dir}'. Ready for registration.")

    def list_assets(self) -> list:
        """
        Return a summary list of all registered assets.

        Returns:
            List of dicts: [{"asset_id", "class_name", "num_references"}, ...]
        """
        return [
            {
                "asset_id":       aid,
                "class_name":     data["class_name"],
                "num_references": len(data["embeddings"])
            }
            for aid, data in self._store.items()
        ]

    @property
    def asset_count(self) -> int:
        """Number of registered assets in the store."""
        return len(self._store)

    # ------------------------------------------------------------------
    # Core math
    # ------------------------------------------------------------------

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """
        Compute cosine similarity between two L2-normalised vectors.

        Because both vectors are already L2-normalised (norm=1.0),
        cosine similarity reduces to a simple dot product.

        Returns a float in [-1.0, 1.0]. Higher = more similar.
        """
        return float(np.dot(a, b))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _save_asset(self, asset_id: str):
        """Persist a single asset's data to a .npz file."""
        data = self._store[asset_id]
        out_path = self.db_dir / f"{asset_id}.npz"
        np.savez(
            out_path,
            class_name=np.array(data["class_name"]),
            embeddings=data["embeddings"],
            added_at=np.array(data.get("added_at", ""))
        )

    def _aggregate(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Combine multiple reference embeddings into a single representative vector.

        Uses mean aggregation by default (configurable in reid_config.yaml).
        The result is L2-normalised so cosine similarity remains valid.
        """
        if self.aggregation == "mean":
            agg = embeddings.mean(axis=0)
        elif self.aggregation == "max":
            agg = embeddings.max(axis=0)
        else:
            agg = embeddings.mean(axis=0)

        norm = np.linalg.norm(agg)
        if norm < 1e-8:
            return agg
        return agg / norm

    def _decide_status(self, score: float, margin: float) -> str:
        """
        Determine identity status from the top similarity score and margin.

          CONFIRMED  — high score AND clear separation from second candidate
          PROBABLE   — reasonable score but below CONFIRMED threshold
          AMBIGUOUS  — score is OK but margin is too small (two similar candidates)
          UNKNOWN    — score is below the minimum threshold
        """
        if score < self.t_min:
            return "UNKNOWN"
        if score >= self.t_high and margin >= self.t_margin:
            return "CONFIRMED"
        if score >= self.t_low:
            if margin < self.t_margin:
                return "AMBIGUOUS"
            return "PROBABLE"
        return "UNKNOWN"

    @staticmethod
    def _no_match_result(status: str, reason: str = "") -> dict:
        return {
            "asset_id":         None,
            "class_name":       None,
            "similarity_score": 0.0,
            "identity_status":  status,
            "margin":           0.0,
            "candidates":       [],
            "reason":           reason
        }
