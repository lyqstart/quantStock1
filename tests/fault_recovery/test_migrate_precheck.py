"""Tests for migrate-disk precheck script (DD-CORE-019, REQ-CORE-029)."""

import os

import pytest


class TestMigratePrecheck:
    def test_precheck_script_exists(self):
        assert os.path.exists("scripts/db_migrate_disk/precheck.sh")

    def test_migrate_script_exists(self):
        assert os.path.exists("scripts/db_migrate_disk/migrate.sh")

    def test_rollback_script_exists(self):
        assert os.path.exists("scripts/db_migrate_disk/rollback.sh")

    def test_precheck_is_executable_content(self):
        with open("scripts/db_migrate_disk/precheck.sh", encoding='utf-8') as f:
            content = f.read()
        assert len(content) > 100  # non-trivial script

    def test_migrate_has_dry_run_or_waiting_marker(self):
        with open("scripts/db_migrate_disk/migrate.sh", encoding='utf-8') as f:
            content = f.read()
        # Script should mention WAITING_USER_EXECUTION or dry-run
        assert "WAITING_USER_EXECUTION" in content or "dry" in content.lower()
