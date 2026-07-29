"""Tests for restore verification (DD-CORE-020, REQ-CORE-033)."""

import os

import pytest


class TestRestoreVerify:
    def test_restore_readme_exists(self):
        assert os.path.exists("scripts/db_restore/README.md")

    def test_backup_readme_exists(self):
        assert os.path.exists("scripts/db_backup/README.md")

    def test_migrate_readme_exists(self):
        assert os.path.exists("scripts/db_migrate_disk/README.md")

    def test_compose_test_exists(self):
        assert os.path.exists("compose.test.yml")

    def test_env_test_example_exists(self):
        assert os.path.exists(".env.test.example")
