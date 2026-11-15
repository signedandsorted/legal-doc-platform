import os
import httpx

# URL of the Ollama API inside the Docker network
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/generate")

def call_ollama(prompt: str, system: str = "You are a UK solicitor.") -> str:
    """Send a prompt to the local Ollama model and return the generated text.

    The function uses the Ollama HTTP API with the model specified in the
    `OLLAMA_MODEL` environment variable (defaults to `llama‑2‑13b‑chat‑qa`).
    """
    model = os.getenv("OLLAMA_MODEL", "llama-2-13b-chat-qa")
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": False,
    }
    resp = httpx.post(OLLAMA_URL, json=payload, timeout=30.0)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "")
