"""Tests for server-test environment isolation (DD-CORE-018, REQ-CORE-031)."""

import os

import pytest


class TestServerTestIsolation:
    def test_compose_test_uses_different_project(self):
        import yaml
        with open("compose.test.yml") as f:
            config = yaml.safe_load(f)
        assert config.get("name") == "quantstock1-test"

    def test_compose_test_uses_different_db_name(self):
        import yaml
        with open("compose.test.yml") as f:
            config = yaml.safe_load(f)
        env = config.get("services", {}).get("db", {}).get("environment", {})
        assert env.get("POSTGRES_DB") != "quantstock1"

    def test_compose_test_uses_isolated_volume(self):
        import yaml
        with open("compose.test.yml") as f:
            config = yaml.safe_load(f)
        volumes = config.get("volumes", {})
        assert "quantstock1_test_pgdata" in volumes

    def test_compose_test_uses_timescaledb_image(self):
        import yaml
        with open("compose.test.yml") as f:
            config = yaml.safe_load(f)
        image = config.get("services", {}).get("db", {}).get("image", "")
        assert "timescale" in image.lower()
