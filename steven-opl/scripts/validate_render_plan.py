#!/usr/bin/env python3
"""Validate render plan, content binding, image hashes and user approval."""
import argparse, re, sys
from pathlib import Path
from common import canonical_sha256, file_sha256, load_json


def valid_content_refs(approved):
    refs = {f"content.{k}" for k in approved.get("content", {})}
    refs.update(x.get("step_id") for x in approved.get("steps", []) if x.get("step_id"))
    return refs


def validate_plan(plan, approved, require_approval=True):
    errors, warnings = [], []
    for key in ("schema_version", "task_id", "plan_id", "approved_sha256", "template_selection", "rows"):
        if key not in plan: errors.append(f"missing {key}")
    if plan.get("task_id") != approved.get("task_id"): errors.append("task_id does not match approved content")
    if plan.get("approved_sha256") != canonical_sha256(approved): errors.append("approved content hash mismatch")
    selection = plan.get("template_selection", {})
    if selection != {"template_id": "steven-opl-standard", "template_version": "1.1.0"}:
        errors.append("unsupported template selection")
    rows = plan.get("rows", [])
    if not 1 <= len(rows) <= 6: errors.append("render plan must contain 1-6 rows")
    row_ids = [x.get("row_id") for x in rows]
    if len(row_ids) != len(set(row_ids)): errors.append("duplicate row_id")
    images = {x.get("image_id"): x for x in approved.get("images", [])}
    valid_refs = valid_content_refs(approved)
    used = set()
    for i, row in enumerate(rows, 1):
        if not str(row.get("title") or "").strip(): errors.append(f"row {i}: missing title")
        if not str(row.get("text") or "").strip(): errors.append(f"row {i}: missing text")
        ids = row.get("image_ids", [])
        if not isinstance(ids, list) or len(ids) > 4: errors.append(f"row {i}: image_ids must contain 0-4 items"); ids = []
        if len(ids) != len(set(ids)): errors.append(f"row {i}: duplicate image id")
        expected_side = "left" if i % 2 else "right"
        expected_side = expected_side if ids else "full_width"
        if row.get("image_side") != expected_side: errors.append(f"row {i}: image_side must be {expected_side}")
        refs = row.get("content_refs", [])
        if not refs: errors.append(f"row {i}: content_refs is empty")
        for ref in refs:
            if ref not in valid_refs: errors.append(f"row {i}: unknown content_ref {ref}")
        for image_id in ids:
            image = images.get(image_id)
            if not image: errors.append(f"row {i}: unknown image {image_id}"); continue
            if not image.get("included") or not image.get("confirmed"):
                errors.append(f"row {i}: image {image_id} is not approved for use")
            if image_id in used: errors.append(f"image {image_id} is used more than once")
            used.add(image_id)
            path = image.get("path")
            sha = image.get("source_sha256")
            if not path or not Path(path).is_file(): errors.append(f"image {image_id}: file is unavailable")
            elif not re.fullmatch(r"[0-9a-f]{64}", str(sha or "")): errors.append(f"image {image_id}: source_sha256 missing")
            elif file_sha256(path) != sha: errors.append(f"image {image_id}: file hash changed after approval")
    expected_images = {x.get("image_id") for x in approved.get("images", []) if x.get("included")}
    missing = sorted(x for x in expected_images - used if x)
    if missing: errors.append("approved images missing from render plan: " + ", ".join(missing))
    if require_approval:
        approval = plan.get("approval") or {}
        if approval.get("approved") is not True: errors.append("render plan is not explicitly approved")
        base = dict(plan); base.pop("approval", None)
        if approval.get("plan_sha256") != canonical_sha256(base): errors.append("render plan changed after approval")
        if not approval.get("source_ref"): errors.append("render-plan approval source_ref is missing")
    return errors, warnings


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--plan", required=True); ap.add_argument("--approved", required=True)
    ap.add_argument("--draft", action="store_true", help="do not require plan approval")
    args = ap.parse_args(); plan, approved = load_json(args.plan), load_json(args.approved)
    errors, warnings = validate_plan(plan, approved, not args.draft)
    for x in warnings: print("WARNING:", x)
    for x in errors: print("ERROR:", x)
    print(f"errors={len(errors)} warnings={len(warnings)}")
    return 1 if errors else 0

if __name__ == "__main__": raise SystemExit(main())
