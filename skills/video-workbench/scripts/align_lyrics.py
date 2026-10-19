"""Draft lyric timing from real local audio, then two-context forced alignment.

Outputs need AI review. Original line text is never replaced by ASR text.
"""
from pathlib import Path
import argparse, difflib, hashlib, json, re, subprocess

def call(args):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode:raise RuntimeError(p.stderr.decode('utf-8',errors='replace')[-4000:])
    return p.stdout

def compact(s):return ''.join(c.lower() for c in s if c.isalnum())

def pieces(s):
    return [compact(x) for x in re.findall(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?|[\u3400-\u9fff]|[^\W\d_]+",s) if compact(x)]

def time_sec(t):
    p=t.replace(',','.').split(':')
    return sum(float(x)*60**i for i,x in enumerate(reversed(p)))

def parse_timed(text):
    cues=[]
    if '-->' in text:
        for block in re.split(r'\n\s*\n',text.replace('\r','').strip()):
            rows=block.splitlines();idx=next((i for i,s in enumerate(rows) if '-->' in s),None)
            if idx is None:continue
            a,b=rows[idx].split('-->',1);end=b.strip().split()[0]
            words=' '.join(rows[idx+1:]).strip()
            if words:cues.append({'start':time_sec(a.strip()),'end':time_sec(end),'text':words})
    else:
        for row in text.splitlines():
            times=re.findall(r'\[(\d+:\d+(?:\.\d+)?)\]',row)
            words=re.sub(r'\[[^]]*\]','',row).strip()
            if words:
                for t in times:cues.append({'start':time_sec(t),'text':words})
        cues.sort(key=lambda c:c['start'])
        for i,c in enumerate(cues):c['end']=cues[i+1]['start'] if i+1<len(cues) else c['start']+5
    return cues

def make_coarse(lines,words,duration):
    known=[];owners=[]
    for i,line in enumerate(lines):
        if line in ('♪','♫','♬'):continue
        for token in pieces(line):known.append(token);owners.append(i)
    seq=[w['token'] for w in words];mapping={}
    for a,b,n in difflib.SequenceMatcher(None,known,seq,autojunk=False).get_matching_blocks():
        for k in range(n):mapping[a+k]=b+k
    rows=[]
    for i,line in enumerate(lines):
        indices=[j for j,v in enumerate(owners) if v==i];matched=[words[mapping[j]] for j in indices if j in mapping]
        if matched:
            rows.append({'index':i,'start':min(x['start'] for x in matched),'end':max(x['end'] for x in matched),'coverage':len(matched)/max(1,len(indices))})
        else:rows.append({'index':i,'start':None,'end':None,'coverage':0})
    # Only coarse search windows use interpolation. Never accept it as timing.
    for i,r in enumerate(rows):
        if r['start'] is None:
            before=next((x for x in reversed(rows[:i]) if x['end'] is not None),None)
            after=next((x for x in rows[i+1:] if x['start'] is not None),None)
            r['start']=before['end'] if before else 0
            r['end']=max(r['start']+.3,after['start'] if after else duration)
    return rows

def main(args):
    import numpy as np
    from faster_whisper import WhisperModel
    from faster_whisper.audio import pad_or_trim
    from faster_whisper.tokenizer import Tokenizer
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    raw=Path(args.lyrics).read_text(encoding='utf-8-sig')
    if Path(args.lyrics).suffix.lower() in ('.srt','.lrc','.vtt'):
        provided=parse_timed(raw);lines=[c['text'] for c in provided]
    else:provided=[];lines=[s.strip() for s in raw.splitlines() if s.strip()]
    if not lines:raise ValueError('The supplied lyric file is empty')
    probe=json.loads(call(['ffprobe','-v','error','-show_format','-show_streams','-of','json',args.audio]))
    duration=float(probe['format']['duration'])
    pcm=call(['ffmpeg','-v','error','-i',args.audio,'-map','0:a:0','-ac','1','-ar','16000','-f','f32le','-'])
    audio=np.frombuffer(pcm,dtype='<f4').copy()
    anchors=parse_timed(Path(args.timestamps).read_text(encoding='utf-8-sig')) if args.timestamps else provided
    if not anchors:
        tags=probe.get('format',{}).get('tags',{})
        for k,v in tags.items():
            if 'lyric' in k.lower():
                anchors=parse_timed(v)
                if anchors:break
    model=WhisperModel(str(Path(args.model).resolve()),device='cpu',compute_type='int8',cpu_threads=args.threads,num_workers=1,local_files_only=True)
    coarse_words=[];language=args.language
    if anchors:
        if model.model.is_multilingual and language is None:
            raise ValueError('Supply --language for timestamp-assisted alignment with a multilingual model')
        for a in anchors:
            tokens=pieces(a['text']);span=max(.1,min(duration,a['end'])-a['start'])
            for i,t in enumerate(tokens):coarse_words.append({'token':t,'start':a['start']+span*i/max(1,len(tokens)),'end':a['start']+span*(i+1)/max(1,len(tokens))})
        language=language or 'en'
        coarse_source='provided/embedded timed cues, coarse positioning only'
    else:
        segments,info=model.transcribe(audio,language=language,word_timestamps=True,vad_filter=False,condition_on_previous_text=False,beam_size=5)
        language=info.language
        for seg in segments:
            for word in seg.words or []:
                tokens=pieces(word.word)
                for t in tokens:coarse_words.append({'token':t,'start':float(word.start),'end':float(word.end)})
        coarse_source='local ASR word positions'
    if not coarse_words:raise ValueError('No coarse word positions obtained; inspect audio and model/language')
    coarse=make_coarse(lines,coarse_words,duration)
    if args.windows:
        groups=json.loads(Path(args.windows).read_text(encoding='utf-8-sig'))['groups']
    else:
        groups=[];current=[]
        for i,r in enumerate(coarse):
            if lines[i] in ('♪','♫','♬'):
                if current:groups.append(current);current=[]
                continue
            if current:
                prev=coarse[current[-1]];first=coarse[current[0]]
                if r['end']-first['start']>23 or r['start']-prev['end']>2 or sum(len(lines[j]) for j in current)>350:
                    groups.append(current);current=[]
            current.append(i)
        if current:groups.append(current)
        groups=[{'start':min(coarse[j]['start'] for j in ids),'end':max(coarse[j]['end'] for j in ids),'line_indices':ids} for ids in groups]
    tokenizer=Tokenizer(model.hf_tokenizer,model.model.is_multilingual,task='transcribe',language=language)
    candidates={i:[] for i in range(len(lines))};evidence=[];warnings=[]
    for gid,g in enumerate(groups):
        ids=g.get('line_indices',g.get('lineIndices'))
        if not ids:raise ValueError('Every window needs zero-based line_indices')
        text=' '.join(lines[j] for j in ids);expected=compact(text)
        tokens=tokenizer.encode(' '+text)
        if len(tokens)>440:raise ValueError('Window transcript exceeds model token limit; split windows')
        variants=[]
        for before,after in ((.25,.25),(.9,.6)):
            begin=max(0,float(g['start'])-before);end=min(duration,float(g['end'])+after)
            if end-begin>29.8 or end<=begin:raise ValueError(f'Window {gid} must span less than 29.8 seconds; review coarse windows')
            chunk=audio[int(begin*16000):int(end*16000)]
            features=model.feature_extractor(chunk);enc=model.encode(pad_or_trim(features))
            found=model.find_alignment(tokenizer,[tokens],enc,int(features.shape[-1]))[0]
            words=[{'word':w['word'],'start':round(begin+float(w['start']),3),'end':round(begin+float(w['end']),3),'probability':float(w['probability'])} for w in found]
            if compact(''.join(w['word'] for w in words))!=expected:raise ValueError('Forced text does not match supplied text; inspect tokenization')
            pos=0;spans=[]
            for w in words:
                n=len(compact(w['word']));spans.append((pos,pos+n,w));pos+=n
            pos=0;bounds=[]
            for j in ids:
                n=len(compact(lines[j]));selected=[w for a,b,w in spans if b>pos and a<pos+n]
                if not selected:raise ValueError('No aligned word for input line '+str(j+1))
                c={'start':min(w['start'] for w in selected),'end':max(w['end'] for w in selected),'confidence':sum(w['probability'] for w in selected)/len(selected)}
                if c['start']<=begin+.06:
                    warnings.append({'line':j+1,'reason':'alignment touches crop start; verify actual vocal onset, not leading music'})
                candidates[j].append(c);bounds.append({'line':j+1,**c});pos+=n
            variants.append({'padding':[before,after],'bounds':bounds,'words':words})
        evidence.append({'group':gid,'window':g,'variants':variants})
    cues=[]
    for i,line in enumerate(lines):
        choices=candidates[i]
        if line in ('♪','♫','♬'):
            before=next((candidates[j] for j in range(i-1,-1,-1) if candidates[j]),[])
            after=next((candidates[j] for j in range(i+1,len(lines)) if candidates[j]),[])
            start=sum(v['end'] for v in before)/len(before) if before else 0
            end=sum(v['start'] for v in after)/len(after) if after else duration
        elif choices:
            start=sum(v['start'] for v in choices)/len(choices);end=sum(v['end'] for v in choices)/len(choices)
            spread=max(max(v[k] for v in choices)-min(v[k] for v in choices) for k in ('start','end'))
            if spread>.25:warnings.append({'line':i+1,'reason':'context disagreement','seconds':round(spread,3)})
            if coarse[i]['coverage']<.5:warnings.append({'line':i+1,'reason':'low coarse match; check repeated passages'})
            if coarse[i]['coverage']>=.5 and abs(start-coarse[i]['start'])>.5:
                warnings.append({'line':i+1,'reason':'forced onset differs from coarse position; inspect breath/leading sound','seconds':round(abs(start-coarse[i]['start']),3)})
            if min(v['confidence'] for v in choices)<.15:warnings.append({'line':i+1,'reason':'low forced alignment confidence'})
        else:raise ValueError(f'Line {i+1} not covered by windows')
        if end-start<.25:warnings.append({'line':i+1,'reason':'very short or reversed cue'})
        cues.append({'index':i+1,'start':round(max(0,start),2),'end':round(min(duration,end),2),'text':line})
    for a,b in zip(cues,cues[1:]):
        if a['end']>b['start']:warnings.append({'line':a['index'],'reason':'overlap; review both cues','overlap':round(a['end']-b['start'],3)})
    result={'schema':'video-workbench-cues-v1','duration':duration,'source':{'audio':str(Path(args.audio).resolve()),'lyrics':str(Path(args.lyrics).resolve()),'lyrics_sha256':hashlib.sha256(Path(args.lyrics).read_bytes()).hexdigest()},'audit':{'status':'needs_review','method':'Actual audio, two-context local forced alignment','evidence':'alignment-evidence.json','warnings':warnings},'cues':cues}
    (out/'cues.draft.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'alignment-evidence.json').write_text(json.dumps({'coarse_source':coarse_source,'coarse':coarse,'groups':groups,'forced':evidence},ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'source-lines.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'lines':len(lines),'duration':duration,'groups':len(groups),'warnings':len(warnings),'status':'needs_review','output':str(out/'cues.draft.json')},ensure_ascii=False,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--audio',required=True);ap.add_argument('--lyrics',required=True);ap.add_argument('--timestamps');ap.add_argument('--model',required=True);ap.add_argument('--language');ap.add_argument('--windows');ap.add_argument('--threads',type=int,default=4);ap.add_argument('--out',required=True)
    main(ap.parse_args())
