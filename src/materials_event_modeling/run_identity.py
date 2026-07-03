"""Capture code/run identity for result manifests.

Every result manifest should record which code produced it. Call ``run_identity()``
when building a report and store the dict under a ``run_identity`` key. Records the
git commit (plus a dirty flag for tracked-file modifications), the exact command line,
interpreter/platform, and the versions of the numerical packages that determine results.
"""

from __future__ import annotations

import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RESULT_PACKAGES = ("numpy", "scipy", "sklearn", "pandas", "torch")


def _git(*args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), *args],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def run_identity(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a JSON-serializable record of the code and environment behind a run."""
    commit = _git("rev-parse", "HEAD")
    status = _git("status", "--porcelain", "--untracked-files=no")
    packages: dict[str, str] = {}
    for name in _RESULT_PACKAGES:
        module = sys.modules.get(name)
        if module is None:
            try:
                module = __import__(name)
            except ImportError:
                continue
        version = getattr(module, "__version__", None)
        if version:
            packages[name] = str(version)
    identity: dict[str, Any] = {
        "git_commit": commit,
        "git_dirty": bool(status) if status is not None else None,
        "argv": list(sys.argv),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": packages,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        identity.update(extra)
    return identity
