from app.governance.tasks import MAPPING_VERSION, NORMALIZATION_VERSION, QUALITY_RULE_VERSION


def test_p4_v1_rule_versions_are_explicit() -> None:
    assert MAPPING_VERSION == "mapping-v1"
    assert NORMALIZATION_VERSION == "normalization-v2"
    assert QUALITY_RULE_VERSION == "quality-v2"
