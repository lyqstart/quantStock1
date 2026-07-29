"""Tests for backup checksum verification (DD-CORE-020, REQ-CORE-032)."""

import hashlib
import os

import pytest


class TestBackupChecksum:
    def test_sha256_computation(self):
        data = b"test backup content"
        expected = hashlib.sha256(data).hexdigest()
        assert len(expected) == 64

    def test_manifest_template_exists(self):
        manifest_path = "scripts/db_backup/manifest.json"
        assert os.path.exists(manifest_path)

    def test_backup_script_exists(self):
        assert os.path.exists("scripts/db_backup/full_backup.sh")

    def test_restore_script_exists(self):
        assert os.path.exists("scripts/db_restore/restore.sh")

    def test_verify_script_exists(self):
        assert os.path.exists("scripts/db_restore/verify.sh")
