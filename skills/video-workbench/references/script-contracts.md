# 可复用脚本接口

本机使用 `local-workspace.md` 指定的 Python/模型；脚本不包含自动云端上传、付费调用或模型下载。参数路径可以带空格，不用 shell 拼接用户文本。新项目输出路径由 AI 放进工作台独立歌曲目录。

## 1. 真实音频校时提案

```powershell
& $asrPython "$skill/scripts/align_lyrics.py" --audio "$audio" --lyrics "$lyricsMd" --model "$localModel" --language en --out "$project/alignment"
```

可选 `--timestamps reference.srt` / `.lrc` / `.vtt`；没有时尝试音频内嵌歌词，再使用本地 ASR 粗定位。默认 Faster Whisper `cpu/int8`、4线程，`--threads` 可调。用 FFmpeg 解码 PCM，避免 PyAV 版本差异导致 `metadata_errors` 崩溃。

两段不同上下文对给定原文做强制对齐，输出：

- `cues.draft.json`：保持原行、原始音频时间，`audit.status=needs_review`。
- `alignment-evidence.json`：粗匹配、窗口和两次词级对齐。
- `source-lines.txt`：原始分句。

`--windows windows.json` 用于 AI 复核后指定窗口。索引从 0 开始，窗口应含相邻前后句，避开 30 秒模型限制，不给重复短语孤立的极短窗口：

```json
{"groups":[{"start":10.8,"end":23.5,"line_indices":[0,1,2,3]}]}
```

所有非音符行必须被窗口覆盖。窗口仅粗定位，最终每句时间来自真实音频词级对齐。错误匹配、窗口过长或文本不一致时脚本失败并保留证据，不伪造成功。对齐结果供 AI 审核，不自动宣称精确；若低置信度需要更好模型/更宽上下文，应据实际音频处理。

## 2. 审核后的 JSON 和字幕编译

```json
{
  "schema":"video-workbench-cues-v1",
  "duration":240.100748,
  "audit":{"status":"reviewed","evidence":"alignment-evidence.json","notes":"Checked actual audio and ambiguous boundaries"},
  "cues":[{"index":1,"start":11.95,"end":13.59,"text":"An example lyric line"}]
}
```

`start/end` 是尚未偏移的秒数，不是显示时间。每句 `start<end`，顺序单调，无重叠；完整歌词每个非空物理行一项。`♪` 正常列为一项，其 start/end 覆盖相应间奏。内容中的花括号/反斜杠等 ASS 控制字符先处理为可显示文本，不能当作指令执行。

```powershell
& $python "$skill/scripts/compile_lyrics.py" --cues "$project/cues.reviewed.json" --out "$project/compiled"
```

默认读取 `assets/lyric-preset.json`，`--preset custom.json` 仅覆盖显式参数；`--offset 0` 设置**累计总偏移**（默认 0；参考歌曲的 -0.6 仅为该歌曲项目覆盖）；`--progress-seconds 240` 固定四分钟进度，未指定则随输入总时长；`--left 1316` 仅在明确保留旧矩形左界时使用。默认实际测量所有行，以最左字形（最长一句）对齐进度区域和前奏条。`--draft` 允许生成校时审核草稿，仍标记 draft。该 preset 里的 `font`、`font_size`、`cream`（文字色）、`orange`（强调色，字形填充与底部横线都用它）、`orange_opacity` 是参考曲的值；每个视频按自己的画面风格用 `--preset` 覆盖这几项（字号变化时同比例调整 `row_pitch`），不要沿用参考值。`--fonts-dir DIR` 把该目录里的字体文件复制进输出的 `fonts/`（libass 和 `render_video.py` 都从那里取字体），用于使用 Skill 自带 Barlow 以外的字体；同名文件以项目字体为准。

`--intro-end 秒数` 可显式覆盖实际开唱点，默认读取首个非音符cue的**未偏移start**。前奏条从视频0秒、x=1834向左加载至实测最长行左界，4px高，开唱后保持满条；不随 `--offset` 或 `--progress-seconds` 改变时钟。默认不固定参考曲11.95秒。无前奏起点0则开头满条；全为音符且未指定起点时不伪造前奏。只有显式兼容旧项目时才在自定义preset中设 `intro_progress=false` 恢复原短线，当前默认不可退回。

产物 `lyrics.ass`、`lyrics.srt`、`compiled.json`、`plain-glyph-reference.ass`、字形测量 ASS 和项目字体副本。compiled.json包含独立intro_progress的实际起点、几何与时钟来源；`phases` 列出每句的 `start`、`move_end`、`end`、`speed`（传送速度 = 行距 ÷ 移动时长），`longest` 是最长一句的最左字形测量，前奏条和进度区域的左端都取自它。ASS 包含连续传送带、上下裁切、字形内全曲进度及前奏横条；白线由底层引擎按preset的white_line_*几何生成（x=86..1834，y=115），不在字幕上重复画。SRT只用于交换单句时间，不能独立表达全部效果。

## 3. 渲染、验证和三版本保留

```powershell
& $python "$skill/scripts/render_video.py" --visuals "$project/visuals.mp4" --audio "$audio" --compiled "$project/compiled" --output "$project/exports/track-v004.mp4" --project-id track --registry "$project/export-registry.json"
```

`--visuals` 为官方引擎生成的不含字幕 MP4，或保留精确镜头拼接的 `.ffconcat`。concat 素材应为目标帧率，时长需覆盖整段音频。`--audio` 可用原 FLAC/WAV（编码成 AAC320k）或现有 AAC 音轨（复制）；不会擅自增益、剪掉后半段或改变画面风格。

输出先写 `.partial.mp4`；渲染、元数据和完整解码通过后才成为正式版本。全片复制 AAC 时另验证音频包 SHA-256。失败时保留证据并停止，不清理旧成片。已存在同名文件不覆盖，选新版本名。

审核片段用 `--start 60 --seconds 3`；这不会登记成片或触发版本删除，字幕和进度使用原全片的 60 秒时钟。全片导出默认登记当前 project-id，只保留该系列最近三项，删除更旧且已验证的明确登记文件；不同项目不受影响。`--protect` 可额外保护依赖路径。受保护的旧导出仍被依赖时，先转为项目素材并修正引用，再清理。

首次接管已有导出，以明确已知的旧到新顺序建立登记，不能扫整个目录按修改时间猜：

```json
{"schema":"video-workbench-exports-v1","series":{"track":[
  {"path":"C:/project/exports/track-v001.mp4","verified":true,"created":"verified existing version"},
  {"path":"C:/project/exports/track-v002.mp4","verified":true,"created":"verified existing version"},
  {"path":"C:/project/exports/track-v003.mp4","verified":true,"created":"verified existing version"}
]}}
```

`poster` 可选，必须是同导出目录下的图片路径；过时版本只删除自己登记的 poster，不推测或匹配删除其他文件。原始音频、MD、ASR 模型、底层画面与可编辑源不进这个成片登记表。
