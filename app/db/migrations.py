import asyncpg

# First base62 number that encodes to a 4-character code (62^3 + 62^2 + 62).
MIN_ID_FOR_4_CHAR_CODE = 238328

CREATE_API_KEYS_SQL = """
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(100),
    rate_limit_per_minute INT DEFAULT 60,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
"""

CREATE_URLS_SQL = """
CREATE TABLE IF NOT EXISTS urls (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    original_url TEXT NOT NULL,
    api_key_id INT REFERENCES api_keys(id),
    clicks_count INT DEFAULT 0,
    is_custom_alias BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
"""

CREATE_URLS_INDEXES_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_urls_code ON urls(code);
CREATE INDEX IF NOT EXISTS idx_urls_created ON urls(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_urls_expires ON urls(expires_at) WHERE expires_at IS NOT NULL;
"""

CREATE_CLICKS_SQL = """
CREATE TABLE IF NOT EXISTS clicks (
    id BIGSERIAL PRIMARY KEY,
    url_id BIGINT REFERENCES urls(id) NOT NULL,
    clicked_at TIMESTAMP DEFAULT NOW(),
    ip_address INET,
    country VARCHAR(2),
    city VARCHAR(100),
    device_type VARCHAR(10),
    browser VARCHAR(50),
    os VARCHAR(50),
    referrer TEXT
);
"""

CREATE_CLICKS_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_clicks_url_id ON clicks(url_id);
CREATE INDEX IF NOT EXISTS idx_clicks_time ON clicks(clicked_at DESC);
CREATE INDEX IF NOT EXISTS idx_clicks_country ON clicks(url_id, country);
"""


async def run_migrations(pool: asyncpg.Pool) -> None:
    """Create tables/indexes if they don't exist, and ensure short codes start at 4 chars."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(CREATE_API_KEYS_SQL)
            await conn.execute(CREATE_URLS_SQL)
            await conn.execute(CREATE_URLS_INDEXES_SQL)
            await conn.execute(CREATE_CLICKS_SQL)
            await conn.execute(CREATE_CLICKS_INDEXES_SQL)

        # Only bump the sequence on a fresh, untouched database — never rewind
        # an existing sequence that's already issuing real IDs.
        seq_row = await conn.fetchrow("SELECT last_value, is_called FROM urls_id_seq")
        if seq_row is not None and not seq_row["is_called"] and seq_row["last_value"] < MIN_ID_FOR_4_CHAR_CODE:
            await conn.execute(f"ALTER SEQUENCE urls_id_seq RESTART WITH {MIN_ID_FOR_4_CHAR_CODE}")
