# mini-gpt-helper

Minimal macOS menu bar app that sends clipboard text or images to AI and copies the result back to your clipboard.

## Features

- Menu bar only app (agent app, no Dock icon when bundled with `Info.plist` `LSUIElement=1`)
- Status indicator:
  - `●` idle
  - `…` processing
  - `✓` success
  - `!` error
- Popover with two modes:
  - Compact: instruction field + Send + Show Output
  - Expanded: instruction field + Send + output view + Hide Output
- Small theme toggle button in popover (`☀︎/☾`) for light/dark mode
- Global hotkey (mandatory format): `Control + Shift + <key from config>`
  - default is `Control + Shift + Space`
  - processes clipboard immediately
  - writes result back to clipboard
- Clipboard support:
  - text
  - image (PNG/TIFF converted to base64 PNG)
- AI provider in config:
  - `chatgpt` (default, uses `gpt-4o-mini`)
  - `gemini` (uses `gemini-2.0-flash` REST API)

## Project layout

- `main.py` - app delegate and workflow orchestration
- `menubar.py` - status bar item controller
- `popover.py` - popover view controller (compact + expanded)
- `clipboard.py` - NSPasteboard text/image read/write
- `openai_client.py` - provider-aware AI client (ChatGPT/Gemini)
- `hotkey.py` - global hotkey monitor
- `state.py` - app state model
- `config.py` - config loader
- `config.json.example` - sample config

## Configuration

1. Copy sample config:

```bash
cp config.json.example config.json
```

2. Choose provider/theme/hotkey in `config.json`:

```json
{
  "provider": "chatgpt",
  "theme": "light",
  "hotkey_key": "space"
}
```

`hotkey_key` examples: `space`, `a`, `b`, `1`, `2`, `-`, `=`.

3. Set API key:

- ChatGPT provider:

```bash
export OPENAI_API_KEY="your_openai_api_key"
```

- Gemini provider:

```bash
export GEMINI_API_KEY="your_gemini_api_key"
```

Optional env overrides:

- `AI_PROVIDER=chatgpt|gemini`
- `APP_THEME=light|dark`
- `HOTKEY_KEY=space|a|...`

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Notes on no Dock icon

`LSUIElement` in `Info.plist` is used when launching as a bundled app (e.g., py2app/pyinstaller app bundle).

When running directly with `python main.py`, Dock behavior can vary by runtime.
