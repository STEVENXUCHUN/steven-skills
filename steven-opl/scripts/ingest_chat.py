#!/usr/bin/env python3
"""Normalize an explicitly exported chat bundle into raw.json."""
import argparse, datetime, mimetypes
from pathlib import Path
from common import dump_json, file_sha256, load_json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="JSON containing messages")
    ap.add_argument("--output", required=True)
    ap.add_argument("--task-id", required=True)
    args = ap.parse_args()
    src = load_json(args.input)
    messages, assets = [], []
    asset_no = 0
    for i, msg in enumerate(src.get("messages", []), 1):
        mid = str(msg.get("message_id") or msg.get("id") or f"MSG-{i:03d}")
        ids = []
        attached = msg.get("attachments", msg.get("files", [])) or []
        for item in attached:
            asset_no += 1
            aid = f"ASSET-{asset_no:03d}"
            path = str(item.get("path") if isinstance(item, dict) else item)
            p = Path(path)
            ids.append(aid)
            assets.append({
                "asset_id": aid,
                "source_message_id": mid,
                "original_name": p.name,
                "path": path,
                "mime_type": (item.get("mime_type") if isinstance(item, dict) else None) or mimetypes.guess_type(path)[0],
                "sha256": file_sha256(p) if p.is_file() else "0" * 64,
                "missing": not p.is_file()
            })
        messages.append({
            "message_id": mid,
            "role": msg.get("role", "user"),
            "timestamp": msg.get("timestamp"),
            "text": str(msg.get("text", msg.get("content", "")) or ""),
            "asset_ids": ids
        })
    out = {
        "schema_version": "1.0", "task_id": args.task_id,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "messages": messages, "assets": assets
    }
    dump_json(out, args.output)
    print(f"wrote {args.output}: {len(messages)} messages, {len(assets)} assets")

if __name__ == "__main__":
    main()
