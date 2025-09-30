
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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


# Helper to get the debug log path, optionally from user preferences
def _get_debug_log_path(prefs=None):
    # If user set a path in preferences, use it
    if prefs:
        user_path = (prefs.get("debug_log_path") or "").strip()
        if user_path:
            try:
                log_path = Path(os.path.expanduser(user_path))
                log_path.parent.mkdir(parents=True, exist_ok=True)
                return log_path
            except Exception:
                pass
    # Otherwise use the extension cache dir
    try:
        ext_id = os.environ.get("EXTENSION_UUID")
        if not ext_id:
            raise RuntimeError("EXTENSION_UUID not set")
        cache_dir = os.path.join(
            os.path.expanduser("~/.cache/ulauncher_cache/extensions"),
            ext_id
        )
        os.makedirs(cache_dir, exist_ok=True)
        return Path(os.path.join(cache_dir, "debug.log"))
    except Exception:
        return Path(os.path.expanduser("~/.UL-JoplinNoteSearch-debug.log"))

def _log(message):

_DEBUG_ENABLED = False


def _log(message, prefs=None):
    if not _DEBUG_ENABLED:
        return
    try:
        log_path = _get_debug_log_path(prefs)
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        with log_path.open("a", encoding="utf-8") as debug_file:
            debug_file.write(f"{timestamp} {message}\n")
    except Exception:
        pass


_log("module loaded")


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

    _log(f"fetch {method} {url}")
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
    _log(f"search notes query='{query}' host='{host}'")
    return _fetch_json(url).get("items", [])


def _create_note(host, token, title, body):
    params = urlencode({"token": token})
    payload = {"title": title}
    if body:
        payload["body"] = body
    url = f"{host}/notes?{params}"
    _log(f"create note '{title}' host='{host}' body_len={len(body)}")
    return _fetch_json(url, method="POST", payload=payload)


def _execute_command(host, token, command_type, **kwargs):
    params = urlencode({"token": token})
    payload = {"type": command_type, **kwargs}
    url = f"{host}/commands?{params}"
    _log(f"command {command_type} payload={kwargs}")
    return _fetch_json(url, method="POST", payload=payload)


def _open_note(host, token, note_id):
    return _execute_command(host, token, "openNote", noteId=note_id)


def _open_note_url(note_id):
    url = f"joplin://x-callback-url/openNote?id={note_id}"
    _log(f"fallback open via url {url}")
    try:
        subprocess.Popen(["xdg-open", url])
    except Exception as exc:
        _log(f"fallback command failed: {exc}")
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
        self._update_logging_flag(self.preferences)

    def on_preferences_update(self, prefs):
        self._update_logging_flag(prefs)

    @staticmethod
    def _update_logging_flag(prefs):
        global _DEBUG_ENABLED
        value = (prefs.get("enable_debug") or "").strip().lower()
        enable_debug = value in {"true", "1", "yes", "on"}
        previous = _DEBUG_ENABLED
        _DEBUG_ENABLED = enable_debug
        if enable_debug and not previous:
            log_path = _get_debug_log_path(prefs)
            _log(f"debug logging enabled. Log path: {log_path}", prefs)
        if not enable_debug and previous:
            try:
                log_path = _get_debug_log_path(prefs)
                with log_path.open("a", encoding="utf-8") as debug_file:
                    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                    debug_file.write(f"{timestamp} debug logging disabled\n")
            except Exception:
                pass


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        query = (event.get_argument() or "").strip()
        _log(f"keyword event received argument='{query}'")
        host = (extension.preferences.get("joplin_host") or DEFAULT_HOST).rstrip("/")
        token = (extension.preferences.get("joplin_token") or "").strip()

        if not query:
            _log("empty query")
            return RenderResultListAction([_empty_query_item()])

        if query.startswith("+"):
            if not token:
                _log("missing token when adding note")
                return RenderResultListAction([_missing_token_item()])

            note_text = query[1:].strip()
            if not note_text:
                _log("note creation requested without title")
                return RenderResultListAction([
                    ExtensionResultItem(
                        icon=ICON_PATH,
                        name="Provide a note title",
                        description="Use +Title::Body to add a note"
                    )
                ])

            title, body = _parse_note_payload(note_text)
            _log(f"note creation prepared title='{title}' body_len={len(body)}")
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
            _log("missing token when searching")
            return RenderResultListAction([_missing_token_item()])

        try:
            notes = _search_notes(host, token, query)
        except (HTTPError, URLError) as exc:
            _log(f"search connection error: {exc}")
            return RenderResultListAction([_error_item("Cannot reach Joplin", str(exc))])
        except ValueError as exc:
            _log(f"search invalid response: {exc}")
            return RenderResultListAction([_error_item("Invalid response from Joplin", str(exc))])
        except Exception as exc:  # pragma: no cover - catch-all for unexpected errors
            _log(f"search unexpected error: {exc}")
            return RenderResultListAction([_error_item("Unexpected error", str(exc))])

        if not notes:
            _log("search returned no notes")
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
        _log(f"item enter event data={data}")
        if not isinstance(data, dict):
            _log("item enter ignored: not dict")
            return None

        action_type = data.get("type")

        host = (extension.preferences.get("joplin_host") or DEFAULT_HOST).rstrip("/")
        token = (extension.preferences.get("joplin_token") or "").strip()

        if action_type == "open-note":
            note_id = data.get("note_id")
            if not note_id:
                _log("open-note missing note_id")
                return None

            if not token:
                _log("open-note missing token")
                return _open_note_url(note_id)

            try:
                _open_note(host, token, note_id)
            except (HTTPError, URLError) as exc:
                _log(f"open note connection error: {exc}")
                return _open_note_url(note_id)
            except ValueError as exc:
                _log(f"open note invalid response: {exc}")
                return _open_note_url(note_id)
            except Exception as exc:  # pragma: no cover
                _log(f"open note unexpected error: {exc}")
                return _open_note_url(note_id)

            return HideWindowAction()

        if action_type != "create-note":
            _log("item enter ignored: unsupported type")
            return None

        if not token:
            _log("item enter missing token")
            return RenderResultListAction([_missing_token_item()])

        title = data.get("title") or "Untitled note"
        body = data.get("body") or ""

        try:
            created_note = _create_note(host, token, title, body)
        except (HTTPError, URLError) as exc:
            _log(f"create note connection error: {exc}")
            return RenderResultListAction([_error_item("Cannot reach Joplin", str(exc))])
        except ValueError as exc:
            _log(f"create note invalid response: {exc}")
            return RenderResultListAction([_error_item("Invalid response from Joplin", str(exc))])
        except Exception as exc:  # pragma: no cover - catch-all for unexpected errors
            _log(f"create note unexpected error: {exc}")
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
