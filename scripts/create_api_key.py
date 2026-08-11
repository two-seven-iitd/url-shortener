"""Create an API key for local testing.

Usage:
    python scripts/create_api_key.py "My App" [rate_limit_per_minute]
"""
import asyncio
import secrets
import sys

import asyncpg

sys.path.insert(0, ".")
from app.config import settings  # noqa: E402


async def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "Test"
    rate_limit = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    key = f"sk_live_{secrets.token_hex(16)}"

    conn = await asyncpg.connect(settings.database_url)
    try:
        await conn.execute(
            "INSERT INTO api_keys (key, name, rate_limit_per_minute) VALUES ($1, $2, $3)",
            key, name, rate_limit,
        )
    finally:
        await conn.close()

    print(f"Created API key for '{name}': {key}")


if __name__ == "__main__":
    asyncio.run(main())
