# 给朋友的 AI：从克隆到成片

目标是复现**字幕视觉规范**，并按新歌曲重新创作画面。你需要本地读写和命令执行能力；不假装网页按钮会自动读 Skill。

## 1. 准备

读根目录 AGENTS、统一 Skill 和相关官方引擎入口。运行 `npm run setup`；确认 `ffmpeg -filters` 有 `ass`、FFmpeg 支持 libx264，确认 Python3.12 和 Node≥22。`npm run doctor` 分别报告引擎、FFmpeg、浏览器与技能位置；配置存在、服务返回200、实际渲染成功是不同检查。

需要本地校时才运行 `npm run setup:alignment` 并显式下载适合语言的模型。安装与模型下载只访问软件来源，不上传音轨。模型、用户数据和输出都位于忽略目录。已有浏览器可通过 `VIDEO_WORKBENCH_BROWSER_PATH` 指向已安装 headless shell；其他机器不能沿用作者的绝对路径。字幕脚本要求 PATH 中有 ffmpeg 和 ffprobe；`FFMPEG_PATH` 仅覆盖工作台按钮使用的 FFmpeg 命令。

Windows 用户可直接运行上述 npm 命令；严格匹配参考音符时确认 Segoe UI Symbol。其他平台可制作同类效果，但补字字体不同时不能承诺音符逐像素相同。

## 2. 接收音频和字幕

在 `projects/<name>/` 建立输入、alignment、compiled、visuals、exports 子目录。ffprobe 检查完整音频。MD每个非空换行一句，记录原文和SHA-256。没有歌词文件时先做音乐/画面分析并索取歌词，不自行补写歌曲歌词。

带时间戳文件（SRT/LRC/VTT）或音频内嵌时间戳仅用来粗定位。文字仍以用户指定的MD为准。用脚本：

```bash
node scripts/python.mjs skills/video-workbench/scripts/align_lyrics.py --audio projects/song/input/song.flac --lyrics projects/song/input/lyrics.md --model .models/base.en --language en --out projects/song/alignment
```

可加 `--timestamps projects/song/input/reference.srt`。没有时间戳时，脚本做本地ASR粗定位，再对给定原文做两段上下文强制对齐。它输出 `needs_review`，不是可以直接冒充精确同步的成品。

逐句复核实际演唱起点和句间停顿，尤其注意0秒/窗口边缘、重复短语、合唱、音符间奏和上下文候选差异。小模型经常把前奏/换气误算成句首；两次结果一致也可能共同出错。必要时扩大上下文、指定 `--windows` 或换更合适的本地模型。保留审核证据，将确认后的文件另存 `cues.reviewed.json` 并设置 `audit.status=reviewed`。

## 3. 生成画面

依实际歌曲建立brief、分镜和节奏/段落图。读官方 `music-to-video` / `hyperframes` / `hyperframes-core`，或用户指定的Remotion对应技能，制作不含字幕的底层画面。可参考 `templates/rock-paper-cut/` 的六组原创矢量剪纸布局；也可完全换成适合歌曲的视觉风格。

模板时长130秒只是示例结构，不是新曲的音乐分析。按新曲重排并替换 YOUR SONG / YOUR ARTIST。最终画面时长必须覆盖全曲；已有项目只改字幕时复用原底层镜头，不重新生成整段动画。

## 4. 固定字幕样式

```bash
node scripts/python.mjs skills/video-workbench/scripts/compile_lyrics.py --cues projects/song/alignment/cues.reviewed.json --out projects/song/compiled
```

默认偏移是0；用户明确要求提前/延后时传 `--offset` 作为累计偏移。**不要默认传-0.6。** 新曲进度默认随实际音频时长，固定四分钟可传 `--progress-seconds 240`。编译器实测字形边缘并将进度左界对齐最长行，不按字符数/Pillow尺寸猜测。

如果行长超过画布，先据用户要求处理，不偷偷换行、缩字或合并句子。字体、40px行距、裁切和字形内进度以仓库preset为准。字形外绝不出现进度矩形，音符也参与遮罩。

## 5. 审核、渲染与版本保留

先出代表性审核片段（`--start 60 --seconds 5`），保留全曲时钟。新风格用户已经确定时不用重复问。检查上下边的半字裁切、橙/白半字边界、历史行、间奏暂停和音符。

```bash
node scripts/python.mjs skills/video-workbench/scripts/render_video.py --visuals projects/song/visuals/base.mp4 --audio projects/song/input/song.flac --compiled projects/song/compiled --output projects/song/exports/song-v001.mp4 --project-id song --registry projects/song/export-registry.json
```

编码失败不清理旧版。正式输出先完整解码和检查时长、尺寸、音轨，再按明确登记顺序保留当前项目最近三版。不要因一个目录里有其他歌曲或原始素材而误删。旧成片仍是画面依赖时先转成素材并改引用。

给用户实际新文件，不只给源代码或旧播放器标签页。说明AI确实完成的音频/画面检查，不声称“装好=运行通过”或“校时草稿=已听完全部”。

## 浏览器工作台

`npm start` 后访问 `http://127.0.0.1:3026`。需要改端口时设置 `VIDEO_WORKBENCH_PORT`、`REMOTION_PORT`、`HYPERFRAMES_PORT`。不要停止别人的服务以抢端口。网页现有按钮针对两个演示项目；每首歌的完整AI制作流程按上面的项目目录执行。
