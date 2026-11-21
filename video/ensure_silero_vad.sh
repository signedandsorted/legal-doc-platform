#!/usr/bin/env bash
# ensure_silero_vad.sh — pre-install / cache Silero VAD for OpenVoice se_extractor
# Run once (or after env rebuilds) before male video renders that use OpenVoice.
set -euo pipefail

TOOLS="${VIDEO_TOOLS:-$HOME/video-tools}"
PY="$TOOLS/openvoice-env/bin/python"
CACHE="$HOME/.cache/torch/hub"

if [[ ! -x "$PY" ]]; then
  echo "ERROR: OpenVoice Python not found at $PY"
  echo "Run the OpenVoice setup first."
  exit 1
fi

mkdir -p "$CACHE"
cd "$CACHE"

# Prefer pinned v4.0 (widely compatible with older OpenVoice se_extractor)
if [[ ! -d snakers4_silero-vad_v4.0 ]]; then
  echo "Downloading Silero VAD v4.0..."
  curl -fsSL -o v4.0.zip https://github.com/snakers4/silero-vad/archive/refs/tags/v4.0.zip
  unzip -q v4.0.zip
  mv silero-vad-4.0 snakers4_silero-vad_v4.0
  rm -f v4.0.zip
fi

# Soft-link the name torch.hub sometimes expects
ln -sfn snakers4_silero-vad_v4.0 snakers4_silero-vad_master || true

# Also install the pip package into the OpenVoice env
"$PY" -m pip install -q --upgrade "silero-vad[audio]" || true

# Smoke test
"$PY" - <<'PY'
import torch
torch.set_num_threads(1)
try:
    model, utils = torch.hub.load(
        repo_or_dir="snakers4/silero-vad:v4.0",
        model="silero_vad",
        force_reload=False,
    )
    print("Silero VAD v4.0 (torch.hub) OK")
except Exception as e:
    print(f"torch.hub fallback: {e}")
    from silero_vad import load_silero_vad
    load_silero_vad()
    print("silero-vad pip package OK")
PY

echo "ensure_silero_vad.sh done — OpenVoice VAD ready"
