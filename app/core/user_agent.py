from user_agents import parse as ua_parse


def parse_user_agent(ua_string: str) -> tuple[str, str, str]:
    """Parse a User-Agent string into (device_type, browser, os)."""
    try:
        ua = ua_parse(ua_string)

        if ua.is_mobile:
            device_type = "mobile"
        elif ua.is_tablet:
            device_type = "tablet"
        elif ua.is_pc:
            device_type = "desktop"
        elif ua.is_bot:
            device_type = "bot"
        else:
            device_type = "unknown"

        browser = ua.browser.family or "unknown"
        os_name = ua.os.family or "unknown"

        return device_type, browser, os_name
    except Exception:
        return "unknown", "unknown", "unknown"
