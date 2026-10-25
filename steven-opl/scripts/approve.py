#!/usr/bin/env python3
"""Freeze a semantically valid content draft after explicit user approval."""
import argparse, datetime, subprocess, sys
from pathlib import Path
from common import canonical_sha256, dump_json, load_json
from validate_data import validate_draft


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--draft", required=True); ap.add_argument("--output", required=True)
    ap.add_argument("--source-ref", required=True, help="Message ID containing explicit approval")
    args = ap.parse_args()
    checker = Path(__file__).with_name("validate_data.py")
    if subprocess.run([sys.executable, str(checker), args.draft]).returncode:
        raise SystemExit("draft validation failed")
    data = load_json(args.draft); data.pop("approval", None)
    data["approval"] = {
        "approved": True, "approved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "approved_by": "user", "source_ref": args.source_ref, "draft_sha256": canonical_sha256(data)
    }
    errors, warnings = [], []
    validate_draft(data, errors, warnings, approved=True)
    if errors:
        for item in errors: print("ERROR:", item)
        raise SystemExit("draft cannot be approved until semantic blockers are resolved")
    dump_json(data, args.output); print(f"wrote frozen content approval: {args.output}")

if __name__ == "__main__": main()
