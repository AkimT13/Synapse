from __future__ import annotations

import tomllib
from pathlib import Path


def test_pyproject_exports_cli_runtime_packages() -> None:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    packages = set(data["tool"]["setuptools"]["packages"])

    assert "synapse_cli" in packages
    assert "retrieval" in packages
    assert "agents" in packages
