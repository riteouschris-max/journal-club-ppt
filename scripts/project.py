"""Small, hash-checked project cache. Uses PyMuPDF only for source extraction."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
from datetime import datetime,timezone
import pymupdf as fitz

SKILL=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path,default=None):return json.loads(Path(path).read_text(encoding='utf-8-sig')) if Path(path).exists() else default
def save(path,data):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_suffix(p.suffix+'.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(p)
def digest(data):return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()
def local(root,value):
    p=(Path(root)/value).resolve()
    if not p.is_relative_to(Path(root).resolve()):raise ValueError('Project asset path must stay inside workspace: '+str(value))
    return p
def pages(spec,count):
    if not spec or spec=='all':return list(range(1,count+1))
    result=[]
    for part in spec.split(','):
        ends=part.split('-');result.extend(range(int(ends[0]),int(ends[-1])+1))
    result=sorted(set(result))
    if not result or min(result)<1 or max(result)>count:raise ValueError('Page range outside document')
    return result
def source(root):
    state=load(root/'state.json',{});p=local(root,state['paper']['path'])
    if sha(p)!=state['paper']['sha256']:raise ValueError('Source PDF changed; use a separate workspace or deliberately re-ingest it')
    return p,state
def init(root,paper):
    root.mkdir(parents=True,exist_ok=True);h=sha(paper);state=load(root/'state.json',{})
    if state and state.get('paper',{}).get('sha256')!=h:raise ValueError('Workspace already belongs to a different source PDF')
    p=root/'source/paper.pdf';p.parent.mkdir(exist_ok=True)
    if p.exists() and sha(p)!=h:raise ValueError('Existing source differs; refusing to overwrite')
    if not p.exists():shutil.copy2(paper,p)
    index=root/'cache/index.json';cached=load(index,{})
    files_ok=cached.get('paper_sha256')==h and all((root/f"cache/text/page-{v['page']:03d}.txt").exists() for v in cached.get('pages',[]))
    if not files_ok:
        doc=fitz.open(p);items=[]
        for i,page in enumerate(doc,1):
            text=page.get_text(sort=True);f=root/f'cache/text/page-{i:03d}.txt';f.parent.mkdir(parents=True,exist_ok=True);f.write_text(text,encoding='utf8')
            items.append({'page':i,'width_pt':page.rect.width,'height_pt':page.rect.height,'text_chars':len(text),'figure_mentions':sorted(set(re.findall(r'\bFig(?:ure)?\.?\s*\d+[A-Za-z]?',text)))})
        save(index,{'paper_sha256':h,'metadata':doc.metadata,'pages':items})
    if not state:
        save(root/'state.json',{'paper':{'path':'source/paper.pdf','sha256':h},'phase':'reading','completed':['source_cached'],'pending':['scientific_reading','figure_inventory','slide_plan','build','render_review'],'next_action':'Read cache/index.json and relevant cached pages; inspect all original figure pages','updated_at':utc()})
    for name,value in [('assets.json',{}),('figure_inventory.json',[])]:
        if not (root/name).exists():save(root/name,value)
    if not (root/'theme.json').exists():shutil.copy2(SKILL/'assets/theme.json',root/'theme.json')
    idx=load(index)
    print(json.dumps({'workspace':str(root),'cache_hit':bool(files_ok),'page_count':len(idx['pages']),'low_text_pages':[v['page'] for v in idx['pages'] if v['text_chars']<100],'index':str(index)},ensure_ascii=False))
def crop(root,request):
    p,state=source(root);doc=fitz.open(p);assets=load(root/'assets.json',{});changed=[];reused=[]
    jobs=load(request);ids=[j['id'] for j in jobs]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate crop IDs')
    for job in jobs:
        key=job['id']
        if not re.fullmatch(r'[A-Za-z0-9_-]+',key):raise ValueError('Use a simple unique asset ID')
        pg=int(job['page']);dpi=int(job.get('dpi',450));box=fitz.Rect(job['rect'])
        if pg<1 or pg>len(doc) or dpi<72 or dpi>900:raise ValueError('Invalid page or DPI')
        if box.is_empty or not doc[pg-1].rect.contains(box):raise ValueError('Crop outside source page: '+key)
        signature=digest({'paper':state['paper']['sha256'],'page':pg,'rect':list(box),'dpi':dpi})
        target=root/f'assets/{key}.png';old=assets.get(key,{})
        if old.get('source_signature')==signature and target.exists() and sha(target)==old.get('sha256'):
            reused.append(key);continue
        target.parent.mkdir(exist_ok=True);pix=doc[pg-1].get_pixmap(matrix=fitz.Matrix(dpi/72,dpi/72),clip=box,alpha=False);pix.save(target)
        assets[key]={'path':f'assets/{key}.png','sha256':sha(target),'kind':'evidence','page':pg,'rect':list(box),'dpi':dpi,'pixels':[pix.width,pix.height],
            'source_sha256':state['paper']['sha256'],'source_signature':signature,'panel':job.get('panel',key),'readout':job.get('readout','')}
        changed.append(key)
    save(root/'assets.json',assets);print(json.dumps({'extracted':changed,'reused':reused},ensure_ascii=False))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['init','status','text','preview','crop','checkpoint']);ap.add_argument('--workspace',required=True,type=Path)
    ap.add_argument('--paper',type=Path);ap.add_argument('--pages');ap.add_argument('--request',type=Path);ap.add_argument('--phase');ap.add_argument('--next');ap.add_argument('--completed');ap.add_argument('--pending')
    a=ap.parse_args();root=a.workspace.resolve()
    if a.command=='init':
        if not a.paper:ap.error('--paper required')
        return init(root,a.paper)
    p,state=source(root)
    if a.command=='status':print(json.dumps(state,ensure_ascii=False));return
    if a.command=='checkpoint':
        if a.phase:state['phase']=a.phase
        if a.next:state['next_action']=a.next
        if a.completed is not None:state['completed']=[x for x in a.completed.split(',') if x]
        if a.pending is not None:state['pending']=[x for x in a.pending.split(',') if x]
        state['updated_at']=utc();save(root/'state.json',state);print('Checkpoint saved');return
    if a.command=='crop':
        if not a.request:ap.error('--request required')
        return crop(root,a.request)
    doc=fitz.open(p);selected=pages(a.pages,len(doc))
    if a.command=='text':
        print(json.dumps([{'page':n,'text':(root/f'cache/text/page-{n:03d}.txt').read_text(encoding='utf8')} for n in selected],ensure_ascii=False));return
    out=[]
    for n in selected:
        target=root/f'cache/previews/page-{n:03d}.png';target.parent.mkdir(exist_ok=True)
        if not target.exists():doc[n-1].get_pixmap(matrix=fitz.Matrix(1.8,1.8),alpha=False).save(target)
        out.append(str(target))
    print(json.dumps(out))
if __name__=='__main__':main()
