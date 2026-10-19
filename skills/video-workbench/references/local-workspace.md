# Portable workspace layout

Repository root contains `workbench/`, `remotion-studio/`, `templates/rock-paper-cut/`, and `skills/`.

1. Read root `README.md` and `AGENTS.md`.
2. Run `npm run setup` for pinned Node projects, the shared Python environment and original demo audio. `npm run setup:alignment` adds the optional local ASR packages. FFmpeg/ffprobe with libass must already be on PATH.
3. Run `npm run install-skills` to copy the bundled skills into the local agent's skill directory. To avoid overwriting existing skills, the installer asks for an explicit `--replace` flag if files differ.
4. Run `npm start` and open `http://127.0.0.1:3026`. The web UI launches editors and demo renders; the chat AI reads this Skill and makes project-specific lyric MVs.
5. Python is `.venv/Scripts/python.exe` on Windows, `.venv/bin/python` elsewhere. The scripts take explicit paths; do not reuse another user's private absolute paths.
6. Local alignment models go in ignored `.models/`; use `scripts/download-model.py` for an explicitly selected model. Audio stays local. English `base.en` provides draft positions only; choose an appropriate multilingual model for other languages and audit actual audio.
7. Fresh projects belong under ignored `projects/<name>/`, final exports in that project's `exports/`. Keep the latest three verified exports per project.

The original reference was Windows with Barlow Black and Segoe UI Symbol, FFmpeg9/libass and 1920×1080. Barlow is bundled with its OFL license; Segoe UI Symbol comes with Windows. Check symbol support before claiming identical glyph output on another platform.

The public preset has **zero subtitle offset**. -0.6 seconds was a correction for the original song only. Choose each new song's offset from actual audio/user feedback.
