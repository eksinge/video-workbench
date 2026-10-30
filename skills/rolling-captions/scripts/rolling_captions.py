"""Local ASR -> forced alignment -> transparent two-line roll-up ASS -> MP4.

Models are always supplied local paths; this script never installs dependencies.
"""
from pathlib import Path
import argparse
import csv
import json
import math
import os
import subprocess


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def run(cmd):
    return subprocess.check_output([str(x) for x in cmd])


def probe(path):
    return json.loads(run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', path]))


def pcm(path):
    import numpy as np
    return np.frombuffer(run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', '16000', '-f', 'f32le', '-']), dtype='<f4').copy()


def extract_words(data):
    words = data.get('words', data.get('word_segments'))
    if words is None:
        words = [w for s in data.get('segments', []) for w in s.get('words', [])]
    if not words:
        raise ValueError('No timed words found')
    return [dict(w, word=w.get('word', w.get('text', '')).strip()) for w in words]


def validate(words, duration):
    last = 0
    for i, w in enumerate(words):
        a, b = w.get('start'), w.get('end')
        if not w['word'] or a is None or b is None or not (last <= a < b <= duration):
            raise ValueError(f'Word {i + 1} has missing, overlapping or invalid timing: {w}')
        if any(c in w['word'] for c in '{}\\\n\r'):
            raise ValueError(f'Word {i + 1} contains unsupported ASS control characters')
        last = b


def transcribe(args):
    model_path = Path(args.model).resolve()
    if not (model_path / 'model.bin').is_file():
        raise ValueError('Supply an existing CTranslate2 model directory containing model.bin')
    dll_handle = None
    if args.dll_dir:
        dll = str(Path(args.dll_dir).resolve())
        os.environ['PATH'] = dll + os.pathsep + os.environ.get('PATH', '')
        if os.name == 'nt':
            dll_handle = os.add_dll_directory(dll)
    from faster_whisper import WhisperModel
    audio = pcm(args.audio)
    model = WhisperModel(str(model_path), device=args.device,
                         compute_type=args.compute_type or ('int8_float16' if args.device == 'cuda' else 'int8'),
                         local_files_only=True)
    segments, info = model.transcribe(audio, language=args.language, word_timestamps=True,
                                     beam_size=5, condition_on_previous_text=False, vad_filter=True)
    rows = []
    for s in segments:
        rows.append({'start': s.start, 'end': s.end, 'text': s.text.strip(),
                     'words': [{'word': w.word.strip(), 'start': w.start, 'end': w.end,
                                'probability': w.probability} for w in s.words or []]})
        print(f'{s.start:.2f}-{s.end:.2f} {s.text}', flush=True)
    write(args.out, {'language': info.language, 'duration': len(audio) / 16000,
                     'review_status': 'automatic draft', 'segments': rows})
    if dll_handle:
        dll_handle.close()


def align(args):
    # Disallow surprise HF downloads; torchaudio cache is checked before loading.
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import torch
    from whisperx.alignment import align as whisperx_align, load_align_model
    torch.set_num_threads(4)
    data = read(args.asr)
    language = args.language or data.get('language', 'en')
    if args.align_model:
        model_name = str(Path(args.align_model).resolve())
        if not Path(model_name).is_dir():
            raise ValueError('--align-model must be an existing local HuggingFace model directory')
    else:
        if language != 'en' or not args.model_dir:
            raise ValueError('English needs --model-dir; other languages need --align-model')
        checkpoint = Path(args.model_dir) / 'wav2vec2_fairseq_base_ls960_asr_ls960.pth'
        if not checkpoint.is_file():
            raise ValueError(f'Existing alignment checkpoint missing: {checkpoint}; no download attempted')
        model_name = 'WAV2VEC2_ASR_BASE_960H'
    audio = pcm(args.audio)
    duration = len(audio) / 16000
    replacements = read(args.replacements) if args.replacements else {}
    segments = []
    for s in data['segments']:
        text = s['text']
        for before, after in replacements.items():
            text = text.replace(before, after)
        if s['end'] - s['start'] > 20:
            raise ValueError('ASR segment exceeds 20 seconds; split it using existing word positions first')
        if segments and s['end'] + .08 - segments[-1]['start'] <= 20:
            segments[-1]['text'] += ' ' + text
            segments[-1]['end'] = min(duration, s['end'] + .08)
        else:
            segments.append({'start': max(0, s['start'] - .08),
                             'end': min(duration, s['end'] + .08), 'text': text})
    model, meta = load_align_model(language, args.device, model_name=model_name, model_dir=args.model_dir)
    result = whisperx_align(segments, model, meta, audio, args.device, return_char_alignments=False)
    result.update(duration=duration, language=language, review_status='automatic draft',
                  alignment_windows=segments, replacements=replacements)
    # Preserve output even when timing needs repair; compile refuses invalid words.
    write(args.out, result)
    validate(extract_words(result), duration)
    print(f'Aligned {len(result["word_segments"])} words', flush=True)


def clock(t, srt=False):
    scale = 1000 if srt else 100
    units = round(t * scale)
    sec, fraction = divmod(units, scale)
    minute, sec = divmod(sec, 60)
    hour, minute = divmod(minute, 60)
    return (f'{hour:02}:{minute:02}:{sec:02},{fraction:03}' if srt else
            f'{hour}:{minute:02}:{sec:02}.{fraction:02}')


def compile_ass(args):
    from PIL import ImageFont
    data = read(args.timeline)
    words = extract_words(data)
    duration = args.duration if args.duration is not None else data.get('duration')
    if not duration or duration <= 0:
        raise ValueError('Provide positive --duration or a duration field in the JSON')
    validate(words, duration)
    if min(args.width, args.height, args.font_size, args.line_height, args.line_width, args.scroll) <= 0:
        raise ValueError('Dimensions and animation parameters must be positive')
    if ',' in args.font or '\n' in args.font:
        raise ValueError('Invalid ASS font name')
    sx, sy = args.width / 1920, args.height / 1080
    size, x = args.font_size * sy, args.x * sx
    top, pitch, max_width = args.top * sy, args.line_height * sy, args.line_width * sx
    bottom = top + pitch
    if x < 0 or top < 0 or x + max_width > args.width or bottom + pitch > args.height:
        raise ValueError('Caption window lies outside the video canvas')
    font = ImageFont.truetype(args.font_file, round(size))
    lines = []
    for w in words:
        if font.getlength(w['word']) > max_width:
            raise ValueError(f'Word exceeds line width: {w["word"]}; adjust font or width')
        if not lines or font.getlength(' '.join(v['word'] for v in lines[-1] + [w])) > max_width:
            lines.append([])
        lines[-1].append(w)
    starts = [line[0]['start'] + args.offset for line in lines]
    frame = lambda t: max(0, math.ceil(t * args.fps - 1e-7))
    last = frame(duration)
    bounds = {0, last} | {frame(w['start'] + args.offset) for w in words if w['start'] + args.offset < duration}
    for t in starts[1:]:
        bounds.update(range(frame(t), min(last, frame(t + args.scroll)) + 1))
    bounds = sorted(b for b in bounds if b <= last)
    events = []
    def y(idx, current, t):
        if current == 0:
            return bottom
        p = max(0, min(1, (t - starts[current]) / args.scroll))
        return bottom + (idx - current + 1) * pitch - p * p * (3 - 2 * p) * pitch
    for fa, fb in zip(bounds, bounds[1:]):
        a, b = fa / args.fps, min(duration, fb / args.fps)
        visible = [i for i, start in enumerate(starts) if start <= a + 1e-7]
        if not visible or b <= a or clock(a) == clock(b):
            continue
        current = visible[-1]
        for idx in range(max(0, current - 2), current + 1):
            shown = [w for w in lines[idx] if w['start'] + args.offset <= a + 1e-7]
            if not shown:
                continue
            y1, y2 = y(idx, current, a), y(idx, current, b)
            if max(y1, y2) + pitch <= top:
                continue
            tags = (f'\\clip({round(x-12*sx)},{round(top)},{round(x+max_width+20*sx)},{round(bottom+pitch)})'
                    f'\\move({x:.3f},{y1:.3f},{x:.3f},{y2:.3f},0,{round((b-a)*1000)})'
                    '\\an7\\bord0\\shad0\\c&HFFFFFF&')
            events.append(f'Dialogue: 0,{clock(a)},{clock(b)},Default,,0,0,0,,{{{tags}}}' + ' '.join(w['word'] for w in shown))
    header = f'''[Script Info]
Title: Rolling captions
ScriptType: v4.00+
PlayResX: {args.width}
PlayResY: {args.height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{args.font},{size:.3f},&H00FFFFFF,&H00FFFFFF,&HFF000000,&HFF000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'captions.ass').write_text(header + '\n'.join(events) + '\n', encoding='utf-8-sig')
    (out / 'words.srt').write_text('\n'.join(f'{i+1}\n{clock(w["start"],True)} --> {clock(w["end"],True)}\n{w["word"]}\n' for i, w in enumerate(words)), encoding='utf-8-sig')
    with (out / 'words.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['word', 'start', 'end', 'score'])
        writer.writerows([w['word'], w['start'], w['end'], w.get('score', '')] for w in words)
    write(out / 'timeline.json', {'duration': duration, 'words': words, 'review_status': data.get('review_status', 'automatic draft')})
    report = dict(duration=duration, words=len(words), lines=len(lines), events=len(events),
                  width=args.width, height=args.height, fps=args.fps, font=args.font,
                  font_size=size, background=False, offset=args.offset, scroll=args.scroll)
    write(out / 'compile-report.json', report)
    print(json.dumps(report), flush=True)


def render(args):
    compiled = Path(args.compiled).resolve()
    output = Path(args.output).resolve()
    cfg = read(compiled / 'compile-report.json')
    if not args.video and not args.audio:
        raise ValueError('Provide --video and/or --audio')
    sources = [Path(p).resolve() for p in [args.video, args.audio] if p]
    if output in sources or output.exists():
        raise ValueError('Output must be a new path, distinct from all sources')
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = ['ffmpeg', '-nostdin', '-n', '-hide_banner']
    if args.video:
        cmd += ['-i', str(Path(args.video).resolve())]
    else:
        cmd += ['-f', 'lavfi', '-i', f'color=c=black:s={cfg["width"]}x{cfg["height"]}:r={cfg["fps"]}']
    if args.audio:
        cmd += ['-i', str(Path(args.audio).resolve())]
    vf = (f'scale={cfg["width"]}:{cfg["height"]}:force_original_aspect_ratio=decrease,'
          f'pad={cfg["width"]}:{cfg["height"]}:(ow-iw)/2:(oh-ih)/2,'
          f'fps={cfg["fps"]},tpad=stop_mode=clone:stop_duration={cfg["duration"]},ass=captions.ass')
    cmd += ['-map', '0:v:0', '-map', '1:a:0' if args.audio else '0:a:0', '-vf', vf,
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-threads', '6',
            '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-t', str(cfg['duration']),
            '-movflags', '+faststart', str(output)]
    with output.with_suffix('.encode.log').open('w', encoding='utf-8') as log:
        subprocess.run(cmd, cwd=compiled, stdout=log, stderr=log, check=True)
    print(str(output), flush=True)


def verify(args):
    compiled = Path(args.compiled)
    cfg, timeline = read(compiled / 'compile-report.json'), read(compiled / 'timeline.json')
    validate(extract_words(timeline), cfg['duration'])
    p = probe(args.video)
    v = next(s for s in p['streams'] if s['codec_type'] == 'video')
    next(s for s in p['streams'] if s['codec_type'] == 'audio')
    if [v['width'], v['height']] != [cfg['width'], cfg['height']]:
        raise ValueError('Unexpected video dimensions')
    if abs(float(p['format']['duration']) - cfg['duration']) > max(.1, 2 / cfg['fps']):
        raise ValueError('Unexpected video duration')
    check = subprocess.run(['ffmpeg', '-v', 'error', '-i', args.video, '-f', 'null', '-'], capture_output=True, check=True)
    if check.stderr:
        raise ValueError(check.stderr.decode(errors='replace'))
    report = {'full_decode': 'passed', 'timing_bounds': 'passed', 'duration': p['format']['duration'],
              'resolution': [v['width'], v['height']], 'words': cfg['words'], 'audio_present': True}
    write(args.out, report)
    print(json.dumps(report), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('transcribe')
    for name in ['audio', 'model', 'out']:
        p.add_argument('--' + name, required=True)
    p.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    p.add_argument('--compute-type'); p.add_argument('--language'); p.add_argument('--dll-dir')
    p.set_defaults(func=transcribe)
    p = sub.add_parser('align')
    for name in ['audio', 'asr', 'out']:
        p.add_argument('--' + name, required=True)
    p.add_argument('--model-dir'); p.add_argument('--align-model'); p.add_argument('--replacements')
    p.add_argument('--language'); p.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    p.set_defaults(func=align)
    p = sub.add_parser('compile')
    for name in ['timeline', 'font-file', 'out']:
        p.add_argument('--' + name, required=True)
    p.add_argument('--duration', type=float); p.add_argument('--font', default='Times New Roman')
    for name, default in [('width', 1920), ('height', 1080), ('fps', 30)]:
        p.add_argument('--' + name, type=int, default=default)
    for name, default in [('font-size', 62), ('x', 360), ('top', 852), ('line-height', 66),
                          ('line-width', 1160), ('scroll', .3), ('offset', 0)]:
        p.add_argument('--' + name, type=float, default=default)
    p.set_defaults(func=compile_ass)
    p = sub.add_parser('render')
    p.add_argument('--video'); p.add_argument('--audio')
    p.add_argument('--compiled', required=True); p.add_argument('--output', required=True)
    p.set_defaults(func=render)
    p = sub.add_parser('verify')
    for name in ['video', 'compiled', 'out']:
        p.add_argument('--' + name, required=True)
    p.set_defaults(func=verify)
    args = parser.parse_args()
    if getattr(args, 'fps', 30) <= 0 or getattr(args, 'fps', 30) > 60:
        parser.error('ASS compiler supports frame rates from 1 to 60')
    args.func(args)


if __name__ == '__main__':
    main()
