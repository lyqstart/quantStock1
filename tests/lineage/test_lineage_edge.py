"""Tests for lineage_edge write and recursive traverse (DD-CORE-011)."""

import uuid

import pytest

from app.lineage.service import (
    EDGE_TYPE_DERIVED_FROM,
    EDGE_TYPE_QUALIFIED_BY,
    traverse_lineage,
    write_edge,
)
from tests.conftest import skip_no_pg


class TestWriteEdge:
    def test_write_edge_function_exists(self):
        assert callable(write_edge)

    def test_edge_type_constants(self):
        assert EDGE_TYPE_DERIVED_FROM == "DERIVED_FROM"
        assert EDGE_TYPE_QUALIFIED_BY == "QUALIFIED_BY"


class TestTraverseLineage:
    def test_traverse_function_exists(self):
        assert callable(traverse_lineage)

    def test_invalid_direction_raises(self):
        import pytest
        with pytest.raises(ValueError, match="direction"):
            traverse_lineage(
                session=None,
                start_type="CLEAN_BATCH",
                start_id=uuid.uuid4(),
                direction="sideways",
            )

    def test_zero_depth_raises(self):
        with pytest.raises(ValueError, match="max_depth"):
            traverse_lineage(
                session=None,
                start_type="CLEAN_BATCH",
                start_id=uuid.uuid4(),
                max_depth=0,
            )


@skip_no_pg
class TestLineageEdgeModel:
    def test_lineage_edge_model_exists(self):
        from app.storage.models.lineage import LineageEdge
        assert hasattr(LineageEdge, "edge_type")
        assert hasattr(LineageEdge, "source_type")
        assert hasattr(LineageEdge, "target_type")
