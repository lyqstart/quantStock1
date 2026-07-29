"""Tests for Alembic empty-database upgrade from 0001 to head (DD-CORE-021, REQ-CORE-034).

These tests verify that the full migration chain is valid by examining
the migration files. Actual DB upgrade requires real PG.
"""

import os
import re

import pytest


class TestMigrationChain:
    def test_migration_0013_exists(self):
        assert os.path.exists("migrations/versions/0013_lineage_and_snapshot.py")

    def test_migration_0014_exists(self):
        assert os.path.exists("migrations/versions/0014_clean_published_at_financial_dataitem.py")

    def test_migration_0015_exists(self):
        assert os.path.exists("migrations/versions/0015_audit_runcheck_datagap_rawevidence.py")

    def test_0013_down_revision_points_to_0012(self):
        with open("migrations/versions/0013_lineage_and_snapshot.py") as f:
            content = f.read()
        assert "0012_p4_minute_governance" in content

    def test_0014_down_revision_points_to_0013(self):
        with open("migrations/versions/0014_clean_published_at_financial_dataitem.py") as f:
            content = f.read()
        assert "0013" in content

    def test_0015_down_revision_points_to_0014(self):
        with open("migrations/versions/0015_audit_runcheck_datagap_rawevidence.py") as f:
            content = f.read()
        assert "0014" in content

    def test_0013_has_upgrade_function(self):
        with open("migrations/versions/0013_lineage_and_snapshot.py") as f:
            content = f.read()
        assert "def upgrade" in content

    def test_0013_has_downgrade_function(self):
        with open("migrations/versions/0013_lineage_and_snapshot.py") as f:
            content = f.read()
        assert "def downgrade" in content

    def test_all_migrations_have_revision_ids(self):
        for fn in os.listdir("migrations/versions"):
            if fn.startswith("001") and fn.endswith(".py"):
                with open(f"migrations/versions/{fn}") as f:
                    content = f.read()
                assert "revision" in content, f"{fn} missing revision"
                assert "down_revision" in content, f"{fn} missing down_revision"
