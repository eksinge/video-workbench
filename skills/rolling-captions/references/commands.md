# 命令与数据

优先复用已经安装且实际导入成功的 Python 环境；识别和对齐可用不同 Python。识别需 faster-whisper，对齐需兼容的 WhisperX / PyTorch / torchaudio，编译需 Pillow；导出和校验需 PATH 中的 FFmpeg（libass / libx264）与 ffprobe。缺包时在独立环境补齐，不升级用户的其他工具。

下列占位路径必须替换成实际路径；PowerShell 中 Python 路径有空格时用 `& "路径/python.exe"` 调用。

```text
python scripts/rolling_captions.py transcribe --audio input.flac --model /existing/faster-whisper-large-v3 --out work/asr.json --device cuda --language en
python scripts/rolling_captions.py align --audio input.flac --asr work/asr.json --model-dir /existing/torch-checkpoints --out work/aligned.json --device cuda
python scripts/rolling_captions.py compile --timeline work/aligned.json --duration 63.18 --font-file /system/fonts/times.ttf --out compiled
python scripts/rolling_captions.py render --video input.mp4 --audio input.flac --compiled compiled --output exports/preview.mp4
python scripts/rolling_captions.py verify --video exports/preview.mp4 --compiled compiled --out work/verification.json
```

`transcribe --model` 必须是已有 CTranslate2 模型文件夹（含 model.bin）。`--dll-dir` 可在进程内加载已有 torch/lib 的 CUDA DLL，不改系统配置。CUDA 不可用时显式选 CPU，不换成其他模型。

`align --model-dir` 英文路径必须包含 `wav2vec2_fairseq_base_ls960_asr_ls960.pth`；缺少时脚本停止，不下载。其他语言可传 `--align-model /existing/local-hf-model --language zh`，并确认本地模型可被 WhisperX 读取。对非英文分词与字体另行检查，不声称英文默认已覆盖所有语言。可加 `--replacements replacements.json`：例如任务明确确认的 `{ "4.30": "four thirty" }`。替换只用于对齐文本并写入证据；显示文字需要还原时，在修正的 timeline 中保留原文与映射。

`compile --help` 可调画布、字号、x/top、行距、行宽、滚动秒数、累计显示偏移。几何参数使用 1920×1080 参考坐标，按实际宽高缩放。`--font` 与 `--font-file` 必须对应；渲染主机仍需安装该字体。长词超出行宽时停止，调整字号或行宽后重编译。非拉丁文及复杂文字需确认实际字体和字形宽度。

只有音频时，`render` 不传 `--video` 会生成黑色底层画面，字幕层仍透明。独立音频与视频先核对同步；`--audio` 覆盖视频原音轨，不传则复用视频音轨。较长音频配较短视频会暂停最后一帧补齐，应提前确认这符合任务。

## 词级 JSON

`compile` 接受本 skill 的 `words`、WhisperX 的 `word_segments`，或含 `segments[].words` 的 JSON：

```json
{"duration": 2.4, "words": [
  {"word": "Hello", "start": 0.12, "end": 0.48, "score": 0.93},
  {"word": "world.", "start": 0.55, "end": 1.02, "score": 0.91}
]}
```

满足 `0 <= start < end <= duration`，顺序正确且相邻词不重叠。未对齐的词不能删除后伪装全文完整。修正保留证据；低分不是错误率，高分也不等于文字正确。

输出：`captions.ass`、`words.srt`、`words.csv`、`timeline.json`、`compile-report.json`。ASS 不含背景矩形、黄色高亮、描边或阴影；词起点取下一显示帧，滚动是 smoothstep 每帧采样，窗口硬裁切。

先用实际素材验证完整链路，检查困难位置。样式编辑可直接使用既有时间轴，避免重复识别。长素材先导出代表片段，全文听审与自动技术检查分别报告。
