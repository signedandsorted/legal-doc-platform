#!/usr/bin/env python3
"""Render every step video for free on our own server with open-source tools.

  voice:  Kokoro-82M TTS (Apache-2.0), British English voice 'bf_emma'      -> or Josh's own recordings
  face:   presenter photo generated locally with FLUX.1-schnell (Apache-2.0) in ComfyUI
  motion: SadTalker (Apache-2.0) audio-driven talking head, run on the server GPU (ROCm)
  edit:   ffmpeg (title, captions file, poster, loudness, web encoding)

No paid services. Output: static/videos/<id>.mp4, <id>.vtt (captions) and <id>.jpg (poster).

Swap in Josh's voice: record each script in video/RECORDING_SCRIPT.md as video/voice/josh/<id>.wav
(any sample rate, mono or stereo) and run:  render.py --voice-dir video/voice/josh
Any video without a recording falls back to the TTS voice, so he can do them a few at a time.

Usage: render.py [--only id1,id2] [--force] [--voice bf_emma] [--voice-dir DIR]
Env:   VIDEO_TOOLS (default ~/video-tools) holding env/, tts-env/, SadTalker/, models/kokoro/, presenter.png
The script pauses itself during Josh's no-heavy-work windows (11:50-12:40 and 14:50-15:40 US Eastern).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "static" / "videos"
TOOLS = Path(os.environ.get("VIDEO_TOOLS", Path.home() / "video-tools"))
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BLACKOUTS = [((11, 50), (12, 40)), ((14, 50), (15, 40))]
ET = ZoneInfo("America/New_York")
GAP = 0.35  # seconds of silence between sentences
LEAD = 0.5


def wait_for_window():
    while True:
        now = datetime.now(ET)
        for (h1, m1), (h2, m2) in BLACKOUTS:
            start, end = now.replace(hour=h1, minute=m1, second=0), now.replace(hour=h2, minute=m2, second=0)
            # do not start a ~4 minute job just before a window either
            if start - timedelta(minutes=6) <= now < end:
                secs = (end - now).total_seconds() + 30
                print(f"[pause] no-heavy-work window until {end:%H:%M} ET; sleeping {int(secs)}s", flush=True)
                time.sleep(secs)
                break
        else:
            return


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:])
        raise SystemExit(f"command failed: {cmd[0]} ({r.returncode})")
    return r.stdout


def wav_seconds(p: Path) -> float:
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)])
    return float(out.strip())


def vtt_time(t: float) -> str:
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def narration(vid: str, lines: list[str], work: Path, voice: str, voice_dir: Path | None) -> tuple[Path, list[tuple[float, float, str]], str]:
    audio = work / "narration.wav"
    if voice_dir and (voice_dir / f"{vid}.wav").exists():
        # Josh's own recording: captions are spread over the recording in proportion to words.
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(voice_dir / f"{vid}.wav"), "-af", f"adelay={int(LEAD * 1000)}:all=1,loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "24000", "-ac", "1", str(audio)])
        total = wav_seconds(audio) - LEAD
        words = [len(l.split()) for l in lines]
        cues, t = [], LEAD
        for l, w in zip(lines, words):
            d = total * w / sum(words)
            cues.append((t, t + d, l))
            t += d
        return audio, cues, "recorded"
    tts_dir = work / "tts"
    durs = run([str(TOOLS / "tts-env/bin/python"), str(ROOT / "video/tts_kokoro.py"), str(TOOLS / "models/kokoro/kokoro-v1.0.onnx"),
                str(TOOLS / "models/kokoro/voices-v1.0.bin"), voice, str(tts_dir), *lines]).split()
    durs = [float(d) for d in durs]
    parts, cues, t = [], [], LEAD
    concat = work / "concat.txt"
    silence = work / "gap.wav"
    lead = work / "lead.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(GAP), str(silence)])
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(LEAD), str(lead)])
    parts.append(lead)
    for i, (line, d) in enumerate(zip(lines, durs)):
        parts += [tts_dir / f"line_{i:02d}.wav", silence]
        cues.append((t, t + d, line))
        t += d + GAP
    concat.write_text("".join(f"file '{p}'\n" for p in parts))
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "24000", "-ac", "1", str(audio)])
    return audio, cues, f"tts:{voice}"


def talking_head(audio: Path, work: Path) -> Path:
    res = work / "sadtalker"
    shutil.rmtree(res, ignore_errors=True)
    env = {**os.environ, "PYTORCH_ALLOC_CONF": "expandable_segments:True", "MIOPEN_FIND_MODE": "FAST"}
    run([str(TOOLS / "env/bin/python"), "inference.py", "--driven_audio", str(audio), "--source_image", str(TOOLS / "presenter.png"),
         "--result_dir", str(res), "--still", "--preprocess", "full", "--size", "256", "--batch_size", "1"], cwd=TOOLS / "SadTalker", env=env)
    vids = sorted(res.glob("*.mp4"))
    if not vids:
        raise SystemExit("SadTalker produced no video")
    return vids[-1]


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\u2019").replace("%", "\\%")


def compose(vid: str, title: str, head: Path, audio: Path, cues, work: Path):
    OUT.mkdir(parents=True, exist_ok=True)
    mp4, vtt, jpg = OUT / f"{vid}.mp4", OUT / f"{vid}.vtt", OUT / f"{vid}.jpg"
    # Lower third with the step title for the first 6 seconds, small brand mark throughout.
    vf = (f"scale=960:540:flags=lanczos,unsharp=5:5:0.6,"
          f"drawbox=x=0:y=ih-92:w=iw*0.62:h=60:color=0x14213d@0.82:t=fill:enable='between(t,0.3,6.5)',"
          f"drawtext=fontfile={FONT}:text='{esc(title)}':x=28:y=h-80:fontsize=30:fontcolor=white:enable='between(t,0.3,6.5)',"
          f"drawtext=fontfile={FONT_REG}:text='Signed and Sorted':x=w-tw-22:y=20:fontsize=18:fontcolor=white@0.85:shadowcolor=black@0.4:shadowx=1:shadowy=1")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(head), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-vf", vf,
         "-c:v", "libx264", "-preset", "slow", "-crf", "25", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-ar", "48000",
         "-movflags", "+faststart", "-shortest", str(mp4)])
    run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1.2", "-i", str(mp4), "-frames:v", "1", "-q:v", "4", str(jpg)])
    vtt.write_text("WEBVTT\n\n" + "\n".join(f"{i}\n{vtt_time(a)} --> {vtt_time(b)}\n{t}\n" for i, (a, b, t) in enumerate(cues, 1)))
    return mp4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--voice", default="bf_emma")
    ap.add_argument("--voice-dir", default="")
    args = ap.parse_args()
    scripts = {k: v for k, v in json.loads((ROOT / "video/scripts.json").read_text()).items() if not k.startswith("_")}
    only = [x for x in args.only.split(",") if x]
    voice_dir = Path(args.voice_dir) if args.voice_dir else None
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for vid, s in scripts.items():
        if only and vid not in only:
            continue
        if not args.force and (OUT / f"{vid}.mp4").exists() and manifest.get(vid, {}).get("lines") == s["lines"]:
            print(f"[skip] {vid} (up to date)")
            continue
        wait_for_window()
        t0 = time.time()
        work = TOOLS / "work" / vid
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True)
        audio, cues, voice_used = narration(vid, s["lines"], work, args.voice, voice_dir)
        head = talking_head(audio, work)
        mp4 = compose(vid, s["title"], head, audio, cues, work)
        manifest[vid] = {"title": s["title"], "lines": s["lines"], "voice": voice_used, "seconds": round(wav_seconds(audio), 1),
                         "bytes": mp4.stat().st_size, "rendered": datetime.now(ET).isoformat(timespec="seconds")}
        manifest_path.write_text(json.dumps(manifest, indent=1))
        print(f"[done] {vid}: {manifest[vid]['seconds']}s, {mp4.stat().st_size // 1024} KB, {voice_used}, took {int(time.time() - t0)}s", flush=True)


if __name__ == "__main__":
    main()
