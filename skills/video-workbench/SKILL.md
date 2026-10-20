---
name: video-workbench
description: Create or edit local videos with Remotion and HyperFrames. Turn audio plus untimed MD/TXT lyrics or timestamped captions into a verified lyric MV using the user's continuous scrolling, glyph-masked progress style. Also retain the integrated general video workflow.
metadata:
  version: "2026-10-19.3"
---

# 视频工作台

这是 Remotion + HyperFrames 的统一入口 Skill。保留官方引擎和官方 Skills，整合本地工作台、素材、预览和渲染。网页按钮直接运行本地程序；是聊天里的 AI 读取本 Skill 后操作工具，网页不会自动读取或执行 Skill。

## 输入音频和字幕后直接制作

用户提供歌曲及 MD/TXT/SRT/LRC/VTT 时，先读 [歌词 MV 流程](references/lyric-workflow.md) 和 [当前字幕样式规范](references/lyric-style.md)。仅有音频而缺歌词时，不自行补写歌曲歌词；继续做画面/音频分析，再索取缺少的歌词。

- MD/TXT **每一个非空物理换行就是一句**，逐行保留文字和顺序，不能按逗号合并或自行拆句。音符 `♪` 也属于文字。
- MD 无时间戳时，AI 根据实际音频对齐并审核；同时提供的带时间戳文件和音频内嵌歌词只作校时参考，以用户指定的分句文件为文字依据。不能按字数平均分配演唱时间。
- 新 MV 画面仍按下方 Remotion / HyperFrames 路由制作；字幕默认严格使用当前最终样式。早期的单句消失、两行合并、0.42 秒阶梯滚动和可见橙色大矩形均已被替代。
- 默认字幕：1920×1080 坐标系，Barlow Black 42，米白 `#F0ECE5`，右对齐 x=1830，**行距 40px**，透明底、无阴影无描边。通用时间偏移默认为 **0 秒**，按实际音频和用户反馈调整，只应用一次。此前提前 0.6 秒仅属于参考歌曲项目，不能套给其他歌曲或用户。
- 整段歌词作为一条刚性传送带持续上移；速度按每句实际演唱时长调整，短换气连续，明显无词间隔暂停。旧句保留，橙线高度处逐渐露出，白线高度处逐渐裁掉，使用空间裁切而非淡出。
- 原橙色进度区域只在歌词及音符的字形内部显示；字孔、行间和字外透明。保留 `#E85D26`、50% 叠色、由下向上增长的进度逻辑。六组参考图案及未来新增的所有画面均在歌词层下方。
- 下方橙线改为**独立的前奏进度条**：从视频0秒、左下原点 `(1834,116)` 向左加载，在实际第一句开唱时到达最长歌词最左字形（参考曲 x=1316），之后保持满条。速度按每首歌实际前奏时长计算，不能固定11.95秒，也不能跟随全曲进度或字幕显示偏移。颜色仍为原橙色，4px高；这是允许显示在字外的独立线条，不属于字形内进度矩形。
- 上方白线两端对称延长：1920宽基准下由 x=110..1810 改成 **x=86..1834**，左右各加24px，中点960不变，左下原点高度965（屏幕y=115）。全部背景场景同步，白线仍在歌词下层，保留原透明度、颗粒及场景过渡；不是只延长右边。
- 新歌曲的内容、总长度、节奏与画面由实际素材决定，不把上一首歌的 62 行、130 秒切点或六组图案硬编码成所有项目的要求。参考曲进度恰为 240 秒；新曲默认随实际总长填满，可显式固定 240 秒。

可复用工具（路径相对本 Skill）：

1. `scripts/align_lyrics.py`：本地音频 + 无时间戳歌词 + 可选时间戳参考 → 原始校时提案和审核标记；不会自动把提案冒充已审核结果。
2. `scripts/compile_lyrics.py`：已审核的逐行时间 JSON → 当前样式 ASS、SRT、传送带状态与字形测量记录。
3. `scripts/render_video.py`：本地引擎画面 + 音轨 + 编译结果 → 验证后的成片，可登记并只保留该项目最近三个版本。

参数及文件格式见 [脚本接口](references/script-contracts.md)。依赖本机 FFmpeg；本地对齐另需 Faster Whisper 和已有模型。Skill 不包含模型、FFmpeg 或 Node 引擎运行时，不代表已经获得云端生成额度。

## 修改现有项目与保留三个版本

先确认用户实际播放的文件和最新版本。只改明确要求的项目与参数；保留原画面、音轨、镜头节奏和既有样式，除非这次明确要求改变它们。字幕编辑优先重新合成独立字幕层，复用已验证的底层画面，不重绘全部动画。

用户要求“再提前 0.2 秒”时，在当前累计偏移上相加，不回到原始版本或重复应用默认偏移。左右边界使用 x，上下高度使用 y；用户称错轴但几何意图明确时，说明解释并按实际方向执行。文字 y 随滚动改变，不声称它有唯一固定 y。

**每个项目只保留最新版、上一版、上上一版共三个成片导出。** 新版生成、解码及内容检查通过后，再清理更旧的该项目导出和对应过时预览；保留原始素材、字幕源、工程和对齐证据。若待删导出还是工程依赖，先归入素材并修正引用。按导出登记顺序保留，禁止按整个文件夹的修改时间随意删其他项目。细则见 [歌词 MV 流程](references/lyric-workflow.md)。

本对话相关要求及被替代版本见 [用户要求记录](references/user-requirements.md)，用于理解继承关系，不能把被替代参数重新启用。

## Resolve the existing project first

Read [local-workspace.md](references/local-workspace.md) for the installed workspace and commands. Open the user's current source before editing because Studio and other sessions can save changes independently.

- Existing Remotion/React source: retain Remotion and read `../remotion-best-practices/SKILL.md` plus the matching domain skill.
- Existing HyperFrames HTML source: retain HyperFrames, read `../hyperframes/SKILL.md` and the matching domain skill.
- Fresh music/lyric/beat-synced video: prefer HyperFrames with `../music-to-video/SKILL.md`, unless the user chose Remotion.
- Fresh React-driven data animation, reusable React video component or Remotion application: use Remotion.
- For other fresh work, choose by requested output using [capabilities.md](references/capabilities.md). Follow an explicit engine choice.
- Source migration is separate from media reuse. Use `remotion-to-hyperframes` only for an explicit source-port request. Do not promise an automatic round trip between the source formats.

## Connect the engines through media

Use a shared brief, storyboard, beat/phrase times, caption timestamps, and local media. Keep source files editable in their native framework. Exchange MP4/WebM/MOV, image sequences, WAV, images, and caption JSON/SRT as appropriate. Copy or stage source media; do not replace the user's original.

The local verified demonstration renders the Remotion project to MP4, stages that file with its SHA-256 in `bridge-manifest.json`, and places it in a HyperFrames timeline. It is an example of media interoperability, not a source-code converter.

Keep the clocks separate: Remotion uses `useCurrentFrame()` and its deterministic React APIs; HyperFrames uses the seekable runtime and timeline described by `hyperframes-core`. Read the active engine's rules before authoring; don't transfer engine-specific restrictions or syntax blindly.

## Use the complete skill library progressively

The repository setup installs all 33 pinned official skills and their supporting files; verify their presence before claiming they are ready. Consult the capability map, then read the selected skill and its relevant references in full. The index is not a substitute for a workflow's detailed instructions. Avoid loading unrelated workflows into a narrow edit.

For MV work, establish the music source and desired visual style. Analyze the actual track before choosing cuts. Prefer phrases and energy on calm music, and beat anchors on genuinely rhythmic music. Verify vocal timing before presenting lyrics as synchronized. Offer a short representative excerpt when the style is undecided.

## Verify the actual deliverable

Run the selected engine's checks; inspect frames that contain imported video and confirm audio in the exported file. A working skill installation, a passing doctor report, a successful render, and user approval of the visual result are different claims. Report only the state actually verified.

Installed skills do not supply credentials, cloud credit, video-generation models, or source assets. Use the user's authorized services when required. Installing these skills does not authorize publishing, cloud uploads, external feedback, messages, or paid generation; follow the user's instructions and the host's authorization rules. Keep the local integration's telemetry-disabled environment when using its wrappers.
