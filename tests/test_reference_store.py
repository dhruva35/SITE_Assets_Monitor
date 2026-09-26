"""
Tests for src/reference_store.py
Spec: PER-REID-006 → 010

Tests the full lifecycle of the ReferenceStore:
add → save → load → query → remove
All tests use a temporary directory — nothing touches data/reference_db/.
"""

import numpy as np
import pytest
from src.reference_store import ReferenceStore


# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------

def make_store(tmp_path):
    """Create a ReferenceStore with a temp config and temp db directory."""
    config = tmp_path / "reid_config.yaml"
    config.write_text(
        "model_path: 'models/reid/reid_backbone_best.onnx'\n"
        "embedding_dim: 512\n"
        "thresholds:\n"
        "  t_high: 0.85\n"
        "  t_low: 0.65\n"
        "  t_margin: 0.15\n"
        "  t_min: 0.40\n"
        "max_references_per_asset: 10\n"
        "embedding_aggregation: mean\n"
        "max_candidates: 5\n"
    )
    store = ReferenceStore(config_path=str(config))
    # Override db_dir to use tmp_path so we don't pollute the real DB
    store.db_dir = tmp_path / "reference_db"
    store.db_dir.mkdir(exist_ok=True)
    store._store = {}
    return store


def unit_vector(seed=0) -> np.ndarray:
    """Return a reproducible L2-normalised 512D float32 vector."""
    rng = np.random.default_rng(seed)
    v = rng.random(512).astype(np.float32)
    return v / np.linalg.norm(v)


# ---------------------------------------------------------------------------
# 1. Add & basic retrieval
# ---------------------------------------------------------------------------

class TestAddReference:

    def test_add_single_reference(self, tmp_path):
        store = make_store(tmp_path)
        emb = unit_vector(0)
        result = store.add_reference("EXC-001", "Excavator", emb, auto_save=False)
        assert result is True
        assert store.asset_count == 1

    def test_add_multiple_assets(self, tmp_path):
        store = make_store(tmp_path)
        for i in range(5):
            store.add_reference(f"ASSET-{i:03d}", "Dump truck", unit_vector(i), auto_save=False)
        assert store.asset_count == 5

    def test_add_multiple_refs_same_asset(self, tmp_path):
        store = make_store(tmp_path)
        for i in range(4):
            store.add_reference("EXC-001", "Excavator", unit_vector(i), auto_save=False)
        assert store._store["EXC-001"]["embeddings"].shape == (4, 512)

    def test_max_references_cap_enforced(self, tmp_path):
        store = make_store(tmp_path)
        store.max_refs = 3
        for i in range(10):
            store.add_reference("EXC-001", "Excavator", unit_vector(i), auto_save=False)
        assert store._store["EXC-001"]["embeddings"].shape[0] == 3

    def test_invalid_embedding_rejected(self, tmp_path):
        store = make_store(tmp_path)
        bad_emb = np.ones(128, dtype=np.float32)  # Wrong shape
        result = store.add_reference("EXC-001", "Excavator", bad_emb, auto_save=False)
        assert result is False
        assert store.asset_count == 0

    def test_none_embedding_rejected(self, tmp_path):
        store = make_store(tmp_path)
        result = store.add_reference("EXC-001", "Excavator", None, auto_save=False)
        assert result is False


# ---------------------------------------------------------------------------
# 2. Cosine similarity math
# ---------------------------------------------------------------------------

class TestCosineSimilarity:

    def test_identical_vectors_score_is_one(self):
        v = unit_vector(42)
        score = ReferenceStore.cosine_similarity(v, v)
        assert abs(score - 1.0) < 1e-5

    def test_orthogonal_vectors_score_is_zero(self):
        a = np.zeros(512, dtype=np.float32)
        b = np.zeros(512, dtype=np.float32)
        a[0] = 1.0
        b[1] = 1.0
        score = ReferenceStore.cosine_similarity(a, b)
        assert abs(score) < 1e-5

    def test_opposite_vectors_score_is_negative_one(self):
        v = unit_vector(1)
        score = ReferenceStore.cosine_similarity(v, -v)
        assert abs(score + 1.0) < 1e-5

    def test_score_is_symmetric(self):
        a = unit_vector(10)
        b = unit_vector(20)
        assert abs(
            ReferenceStore.cosine_similarity(a, b) -
            ReferenceStore.cosine_similarity(b, a)
        ) < 1e-6


# ---------------------------------------------------------------------------
# 3. Query & identity status
# ---------------------------------------------------------------------------

class TestQuery:

    def test_empty_store_returns_unknown(self, tmp_path):
        store = make_store(tmp_path)
        result = store.query(unit_vector(0))
        assert result["identity_status"] == "UNKNOWN"
        assert result["asset_id"] is None

    def test_confirmed_match(self, tmp_path):
        store = make_store(tmp_path)
        ref = unit_vector(0)
        store.add_reference("EXC-001", "Excavator", ref, auto_save=False)
        # Add a very different second asset to ensure large margin
        store.add_reference("GEN-001", "Generator", unit_vector(99), auto_save=False)
        result = store.query(ref)
        assert result["identity_status"] == "CONFIRMED"
        assert result["asset_id"] == "EXC-001"
        assert result["similarity_score"] > 0.85

    def test_unknown_when_score_below_minimum(self, tmp_path):
        store = make_store(tmp_path)
        store.t_min = 0.99    # set an impossibly high minimum
        store.add_reference("EXC-001", "Excavator", unit_vector(0), auto_save=False)
        # Query with a very different vector
        result = store.query(unit_vector(99))
        assert result["identity_status"] == "UNKNOWN"
        assert result["asset_id"] is None

    def test_class_filter_excludes_wrong_class(self, tmp_path):
        store = make_store(tmp_path)
        ref = unit_vector(0)
        store.add_reference("EXC-001", "Excavator", ref, auto_save=False)
        # Query with the exact same vector but filter for a different class
        result = store.query(ref, class_filter="Generator")
        assert result["identity_status"] == "UNKNOWN"

    def test_candidates_list_is_populated(self, tmp_path):
        store = make_store(tmp_path)
        for i in range(3):
            store.add_reference(f"A-{i}", "Excavator", unit_vector(i), auto_save=False)
        result = store.query(unit_vector(0))
        assert len(result["candidates"]) <= store.max_candidates
        assert all("asset_id" in c and "score" in c for c in result["candidates"])

    def test_candidates_sorted_descending(self, tmp_path):
        store = make_store(tmp_path)
        for i in range(5):
            store.add_reference(f"A-{i}", "Excavator", unit_vector(i), auto_save=False)
        result = store.query(unit_vector(0))
        scores = [c["score"] for c in result["candidates"]]
        assert scores == sorted(scores, reverse=True)

    def test_invalid_query_embedding_returns_unknown(self, tmp_path):
        store = make_store(tmp_path)
        store.add_reference("EXC-001", "Excavator", unit_vector(0), auto_save=False)
        result = store.query(None)
        assert result["identity_status"] == "UNKNOWN"

    def test_margin_is_computed(self, tmp_path):
        store = make_store(tmp_path)
        store.add_reference("EXC-001", "Excavator", unit_vector(0), auto_save=False)
        store.add_reference("GEN-001", "Generator", unit_vector(99), auto_save=False)
        result = store.query(unit_vector(0))
        assert "margin" in result
        assert result["margin"] >= 0.0


# ---------------------------------------------------------------------------
# 4. Persistence (save → load)
# ---------------------------------------------------------------------------

class TestPersistence:

    def test_save_creates_npz_file(self, tmp_path):
        store = make_store(tmp_path)
        store.add_reference("EXC-001", "Excavator", unit_vector(0))
        npz = store.db_dir / "EXC-001.npz"
        assert npz.exists()

    def test_load_restores_saved_asset(self, tmp_path):
        store = make_store(tmp_path)
        store.add_reference("EXC-001", "Excavator", unit_vector(0))

        # Create a fresh store pointing at the same directory
        store2 = make_store(tmp_path)
        store2.db_dir = store.db_dir
        store2.load()

        assert store2.asset_count == 1
        assert "EXC-001" in store2._store

    def test_query_works_after_reload(self, tmp_path):
        ref = unit_vector(0)
        store = make_store(tmp_path)
        store.add_reference("EXC-001", "Excavator", ref)

        store2 = make_store(tmp_path)
        store2.db_dir = store.db_dir
        store2.load()

        result = store2.query(ref)
        assert result["asset_id"] == "EXC-001"

    def test_multiple_assets_all_reload(self, tmp_path):
        store = make_store(tmp_path)
        ids = ["EXC-001", "GEN-002", "TRUCK-003"]
        for i, aid in enumerate(ids):
            store.add_reference(aid, "Equipment", unit_vector(i))

        store2 = make_store(tmp_path)
        store2.db_dir = store.db_dir
        store2.load()
        assert store2.asset_count == 3


# ---------------------------------------------------------------------------
# 5. Remove asset
# ---------------------------------------------------------------------------

class TestRemoveAsset:

    def test_remove_existing_asset(self, tmp_path):
        store = make_store(tmp_path)
        store.add_reference("EXC-001", "Excavator", unit_vector(0))
        result = store.remove_asset("EXC-001")
        assert result is True
        assert store.asset_count == 0

    def test_remove_deletes_npz_file(self, tmp_path):
        store = make_store(tmp_path)
        store.add_reference("EXC-001", "Excavator", unit_vector(0))
        store.remove_asset("EXC-001")
        assert not (store.db_dir / "EXC-001.npz").exists()

    def test_remove_nonexistent_asset_returns_false(self, tmp_path):
        store = make_store(tmp_path)
        result = store.remove_asset("DOES-NOT-EXIST")
        assert result is False


# ---------------------------------------------------------------------------
# 6. list_assets
# ---------------------------------------------------------------------------

class TestListAssets:

    def test_list_assets_empty(self, tmp_path):
        store = make_store(tmp_path)
        assert store.list_assets() == []

    def test_list_assets_returns_all(self, tmp_path):
        store = make_store(tmp_path)
        store.add_reference("A-001", "Excavator", unit_vector(0), auto_save=False)
        store.add_reference("A-002", "Dump truck", unit_vector(1), auto_save=False)
        assets = store.list_assets()
        assert len(assets) == 2
        ids = {a["asset_id"] for a in assets}
        assert ids == {"A-001", "A-002"}

    def test_list_assets_shows_reference_count(self, tmp_path):
        store = make_store(tmp_path)
        store.add_reference("A-001", "Excavator", unit_vector(0), auto_save=False)
        store.add_reference("A-001", "Excavator", unit_vector(1), auto_save=False)
        assets = store.list_assets()
        assert assets[0]["num_references"] == 2
