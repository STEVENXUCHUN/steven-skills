#!/usr/bin/env python3
"""Build a reviewable render-plan draft from approved OPL content."""
import argparse, datetime, subprocess, sys
from pathlib import Path
from common import canonical_sha256, dump_json, load_json

CATEGORY_MAP = {
    "fault_judgement": "问题",
    "error_prevention": "基础知识",
    "repair_tip": "基础知识",
    "assembly_note": "基础知识",
    "improvement_case": "改善案例",
}


def fact_value(obj):
    value = (obj or {}).get("value")
    return "" if value is None else str(value).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--approved", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--plan-id", required=True)
    args = ap.parse_args()
    checker = Path(__file__).with_name("validate_data.py")
    if subprocess.run([sys.executable, str(checker), args.approved]).returncode:
        raise SystemExit("approved content validation failed")
    data = load_json(args.approved)
    rows = []
    images_by_step = {}
    for image in data.get("images", []):
        if image.get("included") and image.get("step_id"):
            images_by_step.setdefault(image["step_id"], []).append(image["image_id"])
    for i, step in enumerate(sorted(data.get("steps", []), key=lambda x: x.get("order", 0)), 1):
        text = fact_value(step.get("instruction"))
        check = fact_value(step.get("check"))
        if check: text += ("\n检查：" if text else "检查：") + check
        row_images = images_by_step.get(step.get("step_id"), [])
        rows.append({
            "row_id": f"ROW-{i:03d}", "title": f"要点{i}", "text": text or "待整理",
            "image_ids": row_images,
            "content_refs": [step.get("step_id")],
            "image_side": ("left" if i % 2 else "right") if row_images else "full_width"
        })
    if not rows:
        candidates = [
            ("问题或目标", "problem_or_goal"), ("关键要点", "key_point"),
            ("易错点", "mistakes"), ("安全要求", "safety"), ("验收方法", "acceptance")
        ]
        for label, key in candidates:
            value = fact_value(data.get("content", {}).get(key))
            if value:
                i = len(rows) + 1
                rows.append({"row_id": f"ROW-{i:03d}", "title": label, "text": value,
                             "image_ids": [], "content_refs": [f"content.{key}"],
                             "image_side": "full_width"})
    if not 1 <= len(rows) <= 6:
        raise SystemExit("render plan requires 1-6 rows; split the lesson or consolidate one teaching point")
    plan = {
        "schema_version": "1.0", "task_id": data["task_id"], "plan_id": args.plan_id,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "approved_sha256": canonical_sha256(data),
        "template_selection": {"template_id": "steven-opl-standard", "template_version": "1.1.0"},
        "rows": rows
    }
    dump_json(plan, args.output)
    print(f"wrote render-plan draft: {args.output}; rows={len(rows)}; category={CATEGORY_MAP[data['lesson_type']]}")

if __name__ == "__main__": main()
