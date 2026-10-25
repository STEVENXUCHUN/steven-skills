#!/usr/bin/env python3
import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]; PY=sys.executable

def main():
 with tempfile.TemporaryDirectory() as td:
  td=Path(td); image=td/'phone.jpg'; im=Image.new('RGB',(40,80),'blue'); exif=im.getexif(); exif[274]=6; im.save(image,exif=exif)
  digest=hashlib.sha256(image.read_bytes()).hexdigest()
  raw={'schema_version':'1.0','task_id':'T','created_at':'2026-10-26T00:00:00Z',
       'messages':[{'message_id':'MSG-001','role':'user','timestamp':None,'text':'测试','asset_ids':['ASSET-001']}],
       'assets':[{'asset_id':'ASSET-001','source_message_id':'MSG-001','original_name':'phone.jpg','path':str(image),'mime_type':'image/jpeg','sha256':digest}]}
  rp,out=td/'raw.json',td/'draft.json'; rp.write_text(json.dumps(raw),encoding='utf-8')
  p=subprocess.run([PY,str(ROOT/'scripts/distill.py'),'--raw',str(rp),'--draft-id','D','--output',str(out)],capture_output=True,text=True)
  if p.returncode: raise AssertionError(p.stdout+p.stderr)
  data=json.loads(out.read_text('utf-8')); item=data['images'][0]
  assert data['schema_version']=='1.1'; assert item['source_sha256']==digest
  assert (item['display_width_px'],item['display_height_px'])==(80,40)
  assert data['metadata']['template_category']['value']=='基础知识'
  print('distill image metadata checks passed')
if __name__=='__main__': main()
