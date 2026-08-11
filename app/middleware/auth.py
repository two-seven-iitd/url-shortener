from fastapi import Header, HTTPException

from app.db import repository as db


async def get_api_key(x_api_key: str = Header(...)) -> dict:
    """Dependency that validates the API key."""
    key_record = await db.get_api_key(x_api_key)
    if not key_record or not key_record["is_active"]:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return key_record
