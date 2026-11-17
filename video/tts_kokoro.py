"""Kokoro TTS (Apache-2.0, runs locally on CPU). Called by render.py inside the TTS environment.
usage: tts_kokoro.py <model.onnx> <voices.bin> <voice> <out_dir> <line1> [<line2> ...]
Writes out_dir/line_NN.wav and prints each line's duration in seconds, one per line."""
import os
import sys

import soundfile as sf
from kokoro_onnx import Kokoro

model, voices, voice, out = sys.argv[1:5]
k = Kokoro(model, voices)
os.makedirs(out, exist_ok=True)
for i, line in enumerate(sys.argv[5:]):
    samples, sr = k.create(line, voice=voice, speed=float(os.environ.get("TTS_SPEED", "0.95")), lang="en-gb")
    sf.write(os.path.join(out, f"line_{i:02d}.wav"), samples, sr)
    print(f"{len(samples) / sr:.3f}", flush=True)
