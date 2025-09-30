# Joplin Note Search for uLauncher

Joplin Note Search lets you browse and create notes in [Joplin](https://joplinapp.org/) directly from the uLauncher prompt by talking to the Web Clipper API.

## Features
- Search Joplin notes with fuzzy matching and quick preview snippets
- Create new notes inline with `+Title::Body` syntax
- Open notes in the desktop app (Web Clipper command) or via the `joplin://` fallback
- Configurable keyword, host, and API token via extension preferences

## Requirements
- [uLauncher](https://ulauncher.io/) v5 with extension API v2
- [Joplin](https://joplinapp.org/) desktop app with the Web Clipper service enabled
- Joplin Web Clipper API token (Tools → Options → Web Clipper)

## Installation
1. Open uLauncher preferences → Extensions.
2. Click **Add extension** and paste `https://github.com/mvleest-code/UL-JoplinNoteSearch`.
3. After it installs, open the extension settings.
4. Set your desired keyword, API host, and paste the Web Clipper token.

After saving the preferences, invoke uLauncher and type your keyword followed by a search query.

![Extension settings showing configurable keyword, host, and token fields](images/settings.png)

## Usage
- Search existing notes: `<keyword> your search terms`
- Create a new note: `<keyword> +Title::Optional body`
- Open a result: hit Enter on the desired note. If the Web Clipper command fails, the extension falls back to `joplin://` URLs.

## Development
```bash
# Install or link the extension in the local uLauncher directory
mkdir -p ~/.local/share/ulauncher/extensions
ln -s $(pwd) ~/.local/share/ulauncher/extensions/com.github.mvleest-code.joplin-search

# Run ulauncher with logging for debugging
ulauncher -v
```

Logs are written to `debug.log` (ignored in git).

To prepare a release archive:

```bash
./scripts/package.sh
```

The script creates `dist/joplin-note-search.zip`, ready to attach to a GitHub release if you prefer manual distribution; uLauncher can also install directly from the repository URL.

## License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
