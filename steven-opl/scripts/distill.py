#!/usr/bin/env python3
"""Create a non-inferential content draft skeleton from raw.json."""
import argparse, datetime
from pathlib import Path
from common import dump_json, load_json

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = ImageOps = None


def unknown(): return {"value": None, "status": "unknown", "source_refs": []}
def derived(value, ref): return {"value": value, "status": "derived", "source_refs": [ref]}


def image_info(path):
    if not Image or not path or not Path(path).is_file(): return None, None, None
    try:
        with Image.open(path) as src:
            fmt = src.format
            shown = ImageOps.exif_transpose(src)
            return shown.width, shown.height, fmt
    except Exception:
        return None, None, None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--raw", required=True); ap.add_argument("--output", required=True)
    ap.add_argument("--draft-id", required=True); args = ap.parse_args()
    raw = load_json(args.raw)
    source_index = []
    for msg in raw.get("messages", []):
        source_index.append({"source_id": msg.get("message_id"), "type": "message", "path": None, "sha256": None})
    images, order = [], 0
    for asset in raw.get("assets", []):
        aid, mime = asset.get("asset_id"), asset.get("mime_type") or ""
        source_index.append({"source_id": aid, "type": "image" if mime.startswith("image/") else "file",
                             "path": asset.get("path"), "sha256": asset.get("sha256")})
        if mime.startswith("image/"):
            order += 1; width, height, fmt = image_info(asset.get("path"))
            images.append({
                "image_id": f"IMG-{order:03d}", "asset_id": aid, "path": asset.get("path") or "",
                "source_sha256": asset.get("sha256") or "0" * 64,
                "display_width_px": width, "display_height_px": height, "original_format": fmt,
                "send_order": order, "work_order": None, "insert_order": None,
                "user_description": None, "usage": None, "step_id": None, "caption": None,
                "included": False, "confirmed": False, "source_refs": [x for x in (aid, asset.get("source_message_id")) if x],
                "transform_authorization": {"rotate": False, "mirror": False, "crop": False}
            })
    source_index.append({"source_id": "RULE:lesson-type-map-v1", "type": "rule", "path": None, "sha256": None})
    draft = {
        "schema_version": "1.1", "task_id": raw.get("task_id"), "draft_id": args.draft_id,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "lesson_type": "repair_tip",
        "source_index": source_index,
        "scope": {"single_point": False, "topic": unknown(), "split_required": False, "excluded_topics": []},
        "metadata": {k: unknown() for k in ("group", "procedure", "number", "creation_date", "director", "team_leader", "made_by")},
        "content": {k: unknown() for k in ("title", "applicable_to", "prerequisites", "problem_or_goal", "key_point", "mistakes", "safety", "acceptance", "limitations")},
        "steps": [], "images": images,
        "open_items": [{"item_id": "SCOPE-001", "severity": "critical", "status": "open", "question": "本课只讲哪一个点？"}],
        "template_selection": None
    }
    draft["metadata"]["template_category"] = derived("基础知识", "RULE:lesson-type-map-v1")
    dump_json(draft, args.output)
    print(f"wrote content draft skeleton: {args.output}; images={len(images)}")

if __name__ == "__main__": main()
