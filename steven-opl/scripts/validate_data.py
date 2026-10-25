#!/usr/bin/env python3
"""Semantic validation for raw, draft and approved Steven OPL JSON."""
import argparse, re, sys
from pathlib import Path
from common import canonical_sha256, file_sha256, load_json, walk_facts

FACT_STATUSES = {"user_confirmed", "user_stated", "assistant_suggested", "derived", "unknown", "conflict"}
CATEGORY_MAP = {"fault_judgement": "问题", "error_prevention": "基础知识", "repair_tip": "基础知识", "assembly_note": "基础知识", "improvement_case": "改善案例"}


def validate_raw(d, errors, warnings):
    for k in ("schema_version", "task_id", "messages", "assets"):
        if k not in d: errors.append(f"missing {k}")
    mids = [m.get("message_id") for m in d.get("messages", [])]
    if len(mids) != len(set(mids)): errors.append("duplicate message_id")
    aids = [a.get("asset_id") for a in d.get("assets", [])]
    if len(aids) != len(set(aids)): errors.append("duplicate asset_id")
    for a in d.get("assets", []):
        if a.get("missing"): warnings.append(f"missing attachment: {a.get('path')}")
        if not re.fullmatch(r"[0-9a-f]{64}", str(a.get("sha256", ""))): errors.append(f"bad sha256: {a.get('asset_id')}")


def validate_draft(d, errors, warnings, approved=False):
    required = ("schema_version", "task_id", "draft_id", "lesson_type", "source_index", "scope", "metadata", "content", "steps", "images", "open_items")
    for k in required:
        if k not in d: errors.append(f"missing {k}")
    if d.get("schema_version") != "1.1": errors.append("schema_version must be 1.1")
    scope = d.get("scope", {})
    if scope.get("single_point") is not True: errors.append("single-point gate not passed")
    if scope.get("split_required") is True: errors.append("scope still requires splitting")
    source_ids = [x.get("source_id") for x in d.get("source_index", [])]
    if len(source_ids) != len(set(source_ids)): errors.append("duplicate source_id")
    source_set = {x for x in source_ids if x}
    step_ids = [x.get("step_id") for x in d.get("steps", [])]
    if len(step_ids) != len(set(step_ids)): errors.append("duplicate step_id")
    image_ids = [x.get("image_id") for x in d.get("images", [])]
    if len(image_ids) != len(set(image_ids)): errors.append("duplicate image_id")
    for path, fact in walk_facts(d):
        status = fact.get("status")
        if status not in FACT_STATUSES: errors.append(f"{path}: invalid status")
        refs = [x for x in fact.get("source_refs", []) if x]
        if status in {"user_confirmed", "user_stated", "derived"} and not refs:
            errors.append(f"{path}: stated or derived value has no source")
        for ref in refs:
            if ref not in source_set: errors.append(f"{path}: unknown source_ref {ref}")
        if approved and status == "conflict": errors.append(f"{path}: unresolved conflict")
        if approved and status == "assistant_suggested": errors.append(f"{path}: suggestion not confirmed")
    category = ((d.get("metadata") or {}).get("template_category") or {}).get("value")
    expected = CATEGORY_MAP.get(d.get("lesson_type"))
    if category != expected: errors.append(f"template category must be {expected} for {d.get('lesson_type')}")
    for img in d.get("images", []):
        refs = [x for x in img.get("source_refs", []) if x]
        for ref in refs:
            if ref not in source_set: errors.append(f"{img.get('image_id')}: unknown source_ref {ref}")
        if img.get("included"):
            iid = img.get("image_id")
            if not img.get("confirmed"): errors.append(f"{iid}: included but unconfirmed")
            if not img.get("usage"): errors.append(f"{iid}: included but no usage")
            if not img.get("caption"): warnings.append(f"{iid}: included but no caption")
            path, sha = img.get("path"), img.get("source_sha256")
            if not path or not Path(path).is_file(): errors.append(f"{iid}: image file unavailable")
            elif not re.fullmatch(r"[0-9a-f]{64}", str(sha or "")): errors.append(f"{iid}: invalid source_sha256")
            elif file_sha256(path) != sha: errors.append(f"{iid}: image hash changed")
    for item in d.get("open_items", []):
        if item.get("severity") == "critical" and item.get("status") not in {"resolved", "accepted_limit"}:
            errors.append(f"critical open item: {item.get('item_id', '?')}")
    if approved:
        for key in ("title", "problem_or_goal", "key_point", "acceptance"):
            value = ((d.get("content") or {}).get(key) or {}).get("value")
            if value is None or not str(value).strip(): errors.append(f"approved content requires content.{key}")
        approval = d.get("approval") or {}
        if approval.get("approved") is not True: errors.append("missing explicit approval")
        base = dict(d); base.pop("approval", None)
        if approval.get("draft_sha256") != canonical_sha256(base): errors.append("approved content changed after approval")
        if not approval.get("source_ref"): errors.append("approval source_ref is missing")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--schema"); ap.add_argument("file"); args = ap.parse_args()
    d = load_json(args.file)
    kind = "approved" if "approval" in d or (args.schema and "approved" in args.schema) else "raw" if "messages" in d else "draft"
    errors, warnings = [], []
    validate_raw(d, errors, warnings) if kind == "raw" else validate_draft(d, errors, warnings, kind == "approved")
    for x in warnings: print("WARNING:", x)
    for x in errors: print("ERROR:", x)
    print(f"kind={kind} errors={len(errors)} warnings={len(warnings)}")
    return 1 if errors else 0

if __name__ == "__main__": raise SystemExit(main())
