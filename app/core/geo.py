import ipaddress
from pathlib import Path
from typing import Optional

import geoip2.database
import geoip2.errors

from app.config import settings

_reader: Optional[geoip2.database.Reader] = None
_reader_load_attempted = False


def get_geo_reader() -> Optional[geoip2.database.Reader]:
    """Lazily load the GeoLite2 database. Returns None if the file is missing
    (e.g. it hasn't been downloaded yet) instead of crashing the app."""
    global _reader, _reader_load_attempted
    if _reader is None and not _reader_load_attempted:
        _reader_load_attempted = True
        if Path(settings.geoip_db_path).exists():
            _reader = geoip2.database.Reader(settings.geoip_db_path)
    return _reader


def lookup_geo(ip: str) -> tuple[Optional[str], Optional[str]]:
    """Look up country and city from IP address.

    Returns (country_code, city_name) or (None, None) on failure
    (private/loopback IPs, unknown addresses, or a missing GeoIP database).
    """
    try:
        addr = ipaddress.ip_address(ip)
        if addr.is_private or addr.is_loopback:
            return None, None
    except ValueError:
        return None, None

    reader = get_geo_reader()
    if reader is None:
        return None, None

    try:
        response = reader.city(ip)
        return response.country.iso_code, response.city.name
    except (geoip2.errors.AddressNotFoundError, ValueError):
        return None, None
