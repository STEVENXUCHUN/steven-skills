#!/usr/bin/env python3
import hashlib, json
from pathlib import Path

FACT_STATUSES = {"user_confirmed", "user_stated", "assistant_suggested", "unknown", "conflict"}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(data, path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(p)


def canonical_bytes(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_sha256(data):
    return hashlib.sha256(canonical_bytes(data)).hexdigest()


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def get_path(data, dotted):
    cur = data
    for part in dotted.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur


def walk_facts(obj, prefix=""):
    if isinstance(obj, dict):
        if set(("value", "status", "source_refs")).issubset(obj):
            yield prefix or "$", obj
        for key, value in obj.items():
            yield from walk_facts(value, f"{prefix}.{key}" if prefix else key)
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            yield from walk_facts(value, f"{prefix}[{i}]")
