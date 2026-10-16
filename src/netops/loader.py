from __future__ import annotations

import json
from pathlib import Path

import yaml

from netops.model.core import Topology


def _merge(base: dict, overlay: dict) -> dict:
    merged: dict = dict(base)
    for key, value in overlay.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _merge(merged[key], value)
        elif key in merged and isinstance(merged[key], list) and isinstance(value, list):
            merged[key] = merged[key] + value
        else:
            merged[key] = value
    return merged


def load_topology(path: str | Path) -> Topology:
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return Topology.model_validate(data)


def load_network(*paths: str | Path) -> Topology:
    merged: dict = {}
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            merged = _merge(merged, yaml.safe_load(handle) or {})
    return Topology.model_validate(merged)


def load_network_dir(directory: str | Path) -> Topology:
    files = sorted(Path(directory).glob("*.yaml"))
    if not files:
        raise FileNotFoundError(f"no *.yaml files in {directory}")
    return load_network(*files)


def dump_topology(topology: Topology, sort_keys: bool = True) -> str:
    data = json.loads(topology.model_dump_json())
    return yaml.safe_dump(data, sort_keys=sort_keys, default_flow_style=False)