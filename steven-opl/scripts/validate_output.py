#!/usr/bin/env python3
"""Validate DOCX content, render trace, image identity and delivery status."""
import argparse, datetime, hashlib, subprocess, sys, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from common import dump_json, file_sha256, get_path, load_json


def docx_payload(path):
    texts, media = [], {}
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if "word/document.xml" not in names: raise ValueError("word/document.xml missing")
        for name in names:
            if name.startswith("word/media/") and not name.endswith("/"):
                media[name]=hashlib.sha256(z.read(name)).hexdigest()
            elif name.startswith("word/") and name.endswith(".xml"):
                try:
                    root=ET.fromstring(z.read(name)); texts.append("".join(x.text or "" for x in root.iter()))
                except ET.ParseError: pass
    return "\n".join(texts), media


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--approved",required=True); ap.add_argument("--plan",required=True)
    ap.add_argument("--contract",required=True); ap.add_argument("--docx",required=True); ap.add_argument("--trace",required=True)
    ap.add_argument("--report",required=True); ap.add_argument("--visual-status",choices=("not_performed","passed","failed"),default="not_performed")
    args=ap.parse_args(); scripts=Path(__file__).parent
    approved,plan,contract,trace=map(load_json,(args.approved,args.plan,args.contract,args.trace))
    errors,warnings,manual=[],[],[]
    if subprocess.run([sys.executable,str(scripts/"validate_data.py"),args.approved],capture_output=True).returncode:
        errors.append("approved content validation failed")
    if subprocess.run([sys.executable,str(scripts/"validate_render_plan.py"),"--plan",args.plan,"--approved",args.approved],capture_output=True).returncode:
        errors.append("approved render plan validation failed")
    try: text,media=docx_payload(args.docx)
    except Exception as exc: text,media="",{}; errors.append(f"invalid docx: {exc}")
    for name,slot in contract.get("text_slots",{}).items():
        try: value=get_path(approved,slot["source"])
        except Exception:
            if slot.get("required"): errors.append(f"missing approved source: {name}")
            continue
        if slot.get("required") and str(value or "") not in text: errors.append(f"required text missing: {name}")
        marker=slot.get("marker")
        if marker and marker in text: errors.append(f"unreplaced marker: {marker}")
    for marker in contract.get("forbidden_markers",["{{","}}"]):
        if marker in text: errors.append(f"forbidden marker remains: {marker}")
    if trace.get("output_sha256")!=file_sha256(args.docx): errors.append("render trace output hash mismatch")
    if trace.get("template_sha256")!=contract.get("template_sha256"): errors.append("render trace template hash mismatch")
    if trace.get("row_count")!=len(plan.get("rows",[])): errors.append("render trace row count mismatch")
    if contract.get("training_record_policy")=="leave_blank" and trace.get("training_record_untouched") is not True:
        errors.append("training record was changed")
    expected_ids=[iid for row in plan.get("rows",[]) for iid in row.get("image_ids",[])]
    trace_images=trace.get("images",[]); trace_ids=[x.get("image_id") for x in trace_images]
    if trace_ids!=expected_ids: errors.append("render trace image order does not match approved plan")
    approved_images={x.get("image_id"):x for x in approved.get("images",[])}
    media_hashes=list(media.values())
    for item in trace_images:
        source=approved_images.get(item.get("image_id"),{})
        if item.get("source_sha256")!=source.get("source_sha256"): errors.append(f"source hash mismatch: {item.get('image_id')}")
        if item.get("prepared_sha256") not in media_hashes: errors.append(f"prepared image missing from DOCX: {item.get('image_id')}")
    layout=subprocess.run([sys.executable,str(scripts/"validate_template_layout.py"),args.docx,"--plan",args.plan,"--json"],capture_output=True,text=True)
    if layout.returncode:
        errors.append("template-specific layout validation failed")
        manual.append(layout.stdout.strip() or layout.stderr.strip())
    visual=args.visual_status
    if visual=="failed": errors.append("visual validation failed")
    if visual=="not_performed": warnings.append("structure passed; visual review not performed")
    if contract.get("visual_check_required") and visual!="passed": errors.append("template requires visual validation")
    passed=not errors
    delivery="ready" if passed and visual=="passed" else "ready_pending_visual_review" if passed else "blocked"
    report={
        "validated_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"docx":str(Path(args.docx)),
        "docx_sha256":file_sha256(args.docx) if Path(args.docx).is_file() else None,
        "template_id":contract.get("template_id"),"template_version":contract.get("template_version"),
        "content_validation":"passed" if not any("content" in x for x in errors) else "failed",
        "structure_validation":"passed" if layout.returncode==0 else "failed","visual_validation":visual,
        "delivery_status":delivery,"errors":errors,"warnings":warnings,"manual_checks":manual,"passed":passed
    }
    dump_json(report,args.report); print(f"passed={str(passed).lower()} delivery_status={delivery} errors={len(errors)} report={args.report}")
    return 0 if passed else 1
if __name__=="__main__": raise SystemExit(main())
