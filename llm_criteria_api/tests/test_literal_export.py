from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

from app import frozen_pipeline


def test_active_runtime_function_sources_match_kaggle_manifest():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads(
        (root / "kaggle_frozen_pipeline_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["runtimeSelfParityExactCount"] == 5
    assert manifest["runtimeSelfParityTotal"] == 5
    assert not manifest["functionsNotExported"]

    for name, exported in manifest["functions"].items():
        local_function = getattr(frozen_pipeline, name)
        local_hash = hashlib.sha256(
            inspect.getsource(local_function).encode("utf-8")
        ).hexdigest()
        assert local_hash == exported["sourceHash"], name
