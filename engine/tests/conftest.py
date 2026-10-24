import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from mechy.project import Project, init_project

PY = sys.executable


def mechy(*args, cwd=None, env=None):
    """Run the CLI with --json; return (returncode, events, result)."""
    e = {**os.environ, **(env or {})}
    r = subprocess.run([PY, "-m", "mechy.cli", *args, "--json"], capture_output=True, text=True, cwd=cwd, env=e,
                       timeout=600)
    events = [json.loads(l) for l in r.stdout.splitlines() if l.startswith("{")]
    result = next((ev for ev in reversed(events) if ev["type"] == "result"), None)
    return r.returncode, events, result


@pytest.fixture
def project(tmp_path) -> Project:
    return init_project(tmp_path / "proj", example="tennis-catcher")


@pytest.fixture(scope="session")
def built_project(tmp_path_factory) -> Project:
    root = tmp_path_factory.mktemp("built") / "proj"
    proj = init_project(root, example="tennis-catcher")
    code, _, res = mechy("cad", "build", "v1", "--project", str(root))
    assert code == 0 and res["ok"], res
    return proj
