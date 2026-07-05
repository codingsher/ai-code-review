from app.schemas import FindingList
from app.services.llm_review import _parse


def test_parse_plain_json():
    assert _parse('{"findings": []}').findings == []


def test_parse_fenced_json():
    raw = '```json\n{"findings": []}\n```'
    assert _parse(raw).findings == []


def test_schema_validates_finding():
    fl = FindingList.model_validate({"findings": [{
        "title": "t", "description": "d", "severity": "high", "confidence": 0.9,
        "category": "security", "explanation": "e", "suggested_fix": "f",
        "file": "a.py", "line": 3,
    }]})
    assert fl.findings[0].severity.value == "high"


def test_schema_rejects_bad_confidence():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        FindingList.model_validate({"findings": [{
            "title": "t", "description": "d", "severity": "high", "confidence": 2.0,
            "category": "security", "explanation": "e", "suggested_fix": "f",
            "file": "a.py", "line": 3,
        }]})
