"""Load the small YAML subset this repo ships, plus JSON.

Supported YAML: comments, `key: value` scalars, and `key:` followed by
`- item` lists. No nested maps. Enough for rules and board lists, and it
keeps a clone on the Python standard library.
"""

import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_simple_yaml(path):
    root = {}
    current = None
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith("  - ") or line.startswith("- "):
            if current is None:
                raise ValueError(f"List item outside a key in {path}: {raw}")
            item = line.split("-", 1)[1].strip()
            if item:
                root[current].append(item)
            continue
        if ":" not in line:
            raise ValueError(f"Cannot parse {path}: {raw}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value in ("", "[]"):
            root[key] = []
            current = key if value == "" else None
        else:
            root[key] = int(value) if value.isdigit() else value
            current = None
    return root
