"""Tests for the run-identity capture helper."""

from __future__ import annotations

import json

from materials_event_modeling.run_identity import run_identity


def test_run_identity_captures_code_and_environment() -> None:
    identity = run_identity()
    # Git commit: 40-hex string in a repo checkout (None only outside a repo).
    assert identity["git_commit"] is None or (
        len(identity["git_commit"]) == 40
        and all(c in "0123456789abcdef" for c in identity["git_commit"])
    )
    assert isinstance(identity["argv"], list) and identity["argv"]
    assert identity["python"]
    assert "numpy" in identity["packages"]
    assert identity["captured_at"]
    # Must be manifest-writable as-is.
    json.dumps(identity)


def test_run_identity_extra_fields_merge() -> None:
    identity = run_identity(extra={"seed": 17})
    assert identity["seed"] == 17
