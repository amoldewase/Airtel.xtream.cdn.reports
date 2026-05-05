"""Indian number system formatters for Hungama brand."""


def indian_format(n, decimals: int = 2) -> str:
    """Format a number in the Indian system.

    >= 1 Crore (1e7) → "1.23 Cr"
    < 1 Crore        → Indian comma grouping: "12,34,567"

    The Lakh label ("2.34 Lakh") is used as a manual display label in tiles
    and should not be auto-appended by this function (per PRD acceptance test:
    indian_format(1234567) == "12,34,567").
    """
    if n is None:
        return "-"
    n = float(n)
    if n >= 1e7:
        return f"{n / 1e7:,.{decimals}f} Cr"
    return _indian_comma(int(n))


def _indian_comma(n: int) -> str:
    """Render an integer with Indian grouping: 1,23,456."""
    s = str(abs(n))
    sign = "-" if n < 0 else ""
    if len(s) <= 3:
        return sign + s
    # last 3 digits, then groups of 2
    last3 = s[-3:]
    rest = s[:-3]
    groups = []
    while rest:
        groups.append(rest[-2:])
        rest = rest[:-2]
    groups.reverse()
    return sign + ",".join(groups) + "," + last3


def humanize_seconds(secs) -> str:
    """Return duration as H:MM:SS string."""
    secs = int(secs or 0)
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"


def humanize_minutes(secs) -> str:
    """Return duration as a plain minutes value: '16.8 Min' or '2.3 Hrs'."""
    secs = float(secs or 0)
    mins = secs / 60
    if mins < 60:
        return f"{mins:.1f} Min"
    hrs = mins / 60
    return f"{hrs:.2f} Hrs"


def humanize_bytes(b) -> str:
    """Return bytes in human-readable IEC-ish units (B, KB, MB, GB, TB)."""
    b = float(b or 0)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if b < 1024:
            return f"{b:.2f} {unit}"
        b /= 1024
    return f"{b:.2f} EB"


def indian_minutes(seconds) -> str:
    """Return playback seconds formatted as Indian-system minutes label."""
    mins = float(seconds or 0) / 60
    return indian_format(mins) + " min"


def indian_hours(seconds) -> str:
    """Return playback seconds as Indian-system hours label."""
    hrs = float(seconds or 0) / 3600
    return indian_format(hrs) + " hrs"


def format_date(dt) -> str:
    """DD/MM/YYYY from a datetime."""
    return dt.strftime("%d/%m/%Y") if dt else "-"


def format_datetime(dt) -> str:
    """DD/MM/YYYY HH:MM:SS IST from a timezone-aware datetime."""
    return dt.strftime("%d/%m/%Y %H:%M:%S IST") if dt else "-"
