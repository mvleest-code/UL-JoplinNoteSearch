# Security

## Reporting a problem

Please do not include a Joplin API token, note contents or an unredacted debug
log in a public issue. Open an issue containing only the affected version and a
description of the behaviour. I will arrange a safer way to collect any details
that are genuinely needed.

## Token and log handling

The extension needs a Joplin Web Clipper token to call the local API. The token
is read from the Ulauncher extension preferences and is never intended to be
stored in this repository.

Request URLs are sanitized before they are written to `debug.log`. Query
parameters named `token` are replaced with a mask. Debug logs can still contain
search lengths, note identifiers, titles entered while creating notes, hostnames
and error messages. Review and redact a log before sharing it.

Logs rotate every 30 minutes and five backups are retained. Delete `debug.log*`
at any time if you do not want to keep local diagnostic history.
