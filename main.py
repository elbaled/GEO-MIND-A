from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os

app = FastAPI(title="GEO MIND AI API", version="0.1.0")

# During development, allow the static frontend. Restrict this list before production.
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)

@app.get("/health")
def health():
    return {"status": "ok", "service": "geo-mind-ai", "version": "0.1.0"}

@app.post("/api/chat")
def chat(payload: ChatRequest):
    # Safe starter response: no model is connected yet.
    # Next step: connect an open-weight model through a private server-side provider.
    return {
        "reply": (
            "وصل طلبك إلى GEO MIND AI API بنجاح. "
            "لكن نموذج اللغة لم يتم ربطه بعد. "
            "المرحلة التالية هي إعداد مزود النموذج على الخادم، "
            "ثم إضافة الذاكرة والأدوات المتخصصة."
        ),
        "model_connected": False
    }
