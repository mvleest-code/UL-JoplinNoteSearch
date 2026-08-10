"""Small, dependency-free helpers for the Joplin integration."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


SNIPPET_MAX_LENGTH = 120


def sanitize_url(url: str) -> str:
    """Return a log-safe URL with every token query value masked."""
    if not url:
        return url

    parts = urlsplit(url)
    query = [
        (key, "***" if key.lower() == "token" else value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def normalize_host(host: str, default_host: str) -> str:
    """Validate and normalize a configured Web Clipper API host."""
    candidate = (host or default_host).strip().rstrip("/")
    parts = urlsplit(candidate)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("Joplin host must be a complete http:// or https:// URL")
    if parts.username or parts.password:
        raise ValueError("Joplin host must not contain embedded credentials")
    if parts.query or parts.fragment:
        raise ValueError("Joplin host must not contain a query string or fragment")
    return candidate


def format_snippet(text: str, max_length: int = SNIPPET_MAX_LENGTH) -> str:
    """Collapse whitespace and keep result descriptions compact."""
    normalized = " ".join((text or "").split())
    if len(normalized) > max_length:
        normalized = normalized[: max_length - 3].rstrip() + "..."
    return normalized


def parse_note_payload(raw_text: str) -> tuple[str, str]:
    """Parse the ``Title::Body`` shorthand used when creating a note."""
    parts = raw_text.split("::", 1)
    title = parts[0].strip() if parts else ""
    body = parts[1].strip() if len(parts) > 1 else ""
    return title or "Untitled note", body
