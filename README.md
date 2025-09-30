# UL Joplin Note Search for uLauncher

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Buy me a coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-%F0%9F%8D%BA-FFDD00?logo=buymeacoffee&logoColor=000)](https://www.buymeacoffee.com/mvleest.code)

Search, preview, and create notes in [Joplin](https://joplinapp.org/) straight from the uLauncher command bar.

## Highlights
- 🔍 Fuzzy-search across Joplin notes with instant preview snippets
- ✏️ Create notes inline using the `+Title::Body` shorthand
- 🔗 Open notes via Web Clipper command with automatic `joplin://` fallback
- ⚙️ Configure keyword, host, and API token from the extension preferences

## Requirements
- [uLauncher](https://ulauncher.io/) v5 with extension API v2
- [Joplin](https://joplinapp.org/) desktop app running locally with the Web Clipper service enabled
- Joplin Web Clipper API token (`Tools → Options → Web Clipper`)

> ✅ Keep Joplin open and confirm the Web Clipper toggle is on before invoking the extension.

![Joplin Web Clipper settings showing service enabled and token](images/enablewebclipper.png)

## Installation
### Install via GitHub URL (recommended)
1. Open uLauncher preferences → **Extensions**.
2. Click **Add extension** and paste `https://github.com/mvleest-code/UL-JoplinNoteSearch`.
3. Open the new entry’s preferences and fill in the keyword, host, and API token.

![Extension settings showing configurable keyword, host, and token fields](images/settings.png)

## Usage
- Search existing notes: `<keyword> your search terms`
- Create a note inline: `<keyword> +Title::Optional body`
- Open a result: press Enter — the extension tries the Web Clipper command first, then falls back to a `joplin://` URL if needed
- Typing only the keyword keeps uLauncher waiting; add a query or `+Title::Body` payload to trigger actions
- Debug logging is enabled by default (writes to `debug.log` next to `main.py`, rotated hourly); switch off **Enable debug logging** in preferences if you want fewer traces

![Searching for a note from uLauncher](images/searchnote.png)

![Creating a note inline](images/addnote.png)

## Troubleshooting
- **No results / spinner forever** → Confirm Joplin is running and Web Clipper is enabled. Restart Joplin if the service was recently toggled.
- **HTTP 403/401 errors** → The API token is missing or incorrect. Regenerate it in Joplin and update the extension preferences.
- **Open note fails** → The note ID may not exist or Joplin refused the command; the extension automatically falls back to a `joplin://` link.
- **Keyword does nothing** → The keyword field must be saved in uLauncher preferences. Reopen settings, enter your keyword (e.g., `note`), save, and try again.
- **Need fewer logs?** → Disable the **Enable debug logging** setting, reproduce the behaviour, then re-enable it when you’re done collecting details.

***

## Development
```bash
# Link the extension into local uLauncher extensions
mkdir -p ~/.local/share/ulauncher/extensions
ln -s $(pwd) ~/.local/share/ulauncher/extensions/com.github.mvleest-code.ul-joplinnotesearch

# Launch uLauncher with verbose logging
ulauncher -v
```

Logs are written to `debug.log` in the project root (git-ignored).

## Support
If you hit a snag or have questions, open a GitHub issue with the relevant `debug.log` excerpt and environment details (uLauncher version, Joplin version, OS). I respond as quickly as I can.

## License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
