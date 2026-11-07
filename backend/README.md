# GEO MIND AI API — v0.1

## Run locally
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Health check: `http://127.0.0.1:8000/health`

This is an API scaffold, not a connected AI agent yet. Do not expose it publicly with wildcard CORS or without authentication/rate limits. Do not put model-provider secrets in the frontend.
