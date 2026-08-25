import json

import pytest

from app.model_output import normalise_model_output


@pytest.mark.parametrize(
    ("raw", "expected", "applied"),
    [
        ('{"criteria": []}', '{"criteria": []}', False),
        ('```json\n{"criteria": []}\n```', '{"criteria": []}', True),
        ('```JSON\n{"criteria": []}\n```', '{"criteria": []}', True),
        ('```\n{"criteria": []}\n```', '{"criteria": []}', True),
        ('  ```json\n  {"criteria": []}  \n```  ', '{"criteria": []}', True),
        ('```json\n{"text": "keep ``` inside"}\n```', '{"text": "keep ``` inside"}', True),
    ],
)
def test_normalise_model_output(raw, expected, applied):
    actual, was_applied = normalise_model_output(raw)
    assert actual == expected
    assert was_applied is applied
    assert json.loads(actual)


@pytest.mark.parametrize(
    ("raw", "fence_is_removed"),
    [
        ('{"criteria": [}', False),
        ('prefix ```json\n{"criteria": []}\n```', False),
        ('```json\n{"criteria": []}\n``` suffix', False),
        ('```json\n{"criteria": [}\n```', True),
    ],
)
def test_malformed_or_non_outer_fence_is_not_repaired(raw, fence_is_removed):
    normalised, applied = normalise_model_output(raw)
    assert applied is fence_is_removed
    with pytest.raises(json.JSONDecodeError):
        json.loads(normalised)
