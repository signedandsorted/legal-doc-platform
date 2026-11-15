from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel
from .ollama_client import call_ollama
from .stripe_client import create_checkout_session
import os
import json

router = APIRouter()

class DraftRequest(BaseModel):
    data: dict
    service: str  # "will", "poa", "probate"

@router.post("/draft/{service}")
async def create_draft(service: str, req: DraftRequest):
    if service not in {"will", "poa", "probate"}:
        raise HTTPException(status_code=400, detail="Invalid service")

    # Load the appropriate prompt file
    # Map service to prompt file name
    prompt_map = {
        "will": "will_draft.txt",
        "poa": "poa_property.txt",  # could be extended to health variant
        "probate": "probate_form_fill.txt",
    }
    prompt_file = prompt_map.get(service)
    prompt_path = os.path.join(os.path.dirname(__file__), "..", "..", "prompts", prompt_file)
    try:
        with open(prompt_path, "r") as f:
            prompt_template = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prompt load error: {e}")

    # Insert the JSON data into the prompt (simple insertion)
    # The LLM expects a JSON block; we just append it.
    prompt = f"{prompt_template}\n\nClient data:\n{json.dumps(req.data, indent=2)}"
    try:
        result_text = call_ollama(prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # In a real system we would convert markdown to PDF; here we return the raw text.
    return {"status": "draft created", "service": service, "content": result_text}

# Stripe payment endpoints (placeholders)
class PaymentCreateRequest(BaseModel):
    service: str

@router.post("/payments/create-session")
async def create_payment_session(req: PaymentCreateRequest):
    # Example pricing (in GBP pence). Adjust as needed.
    price_map = {"will": 1999, "poa": 1499, "bundle": 2999}
    amount = price_map.get(req.service, 1999)
    try:
        url = create_checkout_session(service=req.service, amount_cents=amount)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {e}")
    return {"url": url}

@router.post("/webhook/stripe")
async def stripe_webhook():
    # Verify signature, update payment status, unlock document
    return {"status": "ok"}

# Video upload placeholder
@router.post("/capacity/video/upload")
async def upload_video(file: UploadFile = File(...)):
    # Store the uploaded video in the shared media directory
    media_dir = os.getenv("MEDIA_DIR", os.path.expanduser("~/.openclaw/media"))
    os.makedirs(media_dir, exist_ok=True)
    dest_path = os.path.join(media_dir, file.filename)
    with open(dest_path, "wb") as out:
        content = await file.read()
        out.write(content)
    return {"status": "uploaded", "path": dest_path}
