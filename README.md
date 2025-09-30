# Joplin Note Search for Ulauncher

Joplin Note Search lets you browse and create notes in [Joplin](https://joplinapp.org/) directly from the Ulauncher prompt by talking to the Web Clipper API.

## Features
- Search Joplin notes with fuzzy matching and quick preview snippets
- Create new notes inline with `+Title::Body` syntax
- Open notes in the desktop app (Web Clipper command) or via the `joplin://` fallback
- Configurable keyword, host, and API token via extension preferences

## Requirements
- [Ulauncher](https://ulauncher.io/) v5 with extension API v2
- [Joplin](https://joplinapp.org/) desktop app with the Web Clipper service enabled
- Joplin Web Clipper API token (Tools → Options → Web Clipper)

## Installation
1. Open Ulauncher preferences → Extensions.
2. Click **Add extension** and paste `https://github.com/mvleest-code/UL-JoplinNoteSearch`.
3. After it installs, open the extension settings.
4. Set your desired keyword, API host, and paste the Web Clipper token.

After saving the preferences, invoke Ulauncher and type your keyword followed by a search query.

![Extension settings showing configurable keyword, host, and token fields](images/settings.png)

## Usage
- Search existing notes: `<keyword> your search terms`
- Create a new note: `<keyword> +Title::Optional body`
- Open a result: hit Enter on the desired note. If the Web Clipper command fails, the extension falls back to `joplin://` URLs.

## License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
