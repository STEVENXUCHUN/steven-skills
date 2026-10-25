#!/usr/bin/env python3
import json, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; PY=sys.executable

def fact(value,status="user_stated",refs=None): return {"value":value,"status":status,"source_refs":refs or ["MSG-001"]}
def run(*args,expect=0):
    p=subprocess.run([PY,*map(str,args)],text=True,capture_output=True)
    if p.returncode!=expect: raise AssertionError(f"command={args}\nstdout={p.stdout}\nstderr={p.stderr}")
    return p

def draft_data():
    return {
      "schema_version":"1.1","task_id":"T-1","draft_id":"D-1","lesson_type":"repair_tip",
      "source_index":[{"source_id":"MSG-001","type":"message"},{"source_id":"RULE:lesson-type-map-v1","type":"rule"}],
      "scope":{"single_point":True,"topic":fact("插头复位要点"),"split_required":False,"excluded_topics":[]},
      "metadata":{
        "group":fact("维修组"),"procedure":fact("测试工序"),"number":fact("T-001"),"creation_date":fact("2026-10-26"),
        "template_category":fact("基础知识","derived",["RULE:lesson-type-map-v1"]),
        "director":fact(None,"unknown",[]),"team_leader":fact(None,"unknown",[]),"made_by":fact("测试员")},
      "content":{
        "title":fact("插头复位要点"),"applicable_to":fact("测试设备"),"prerequisites":fact("断电确认"),
        "problem_or_goal":fact("插接不到位"),"key_point":fact("对正后插到底"),"mistakes":fact("不得斜插"),
        "safety":fact("先断电"),"acceptance":fact("锁扣到位"),"limitations":fact("仅适用于该插头")},
      "steps":[{"step_id":"STEP-001","order":1,"instruction":fact("对正插入"),"check":fact("锁扣到位"),"source_refs":["MSG-001"]}],
      "images":[],"open_items":[],"template_selection":None}

def main():
  with tempfile.TemporaryDirectory() as td:
    td=Path(td); draft=draft_data(); dp,ap=td/"draft.json",td/"approved.json"
    dp.write_text(json.dumps(draft,ensure_ascii=False),encoding="utf-8")
    run(ROOT/"scripts/validate_data.py",dp)
    run(ROOT/"scripts/approve.py","--draft",dp,"--output",ap,"--source-ref","MSG-002")
    run(ROOT/"scripts/validate_data.py",ap)
    plan,approved_plan=td/"render-plan.json",td/"approved-render-plan.json"
    run(ROOT/"scripts/build_render_plan.py","--approved",ap,"--plan-id","P-1","--output",plan)
    run(ROOT/"scripts/validate_render_plan.py","--plan",plan,"--approved",ap,"--draft")
    run(ROOT/"scripts/approve_render_plan.py","--plan",plan,"--approved",ap,"--output",approved_plan,"--source-ref","MSG-003")
    run(ROOT/"scripts/validate_render_plan.py","--plan",approved_plan,"--approved",ap)
    changed=json.loads(ap.read_text("utf-8")); changed["content"]["title"]["value"]+="（改）"
    ap.write_text(json.dumps(changed,ensure_ascii=False),encoding="utf-8")
    run(ROOT/"scripts/validate_data.py",ap,expect=1)
    run(ROOT/"scripts/validate_render_plan.py","--plan",approved_plan,"--approved",ap,expect=1)
    suggested=draft_data(); suggested["content"]["key_point"]=fact("模型猜测","assistant_suggested",[])
    sp=td/"suggested.json"; sp.write_text(json.dumps(suggested,ensure_ascii=False),encoding="utf-8")
    run(ROOT/"scripts/approve.py","--draft",sp,"--output",td/"bad.json","--source-ref","MSG-002",expect=1)
    print("content workflow checks passed")
if __name__=="__main__": main()
