"""Compile reviewed, unshifted line cues into the user's glyph-progress belt."""
from pathlib import Path
import argparse, json, math, shutil, subprocess, sys

SKILL = Path(__file__).resolve().parents[1]

def run(args, **kwargs):
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    if p.returncode:
        raise RuntimeError(p.stderr.decode('utf-8', errors='replace')[-5000:])
    return p.stdout

def rgb(value):
    return tuple(int(value.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

def bgr(value):
    r, g, b = rgb(value) if isinstance(value, str) else value
    return f'&H00{b:02X}{g:02X}{r:02X}&'

def stamp(t):
    n = max(0, round(t*100))
    return f'{n//360000}:{n//6000%60:02d}:{n//100%60:02d}.{n%100:02d}'

def srtstamp(t):
    n = max(0, round(t*1000))
    return f'{n//3600000:02d}:{n//60000%60:02d}:{n//1000%60:02d},{n%1000:03d}'

def safe_text(s):
    if '\n' in s or '\r' in s or any(x in s for x in ('{', '}', '\\')):
        raise ValueError('Each cue must be one physical line without ASS control characters: '+repr(s))
    return s

def ass_header(p):
    cream = bgr(p['cream'])
    tint = tuple(round(c*(1-p['orange_opacity'])+a*p['orange_opacity']) for c, a in zip(rgb(p['cream']), rgb(p['orange'])))
    common = f",{p['font']},{p['font_size']},{{color}},&H00000000&,&HFF000000&,&HFF000000&,0,0,0,0,100,100,0,0,1,0,0,3,0,0,0,1"
    return (f"[Script Info]\nTitle: video-workbench conveyor glyph progress\nScriptType: v4.00+\nPlayResX: {p['width']}\nPlayResY: {p['height']}\nWrapStyle: 2\nScaledBorderAndShadow: no\nYCbCr Matrix: TV.709\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            + 'Style: Lyric'+common.format(color=cream)+'\n'
            + 'Style: Fill'+common.format(color=bgr(tint))+'\n'
            + 'Style: Shape,Arial,1,&H00000000&,&H00000000&,&HFF000000&,&HFF000000&,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1\n\n'
            + '[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')

def font_tag(text, p):
    return f"\\fn{p['symbol_font']}\\fs{p['font_size']}" if text.strip() in ('♪', '♫', '♬') else f"\\fs{p['font_size']}"

def measure_lines(lines, p, out):
    """Use the actual libass renderer; Pillow point metrics differ from ASS."""
    header = ass_header(p)
    rows=[]
    for i, text in enumerate(lines):
        tags=f"{{\\an3\\q2\\pos({p['right']},951){font_tag(text,p)}\\bord0\\shad0}}"
        rows.append(f'Dialogue: 20,{stamp(i)},{stamp(i+1)},Lyric,,0,0,0,,{tags}{text}')
    (out/'measure.ass').write_text(header+'\n'.join(rows)+'\n', encoding='utf-8-sig')
    cmd=['ffmpeg','-v','error','-f','lavfi','-i',f"color=black:s={p['width']}x{p['height']}:r=1:d={len(lines)}",'-vf','setparams=colorspace=bt709,ass=measure.ass:fontsdir=fonts,format=gray','-frames:v',str(len(lines)),'-f','rawvideo','-pix_fmt','gray','-']
    from PIL import Image
    import tempfile
    with tempfile.TemporaryFile() as err:
        proc=subprocess.Popen(cmd,cwd=out,stdout=subprocess.PIPE,stderr=err)
        result=[];size=p['width']*p['height']
        for text in lines:
            raw=bytearray()
            while len(raw)<size:
                chunk=proc.stdout.read(size-len(raw))
                if not chunk:break
                raw.extend(chunk)
            if len(raw)!=size:
                proc.wait();err.seek(0);raise RuntimeError(err.read().decode('utf-8',errors='replace'))
            im=Image.frombytes('L',(p['width'],p['height']),bytes(raw))
            box=im.point(lambda x:255 if x>5 else 0).getbbox()
            if box is None:raise ValueError('No glyph rendered for '+repr(text))
            if box[0]<=0:raise ValueError('Line exceeds the canvas; do not silently wrap or shrink: '+text)
            result.append({'text':text,'left':box[0],'right':box[2]-1,'width':box[2]-box[0]})
        proc.stdout.close();code=proc.wait();err.seek(0);log=err.read().decode('utf-8',errors='replace')
        if code:raise RuntimeError(log)
        if 'Glyph' in log and 'not found' in log:raise ValueError('Missing glyph; configure a supported font: '+log)
    return result

def compile_file(input_path, out, preset=None, offset=None, progress_seconds=None, draft=False, left=None, intro_end=None):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    data=json.loads(Path(input_path).read_text(encoding='utf-8-sig'))
    if not draft and data.get('audit',{}).get('status')!='reviewed':
        raise ValueError('Timing is not reviewed. Audit against actual audio or use --draft for review only.')
    p=json.loads((SKILL/'assets/lyric-preset.json').read_text(encoding='utf-8'))
    if preset:p.update(json.loads(Path(preset).read_text(encoding='utf-8-sig')))
    if offset is not None:p['offset_seconds']=offset
    if progress_seconds is not None:p['progress_seconds']=progress_seconds
    duration=float(data['duration']);period=duration if p['progress_seconds']=='audio' else float(p['progress_seconds'])
    if duration<=0 or period<=0:raise ValueError('Duration must be positive')
    cues=data['cues'];lines=[safe_text(str(c['text']).strip()) for c in cues]
    if not cues or any(not x for x in lines):raise ValueError('Empty cue or empty lyrics')
    for i,c in enumerate(cues):
        if not (0<=float(c['start'])<float(c['end'])<=duration+.02):raise ValueError(f'Invalid cue {i+1}: {c}')
        if i and float(cues[i-1]['end'])>float(c['start'])+.001:raise ValueError(f'Overlapping singing cues at {i+1}; review timing first')
    fonts=out/'fonts';fonts.mkdir(exist_ok=True)
    for src in (SKILL/'assets/fonts').iterdir():
        if src.is_file():shutil.copy2(src,fonts/src.name)
    measurements=measure_lines(list(dict.fromkeys(lines)),p,out)
    longest=min(measurements,key=lambda x:x['left']);left=longest['left'] if left is None else int(left)
    p['progress_left']=left
    # A separate clock: actual first vocal onset, never the shifted display time.
    vocal=next((c for c in cues if str(c['text']).strip() not in ('♪','♫','♬')),None)
    onset=float(intro_end) if intro_end is not None else (float(vocal['start']) if vocal else None)
    if onset is not None and not 0<=onset<=duration:raise ValueError('Intro end must lie within the audio duration')
    intro={'enabled':bool(p.get('underline') and p.get('intro_progress',True) and onset is not None),
           'end':onset,'left':left,'right':p['progress_right'],'top':p['underline_y'],
           'height':p.get('underline_height',4),'holds_full':True,'clock':'unshifted actual first vocal onset',
           'source':'explicit reviewed override' if intro_end is not None else 'first non-note unshifted cue'}
    phases=[]
    for j,c in enumerate(cues):
        start=float(c['start'])+p['offset_seconds'];end=float(cues[j+1]['start'])+p['offset_seconds'] if j+1<len(cues) else duration
        vocal_end=float(c['end'])+p['offset_seconds']
        if lines[j] in ('♪','♫','♬'):move_end=min(end,start+p['symbol_entry_seconds'])
        elif j+1==len(cues) or end-vocal_end>=p['breath_gap_seconds']:move_end=vocal_end
        else:move_end=end
        if move_end<=start:raise ValueError('Invalid movement duration')
        phases.append({'cue':j+1,'start':start,'move_end':move_end,'end':end,'speed':p['row_pitch']/(move_end-start)})
    header=ass_header(p);rows=[];plain=[];segments=[]
    if p.get('underline'):
        orange=bgr(p['orange'])[4:-1]
        if intro['enabled']:
            right=intro['right'];top=intro['top'];bottom=top+intro['height'];width=right-left
            if width<=0:raise ValueError('Intro progress width must be positive')
            clip=f'\\clip({left},{top},{right},{bottom})'
            if onset>0:clip=f'\\clip({right},{top},{right},{bottom})\\t(0,{round(onset*1000)},{clip})'
            rows.append(f'Dialogue: 1,{stamp(0)},{stamp(duration+.01)},Shape,,0,0,0,,{{\\an7\\pos({left},{top})\\p1\\bord0\\shad0\\c&H{orange}&{clip}}}m 0 0 l {width} 0 {width} {intro["height"]} 0 {intro["height"]}')
        elif not p.get('intro_progress',True):
            # Explicit compatibility mode only; the current default is the intro bar.
            line=f"Dialogue: 1,{stamp(max(0,cues[0]['start']))},{stamp(duration+.01)},Shape,,0,0,0,,{{\\an7\\pos({p['underline_left']},{p['underline_y']})\\p1\\bord0\\shad0\\c&H{orange}&}}m 0 0 l 49 0 45 4 0 4"
            rows.append(line)
    def edge(t):return round(p['clip_bottom']-(p['clip_bottom']-p['clip_top'])*min(max(t/period,0),1))
    for i,text in enumerate(lines):
        for j in range(i,len(phases)):
            ph=phases[j];a=p['entry_y']-(j-i)*p['row_pitch'];b=a-p['row_pitch']
            if a<=p['clip_top']:break
            start=max(0,ph['start']);end=min(duration,ph['end'])
            if end<=start:continue
            move_duration=ph['move_end']-ph['start']
            # Preserve the exact belt phase if the negative offset crosses t=0.
            elapsed=max(0,start-ph['start']);a=a-p['row_pitch']*min(elapsed/move_duration,1)
            move_ms=max(0,round((ph['move_end']-start)*1000));full_ms=round((end-start)*1000)
            motion=f"\\move({p['right']},{a:g},{p['right']},{b:g},0,{move_ms})" if move_ms>0 else f"\\pos({p['right']},{b:g})"
            base=f"\\an3\\q2{font_tag(text,p)}\\bord0\\shad0"
            y0,y1=edge(start),edge(end)
            top=f"\\clip(0,{p['clip_top']},{p['width']},{y0})\\t(0,{full_ms},\\clip(0,{p['clip_top']},{p['width']},{y1}))"
            bottom=f"\\clip({left},{y0},{p['progress_right']},{p['clip_bottom']})\\t(0,{full_ms},\\clip({left},{y1},{p['progress_right']},{p['clip_bottom']}))"
            for layer,style,clip in ((20,'Lyric',top),(21,'Fill',bottom)):
                rows.append(f'Dialogue: {layer},{stamp(start)},{stamp(end)},'+style+',,0,0,0,,{'+base+clip+motion+'}'+text)
            plain.append(f'Dialogue: 20,{stamp(start)},{stamp(end)},Lyric,,0,0,0,,{{'+base+f"\\clip(0,{p['clip_top']},{p['width']},{p['clip_bottom']})"+motion+'}'+text)
            segments.append({'line':i+1,'phase':j+1,'start':start,'end':end,'from_y':a,'to_y':b})
    (out/'lyrics.ass').write_text(header+'\n'.join(rows)+'\n',encoding='utf-8-sig')
    (out/'plain-glyph-reference.ass').write_text(header+'\n'.join(plain)+'\n',encoding='utf-8-sig')
    (out/'lyrics.srt').write_text('\n\n'.join(f"{i+1}\n{srtstamp(c['start']+p['offset_seconds'])} --> {srtstamp(c['end']+p['offset_seconds'])}\n{lines[i]}" for i,c in enumerate(cues))+'\n',encoding='utf-8')
    manifest={'schema':'video-workbench-compiled-v1','duration':duration,'preset':p,'progress_duration':period,'intro_progress':intro,'longest':longest,'measurements':measurements,'cue_count':len(cues),'audit':data.get('audit',{}),'draft':draft,'phases':phases,'segments':segments,'unshifted_cues':cues}
    (out/'compiled.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return manifest

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cues',required=True);ap.add_argument('--out',required=True);ap.add_argument('--preset');ap.add_argument('--offset',type=float);ap.add_argument('--progress-seconds',type=float);ap.add_argument('--left',type=int);ap.add_argument('--intro-end',type=float);ap.add_argument('--draft',action='store_true')
    args=ap.parse_args();m=compile_file(args.cues,args.out,args.preset,args.offset,args.progress_seconds,args.draft,args.left,args.intro_end)
    print(json.dumps({'cue_count':m['cue_count'],'offset':m['preset']['offset_seconds'],'row_pitch':m['preset']['row_pitch'],'progress_seconds':m['progress_duration'],'intro_progress':m['intro_progress'],'longest':m['longest'],'out':str(Path(args.out).resolve())},ensure_ascii=False,indent=2))
