"""Render a compiled lyric foreground over local engine output; verify and retain 3."""
from pathlib import Path
import argparse, datetime, json, os, subprocess

def run(args):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode:raise RuntimeError(p.stderr.decode('utf-8',errors='replace')[-5000:])
    return p.stdout

def probe(path):return json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))

def register_and_prune(output,project_id,registry,protected=()):
    output=Path(output).resolve();registry=Path(registry).resolve()
    data=json.loads(registry.read_text(encoding='utf-8-sig')) if registry.exists() else {'schema':'video-workbench-exports-v1','series':{}}
    if 'series' not in data:raise ValueError('Registry schema mismatch; explicitly seed the known versions first')
    entries=data['series'].setdefault(project_id,[])
    entries[:]=[e for e in entries if Path(e['path']).resolve()!=output and Path(e['path']).is_file()]
    entries.append({'path':str(output),'verified':True,'created':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    removed=[];protected={Path(p).resolve() for p in protected}
    obsolete=entries[:-3]
    # Validate every target before any deletion. Never scan/delete unrelated files.
    for entry in obsolete:
        target=Path(entry['path']).resolve()
        if target.parent!=output.parent or target.suffix.lower()!='.mp4' or not entry.get('verified'):
            raise ValueError('Unsafe registry deletion target: '+str(target))
        if target in protected:raise ValueError('An old export is still a source; stage it as an asset and update dependencies before pruning: '+str(target))
        poster=entry.get('poster')
        if poster:
            pp=Path(poster).resolve()
            if pp.parent!=output.parent or pp.suffix.lower() not in ('.png','.jpg','.jpeg','.webp'):
                raise ValueError('Unsafe poster path: '+str(pp))
    for entry in obsolete:
        target=Path(entry['path']).resolve()
        if target.exists():target.unlink();removed.append(str(target))
        poster=entry.get('poster')
        if poster:
            pp=Path(poster).resolve()
            if pp.exists():pp.unlink()
    data['series'][project_id]=entries[-3:]
    registry.parent.mkdir(parents=True,exist_ok=True)
    temp=registry.with_name(registry.name+'.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(registry)
    return {'retained':[e['path'] for e in entries[-3:]],'removed':removed}

def main(args):
    compiled=Path(args.compiled).resolve();m=json.loads((compiled/'compiled.json').read_text(encoding='utf-8'))
    if m.get('draft') and args.seconds is None:raise ValueError('Draft alignment can only render an explicitly bounded review excerpt')
    visuals=Path(args.visuals).resolve();audio=Path(args.audio).resolve();output=Path(args.output).resolve()
    if output.exists():raise FileExistsError('Choose a new export filename: '+str(output))
    if not visuals.is_file() or not audio.is_file():raise FileNotFoundError('Audio or visual input missing')
    output.parent.mkdir(parents=True,exist_ok=True)
    temp=output.with_name(output.stem+'.partial.mp4')
    if temp.exists():raise FileExistsError('Partial output already exists; inspect before replacing: '+str(temp))
    p=m['preset'];fps=p['fps'];concat=visuals.suffix.lower() in ('.ffconcat','.concat')
    cmd=['ffmpeg','-hide_banner','-y','-filter_threads','2']
    if concat:
        cmd+=['-copyts','-segment_time_metadata','1','-f','concat','-safe','0','-i',str(visuals)]
        filt=f'select=concatdec_select,setpts=N/({fps}*TB)'
    else:
        cmd+=['-i',str(visuals)];filt=f'fps={fps},setpts=PTS-STARTPTS'
    cmd+=['-i',str(audio),'-map','0:v:0','-map','1:a:0','-vf',filt+',ass=lyrics.ass:fontsdir=fonts']
    codec=next(s['codec_name'] for s in probe(audio)['streams'] if s['codec_type']=='audio')
    copy_audio=codec=='aac'
    cmd+=['-c:v','libx264','-preset','veryfast','-crf','16','-threads','4','-pix_fmt','yuv420p','-fps_mode','cfr','-r',str(fps)]
    cmd+=['-c:a','copy'] if copy_audio else ['-c:a','aac','-b:a','320k']
    if args.start:cmd+=['-ss',str(args.start)]
    length=float(args.seconds) if args.seconds is not None else float(m['duration'])
    cmd+=['-t',str(length),'-map_metadata','-1','-movflags','+faststart',str(temp)]
    print(json.dumps({'phase':'rendering','output':str(output),'preview_start':args.start,'preview_duration':args.seconds}),flush=True)
    env=os.environ.copy();env['HYPERFRAMES_NO_TELEMETRY']='1';env['DO_NOT_TRACK']='1'
    with (compiled/(output.stem+'.encode.log')).open('wb') as log:
        r=subprocess.run(cmd,cwd=compiled,stdout=log,stderr=log,env=env)
    if r.returncode:raise RuntimeError('FFmpeg failed; preserve source and inspect '+str(log.name))
    info=probe(temp);video=next(s for s in info['streams'] if s['codec_type']=='video')
    if (video['width'],video['height'])!=(p['width'],p['height']):raise ValueError('Render dimensions differ from the compiled preset')
    if abs(float(info['format']['duration'])-length)>.15:raise ValueError('Export duration differs; verify the full visual timeline covers the audio')
    run(['ffmpeg','-v','error','-i',str(temp),'-f','null','-'])
    same_audio=None
    if copy_audio and args.seconds is None and not args.start:
        hashes=[run(['ffmpeg','-v','error','-i',str(f),'-map','0:a:0','-c:a','copy','-f','hash','-hash','sha256','-']) for f in (audio,temp)]
        same_audio=hashes[0]==hashes[1]
        if not same_audio:raise ValueError('Copied full audio packets changed')
    temp.replace(output)
    report={'output':str(output),'full_decode_passed':True,'duration':info['format']['duration'],'video_frames':video.get('nb_frames'),'audio_copy':copy_audio,'audio_packets_identical':same_audio,'draft':m.get('draft',False),'preview':args.seconds is not None,'bytes':output.stat().st_size}
    if args.seconds is None:
        registry=Path(args.registry).resolve() if args.registry else output.parent/'export-registry.json'
        report['retention']=register_and_prune(output,args.project_id,registry,[visuals,audio]+args.protect)
    (compiled/(output.stem+'.verification.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--visuals',required=True);ap.add_argument('--audio',required=True);ap.add_argument('--compiled',required=True);ap.add_argument('--output',required=True);ap.add_argument('--project-id',required=True);ap.add_argument('--registry');ap.add_argument('--start',type=float,default=0);ap.add_argument('--seconds',type=float);ap.add_argument('--protect',action='append',default=[])
    main(ap.parse_args())
