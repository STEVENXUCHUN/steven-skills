#!/usr/bin/env python3
"""Freeze a user-approved render plan and bind it to approved content."""
import argparse, datetime
from common import canonical_sha256, dump_json, load_json
from validate_render_plan import validate_plan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True); ap.add_argument("--approved", required=True)
    ap.add_argument("--output", required=True); ap.add_argument("--source-ref", required=True)
    args = ap.parse_args()
    plan, approved = load_json(args.plan), load_json(args.approved)
    plan.pop("approval", None)
    errors, warnings = validate_plan(plan, approved, require_approval=False)
    if errors:
        for item in errors: print("ERROR:", item)
        raise SystemExit("render-plan draft validation failed")
    plan["approval"] = {
        "approved": True,
        "approved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "approved_by": "user", "source_ref": args.source_ref,
        "plan_sha256": canonical_sha256(plan)
    }
    errors, warnings = validate_plan(plan, approved, require_approval=True)
    if errors:
        for item in errors: print("ERROR:", item)
        raise SystemExit("approved render-plan validation failed")
    dump_json(plan, args.output)
    print(f"wrote approved render plan: {args.output}")

if __name__ == "__main__": main()
