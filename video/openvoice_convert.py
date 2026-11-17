#!/usr/bin/env python3
"""Convert a narration wav into Josh's cloned tone using OpenVoice (MIT, MyShell).

usage: openvoice_convert.py <reference.wav|.m4a> <src.wav> <out.wav>

Looks for checkpoints under ~/video-tools/models/openvoice and the OpenVoice
checkout under ~/video-tools/OpenVoice. Runs in the openvoice-env interpreter
when called from render.py.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import torch


def to_wav(src: Path, dest: Path) -> None:
    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ac", "1", "-ar", "22050", "-vn", str(dest)],
        check=True,
    )


def find_converter_ckpt(root: Path) -> Path:
    candidates = [
        root / "converter",
        root / "checkpoints_v2" / "converter",
        root / "OpenVoiceV2" / "converter",
    ]
    # shallow walk of first two levels only (no broad find)
    for d in candidates:
        if (d / "config.json").exists() or list(d.glob("*.pth")):
            return d
    for child in root.iterdir() if root.exists() else []:
        if not child.is_dir():
            continue
        if (child / "config.json").exists():
            return child
        conv = child / "converter"
        if (conv / "config.json").exists() or list(conv.glob("*.pth")):
            return conv
    raise SystemExit(f"OpenVoice converter checkpoint not found under {root}")


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    ref, src, out = map(Path, sys.argv[1:])
    tools = Path.home() / "video-tools"
    ov = tools / "OpenVoice"
    if str(ov) not in sys.path:
        sys.path.insert(0, str(ov))
    ckpt_root = tools / "models" / "openvoice"
    with tempfile.TemporaryDirectory(prefix="openvoice-") as td:
        td = Path(td)
        ref_wav = td / "ref.wav"
        src_wav = td / "src.wav"
        to_wav(ref, ref_wav)
        to_wav(src, src_wav)
        # Import after sys.path is set
        from openvoice import se_extractor
        from openvoice.api import ToneColorConverter

        conv_dir = find_converter_ckpt(ckpt_root)
        cfg = conv_dir / "config.json"
        ckpt = None
        for name in ("checkpoint.pth", "converters.pth", "checkpoint_v2.pth"):
            if (conv_dir / name).exists():
                ckpt = conv_dir / name
                break
        if ckpt is None:
            pths = list(conv_dir.glob("*.pth"))
            if not pths:
                raise SystemExit(f"no .pth in {conv_dir}")
            ckpt = pths[0]
        device = "cpu"
        converter = ToneColorConverter(str(cfg), device=device)
        converter.load_ckpt(str(ckpt))
        target_se, _ = se_extractor.get_se(str(ref_wav), converter, vad=True)
        # Source speaker embedding from the Kokoro base narration
        source_se, _ = se_extractor.get_se(str(src_wav), converter, vad=True)
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp_out = td / "out.wav"
        converter.convert(
            audio_src_path=str(src_wav),
            src_se=source_se,
            tgt_se=target_se,
            output_path=str(tmp_out),
            message="@MyShell",
        )
        # loud-norm to match the female path
        import subprocess
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp_out), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "24000", "-ac", "1", str(out)],
            check=True,
        )
    print(f"wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
