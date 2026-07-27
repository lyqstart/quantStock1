from pathlib import Path


def test_database_engine_hides_sql_parameters():
    source = Path("app/storage/db.py").read_text(encoding="utf-8")
    assert "hide_parameters=True" in source
