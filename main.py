
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from logging.handlers import TimedRotatingFileHandler

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction


ICON_PATH = "images/icon.png"
SEARCH_LIMIT = 10
TIMEOUT_SECONDS = 3
SNIPPET_MAX_LENGTH = 120
DEFAULT_HOST = "http://127.0.0.1:41184"


DEBUG_LOG = Path(__file__).with_name("debug.log")
_LOGGER = None


def _sanitize_url(url: str) -> str:
    if not url:
        return url
    if "token=" not in url:
        return url
    prefix, rest = url.split("token=", 1)
    token_tail = rest.split("&", 1)
    masked = "***"
    if len(token_tail) == 1:
        return f"{prefix}token={masked}"
    return f"{prefix}token={masked}&{token_tail[1]}"


def _get_logger():
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    try:
        DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
        handler = TimedRotatingFileHandler(
            str(DEBUG_LOG),
            when="M",
            interval=30,
            backupCount=5,
            encoding="utf-8",
        )
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter(
            fmt='{"time":"%(asctime)s","payload":%(message)s}',
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        ))
        handler.converter = time.gmtime

        logger = logging.getLogger("joplin_note_search")
        logger.setLevel(logging.INFO)
        logger.propagate = False

        for existing in list(logger.handlers):
            logger.removeHandler(existing)
            try:
                existing.close()
            except Exception:
                pass

        logger.addHandler(handler)

        _LOGGER = logger
        return _LOGGER
    except Exception as exc:
        print(f"[logging setup failed] {exc}", file=sys.stderr)
        return None


def _log(message):
    try:
        logger = _get_logger()
        if logger:
            payload = message if isinstance(message, dict) else {"message": message}
            logger.info(json.dumps(payload, separators=(",", ":")))
    except Exception as exc:
        print(f"[logging failed] {exc}", file=sys.stderr)


def _log_event(event, **fields):
    payload = {"event": event}
    if fields:
        payload.update(fields)
    _log(payload)


_log_event("module_loaded")


def _format_snippet(text):
    normalized = " ".join((text or "").split())
    if len(normalized) > SNIPPET_MAX_LENGTH:
        normalized = normalized[: SNIPPET_MAX_LENGTH - 1].rstrip() + "..."
    return normalized


def _fetch_json(url, *, method="GET", payload=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    _log_event("fetch", method=method, url=_sanitize_url(url))
    request = Request(url, data=data, headers=headers, method=method)
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def _search_notes(host, token, query):
    params = urlencode({
        "query": query,
        "token": token,
        "limit": SEARCH_LIMIT,
        "type": "note",
    })
    url = f"{host}/search?{params}"
    _log_event("search_notes", query_length=len(query), host=host)
    return _fetch_json(url).get("items", [])


def _create_note(host, token, title, body):
    params = urlencode({"token": token})
    payload = {"title": title}
    if body:
        payload["body"] = body
    url = f"{host}/notes?{params}"
    _log_event("create_note_request", host=host, title=title, body_length=len(body))
    return _fetch_json(url, method="POST", payload=payload)


def _execute_command(host, token, command_type, **kwargs):
    params = urlencode({"token": token})
    payload = {"type": command_type, **kwargs}
    url = f"{host}/commands?{params}"
    redacted_kwargs = dict(kwargs)
    if "token" in redacted_kwargs:
        redacted_kwargs["token"] = "***"
    _log_event("command_request", command=command_type, details=redacted_kwargs)
    return _fetch_json(url, method="POST", payload=payload)


def _open_note(host, token, note_id):
    return _execute_command(host, token, "openNote", noteId=note_id)


def _open_note_url(note_id):
    url = f"joplin://x-callback-url/openNote?id={note_id}"
    _log_event("fallback_open_url", url=url)
    try:
        subprocess.Popen(["xdg-open", url])
    except Exception as exc:
        _log_event("fallback_open_failed", error=str(exc))
        return OpenUrlAction(url)
    return HideWindowAction()


def _parse_note_payload(raw_text):
    parts = raw_text.split("::", 1)
    title = parts[0].strip() if parts else ""
    body = parts[1].strip() if len(parts) > 1 else ""
    return title or "Untitled note", body


def _missing_token_item():
    return ExtensionResultItem(
        icon=ICON_PATH,
        name="Joplin token is missing",
        description="Open extension preferences and paste your Web Clipper token"
    )


def _empty_query_item():
    return ExtensionResultItem(
        icon=ICON_PATH,
        name="Start typing to search or add",
        description="Use the keyword, then text to search, or '+Title::Body' to add a note"
    )


def _error_item(name, description):
    return ExtensionResultItem(
        icon=ICON_PATH,
        name=name,
        description=description
    )


class JoplinSearchExtension(Extension):

    def __init__(self):
        super(JoplinSearchExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())
        _log_event("extension_initialized")


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        query = (event.get_argument() or "").strip()
        _log_event("keyword_event", length=len(query))
        host = (extension.preferences.get("joplin_host") or DEFAULT_HOST).rstrip("/")
        token = (extension.preferences.get("joplin_token") or "").strip()

        if not query:
            _log_event("keyword_empty")
            return RenderResultListAction([_empty_query_item()])

        if query.startswith("+"):
            if not token:
                _log_event("add_note_missing_token")
                return RenderResultListAction([_missing_token_item()])

            note_text = query[1:].strip()
            if not note_text:
                _log_event("add_note_missing_title")
                return RenderResultListAction([
                    ExtensionResultItem(
                        icon=ICON_PATH,
                        name="Provide a note title",
                        description="Use +Title::Body to add a note"
                    )
                ])

            title, body = _parse_note_payload(note_text)
            description = _format_snippet(body) or "Press Enter to create this note in Joplin"
            return RenderResultListAction([
                ExtensionResultItem(
                    icon=ICON_PATH,
                    name=f"Create note '{title}'",
                    description=description,
                    on_enter=ExtensionCustomAction(
                        {
                            "type": "create-note",
                            "title": title,
                            "body": body,
                        },
                        keep_app_open=True
                    )
                )
            ])

        if not token:
            _log_event("search_missing_token")
            return RenderResultListAction([_missing_token_item()])

        try:
            notes = _search_notes(host, token, query)
        except (HTTPError, URLError) as exc:
            _log_event("search_error", error=str(exc), kind="connection")
            return RenderResultListAction([_error_item("Cannot reach Joplin", str(exc))])
        except ValueError as exc:
            _log_event("search_error", error=str(exc), kind="invalid_response")
            return RenderResultListAction([_error_item("Invalid response from Joplin", str(exc))])
        except Exception as exc:  # pragma: no cover - catch-all for unexpected errors
            _log_event("search_error", error=str(exc), kind="unexpected")
            return RenderResultListAction([_error_item("Unexpected error", str(exc))])

        if not notes:
            _log_event("search_no_results", query_length=len(query))
            return RenderResultListAction([
                ExtensionResultItem(
                    icon=ICON_PATH,
                    name="No notes found",
                    description=f"Nothing matched '{query}'"
                )
            ])

        items = []
        for note in notes:
            title = note.get("title") or "Untitled note"
            snippet_source = note.get("excerpt") or note.get("body", "")
            description = _format_snippet(snippet_source) or f"Notebook ID: {note.get('parent_id', 'unknown')}"
            note_id = note.get("id")
            on_enter = None
            if note_id:
                on_enter = ExtensionCustomAction(
                    {"type": "open-note", "note_id": note_id},
                    keep_app_open=False
                )
            items.append(ExtensionResultItem(
                icon=ICON_PATH,
                name=title,
                description=description,
                on_enter=on_enter
            ))

        return RenderResultListAction(items)


class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        data = event.get_data()
        event_type = data.get("type") if isinstance(data, dict) else None
        _log_event("item_enter", event_type=event_type)
        if not isinstance(data, dict):
            _log_event("item_enter_ignored", reason="not_dict")
            return None

        action_type = data.get("type")

        host = (extension.preferences.get("joplin_host") or DEFAULT_HOST).rstrip("/")
        token = (extension.preferences.get("joplin_token") or "").strip()

        if action_type == "open-note":
            note_id = data.get("note_id")
            if not note_id:
                _log_event("open_note_missing_id")
                return None

            if not token:
                _log_event("open_note_missing_token")
                return _open_note_url(note_id)

            try:
                _log_event("open_note_request", note_id=note_id)
                _open_note(host, token, note_id)
                _log_event("open_note_success", note_id=note_id)
            except (HTTPError, URLError) as exc:
                _log_event("open_note_error", error=str(exc), kind="connection")
                return _open_note_url(note_id)
            except ValueError as exc:
                _log_event("open_note_error", error=str(exc), kind="invalid_response")
                return _open_note_url(note_id)
            except Exception as exc:  # pragma: no cover
                _log_event("open_note_error", error=str(exc), kind="unexpected")
                return _open_note_url(note_id)

            return HideWindowAction()

        if action_type != "create-note":
            _log_event("item_enter_ignored", reason="unsupported_type", event_type=action_type)
            return None

        if not token:
            _log_event("create_note_missing_token")
            return RenderResultListAction([_missing_token_item()])

        title = data.get("title") or "Untitled note"
        body = data.get("body") or ""

        try:
            created_note = _create_note(host, token, title, body)
        except (HTTPError, URLError) as exc:
            _log_event("create_note_error", error=str(exc), kind="connection")
            return RenderResultListAction([_error_item("Cannot reach Joplin", str(exc))])
        except ValueError as exc:
            _log_event("create_note_error", error=str(exc), kind="invalid_response")
            return RenderResultListAction([_error_item("Invalid response from Joplin", str(exc))])
        except Exception as exc:  # pragma: no cover - catch-all for unexpected errors
            _log_event("create_note_error", error=str(exc), kind="unexpected")
            return RenderResultListAction([_error_item("Unexpected error", str(exc))])

        note_id = (created_note or {}).get("id")
        description = _format_snippet(body) or "Saved using the Web Clipper API"
        on_enter = OpenUrlAction(f"joplin://x-callback-url/openNote?id={note_id}") if note_id else None

        return RenderResultListAction([
            ExtensionResultItem(
                icon=ICON_PATH,
                name=f"Created '{title}'",
                description=description,
                on_enter=on_enter
            )
        ])


if __name__ == "__main__":
    JoplinSearchExtension().run()
