from fastapi import HTTPException, Query
import os
import secrets

API_KEY = os.getenv("OEBB_SCOTTY_PROXY_API_KEY")

async def handle_api_key(api_key: str | None = Query(default=None, alias="apiKey")):
    if API_KEY is None:
        raise HTTPException(status_code=500, detail="Server API key not configured")
    if not api_key or not secrets.compare_digest(api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API Key")