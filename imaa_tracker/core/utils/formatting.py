"""Display formatting helpers."""


def format_minutes(minutes: int) -> str:
    """Format minutes as H:MM or '0 min'"""
    if minutes == 0:
        return "0 min"
    # if minutes < 60:
    #     return f"{minutes} min"
    h = int(minutes // 60)
    m = int(minutes % 60)
    return f"{h}:{m:02}"


def format_duration_str(minutes: int) -> str:
    """Format minutes as 'H hrs MM min' or 'MM min'"""
    if minutes == 0:
        return "0 min"
    if minutes < 60:
        return f"{minutes:02} min"
    h = int(minutes // 60)
    m = int(minutes % 60)
    return f"{h}hrs {m:02}min"
