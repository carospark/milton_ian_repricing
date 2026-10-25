"""Resolve sibling-repo paths from config.yaml and fail loudly when a file is missing."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config.yaml"


class MissingInputError(FileNotFoundError):
    """A configured input file does not exist. Nothing is built from a guess."""


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path) as handle:
        return yaml.safe_load(handle)


def resolve_inputs(config: dict | None = None) -> dict[str, Path | None]:
    """Expand {issuance} and {flow} placeholders; return {name: Path or None}."""
    config = config or load_config()
    siblings = {k: str(Path(v).expanduser()) for k, v in config["siblings"].items()}
    out: dict[str, Path | None] = {}
    for name, template in config["inputs"].items():
        out[name] = None if template is None else Path(template.format(**siblings))
    return out


def require(name: str, config: dict | None = None) -> Path:
    """Return the path for one configured input, or raise with the exact missing path."""
    paths = resolve_inputs(config)
    path = paths.get(name)
    if path is None:
        raise MissingInputError(f"input '{name}' is not configured (null in config.yaml)")
    if not path.exists():
        raise MissingInputError(f"input '{name}' not found at {path}")
    return path


def check_all(config: dict | None = None) -> dict[str, str]:
    """Status of every configured input: 'ok', 'missing', or 'unconfigured'."""
    status = {}
    for name, path in resolve_inputs(config).items():
        status[name] = "unconfigured" if path is None else ("ok" if path.exists() else "missing")
    return status


def output_dir(config: dict | None = None) -> Path:
    config = config or load_config()
    out = ROOT / config.get("output_dir", "data/derived")
    out.mkdir(parents=True, exist_ok=True)
    return out


if __name__ == "__main__":
    for name, state in check_all().items():
        print(f"{state:13s} {name}")
