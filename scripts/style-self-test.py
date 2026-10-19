"""Observable subtitle checks with original synthetic lyrics, no private song data."""
from pathlib import Path
import argparse,importlib.util,json,subprocess,tempfile,statistics
from PIL import Image,ImageChops,ImageFilter
ROOT=Path(__file__).resolve().parents[1];SKILL=ROOT/'skills/video-workbench'
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def run(args,**kw):
    r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**kw)
    if r.returncode:raise RuntimeError(r.stderr.decode('utf-8',errors='replace')[-4000:])
    return r.stdout
def main(args):
    generated=ROOT/'examples/generated';generated.mkdir(parents=True,exist_ok=True)
    lines=(ROOT/'examples/lyrics.md').read_text(encoding='utf-8').splitlines()
    lines=[s.strip() for s in lines if s.strip()];cues=[];clock=1.
    for i,line in enumerate(lines):
        span=8. if line=='♪' else 2.
        cues.append({'index':i+1,'start':clock,'end':clock+span-.2,'text':line});clock+=span
    duration=clock+1
    data={'duration':duration,'audit':{'status':'reviewed','notes':'Synthetic controlled rendering fixture, not an ASR accuracy claim'},'cues':cues}
    cuefile=generated/'cues.json';cuefile.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    compiler=load('lyric_compiler',SKILL/'scripts/compile_lyrics.py');out=generated/'compiled'
    manifest=compiler.compile_file(cuefile,out)
    assert manifest['preset']['offset_seconds']==0 and manifest['preset']['row_pitch']==40
    assert manifest['progress_duration']==duration and manifest['cue_count']==len(lines)
    assert all(abs(p['speed']-40/(p['move_end']-p['start']))<.001 for p in manifest['phases'])
    source=(out/'lyrics.ass').read_text(encoding='utf-8-sig');header=source.split('[Events]')[0]
    body=[s for s in source.splitlines() if s.startswith(('Dialogue: 20,','Dialogue: 21,'))]
    (out/'masked-only.ass').write_text(header+'[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'+'\n'.join(body)+'\n',encoding='utf-8-sig')
    def layer(t,name):
        raw=run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=1920x1080:r=30:d=0.04','-vf',f'setparams=colorspace=bt709,setpts=PTS+{t}/TB,ass={name}:fontsdir=fonts','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'],cwd=out)
        return Image.frombytes('RGB',(1920,1080),raw)
    checks=[]
    for t in [12,30,45,duration-.1]:
        reference=layer(t,'plain-glyph-reference.ass');actual=layer(t,'masked-only.ass')
        support=reference.getchannel('R').point(lambda v:255 if v>10 else 0).filter(ImageFilter.MaxFilter(5))
        ink=actual.getchannel('R').point(lambda v:255 if v>10 else 0)
        assert ImageChops.subtract(ink,support).getbbox() is None,'Color escaped the glyph mask'
        assert ink.crop((0,0,1920,115)).getbbox() is None
        assert ink.crop((0,964,1920,1080)).getbbox() is None
        r,g,b=actual.split();orange=ImageChops.multiply(r.point(lambda v:255 if v>210 else 0),g.point(lambda v:255 if 100<v<200 else 0))
        assert orange.getbbox() is not None
        checks.append({'time':t,'outside_glyph_mask':0,'orange_text_present':True})
    notephase=next(p for p in manifest['phases'] if lines[p['cue']-1]=='♪')
    pause_a=layer(notephase['move_end']+1,'plain-glyph-reference.ass');pause_b=layer(notephase['end']-1,'plain-glyph-reference.ass')
    assert ImageChops.difference(pause_a,pause_b).getbbox() is None,'Conveyor did not pause in the instrumental'
    assert ImageChops.difference(layer(notephase['end']+.5,'plain-glyph-reference.ass'),pause_b).getbbox() is not None
    assert any(s.endswith('♪') for s in body),'Music note not represented as a glyph'
    # Isolate the bottom music-note row while the conveyor is paused.
    note=layer(notephase['move_end']+1,'masked-only.ass').crop((1750,925,1834,964))
    nr,ng,nb=note.split()
    assert ImageChops.multiply(nr.point(lambda v:255 if v>210 else 0),ng.point(lambda v:255 if 100<v<200 else 0)).getbbox() is not None,'Music note is not visibly tinted'
    # Test registry behavior in an isolated directory, never user exports.
    renderer=load('lyric_renderer',SKILL/'scripts/render_video.py')
    with tempfile.TemporaryDirectory(prefix='retention-',dir=generated) as td:
        temp=Path(td).resolve();assert temp.parent==generated.resolve()
        registry=temp/'registry.json'
        for n in ['one','two','three','four','unrelated']:(temp/(n+'.mp4')).write_bytes(b'isolated registry fixture')
        for n in ['one','two','three']:renderer.register_and_prune(temp/(n+'.mp4'),'sample',registry)
        try:renderer.register_and_prune(temp/'four.mp4','sample',registry,[temp/'one.mp4']);raise AssertionError('Protected source was not blocked')
        except ValueError:pass
        assert (temp/'one.mp4').exists()
        renderer.register_and_prune(temp/'four.mp4','sample',registry)
        assert not (temp/'one.mp4').exists() and (temp/'unrelated.mp4').exists()
    if args.write_reference:
        if not args.background:raise ValueError('--write-reference requires a locally rendered engine --background')
        t=45
        png=generated/'style-reference.png'
        run(['ffmpeg','-v','error','-y','-loop','1','-i',str(Path(args.background).resolve()),'-vf',f'setparams=colorspace=bt709,setpts=PTS+{t}/TB,ass=lyrics.ass:fontsdir=fonts','-frames:v','1',str(png)],cwd=out)
        im=Image.open(png);im.thumbnail((1280,720))
        im.save(SKILL/'assets/latest-style.jpg',quality=94);im.save(ROOT/'docs/style-reference.jpg',quality=94)
    report={'passed':True,'default_offset':0,'row_pitch':40,'glyph_mask':checks,'music_note':True,'instrumental_pause_and_resume':True,'retention_three_only':True,'protected_source_preserved':True,'unrelated_file_preserved':True,'synthetic_fixture':True}
    (generated/'style-test.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-reference',action='store_true');p.add_argument('--background');main(p.parse_args())
