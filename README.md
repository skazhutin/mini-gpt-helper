# mini-gpt-helper

Minimal macOS menu bar app that sends clipboard text or images to AI and copies the result back to your clipboard.

## Features

- Menu bar only app (agent app, no Dock icon when bundled with `Info.plist` `LSUIElement=1`)
- Status indicator:
  - `●` idle
  - `…` processing
  - `✓` success
  - `!` error
- Custom status menu with:
  - instruction field
  - `Send`
  - `Show`
  - `Theme`
  - `Quit`
- Separate output window opened by `Show`
- Theme toggle updates the custom menu content and output window
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
- `popover.py` - custom menu content view controller
- `output_window.py` - separate output window controller
- `clipboard.py` - NSPasteboard text/image read/write
- `openai_client.py` - provider-aware AI client (ChatGPT/Gemini)
- `hotkey.py` - global hotkey monitor
- `state.py` - app state model
- `config.py` - config loader
- `config.json.example` - sample config
- `build_app.sh` - native macOS app bundle builder
- `native_launcher.c` - native launcher used by the bundled app

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
  "hotkey_key": "space",
  "logging": 0,
  "openai_api_key": "",
  "gemini_api_key": ""
}
```

`hotkey_key` examples: `space`, `a`, `b`, `1`, `2`, `-`, `=`.
`logging`: `1` enables verbose terminal logs, `0` disables them.
`openai_api_key` and `gemini_api_key` can be stored in `config.json` if you do not want to export env vars.

3. Set API key.

You can keep keys either in `config.json` or in environment variables. Environment variables override the config file.

- ChatGPT provider in `config.json`:

```json
"openai_api_key": "your_openai_api_key"
```

- Gemini provider in `config.json`:

```json
"gemini_api_key": "your_gemini_api_key"
```

Or export them from the shell:

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
- `APP_LOGGING=0|1`
- `OPENAI_API_KEY=...`
- `GEMINI_API_KEY=...`

## Run

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Recommended for development: use a stable python.org Python release such as 3.12 or 3.13, not a prerelease interpreter.

If Gemini fails with an SSL verification error, reinstall dependencies and make sure `certifi` is installed. The app uses the `certifi` CA bundle for Gemini HTTPS requests.

## Build macOS App

If you want macOS Accessibility / Input Monitoring permissions to be requested for `mini-gpt-helper.app` itself, run the app as a real bundled macOS application instead of `python main.py`.

Build it with:

```bash
./build_app.sh
```

The built app will appear at:

```bash
dist/mini-gpt-helper.app
```

Grant permissions to that bundled app in:

- `System Settings > Privacy & Security > Accessibility`
- `System Settings > Privacy & Security > Input Monitoring`

This bundle uses a native launcher executable and points at the current repo checkout plus `.venv`, so permissions should be attributed to `mini-gpt-helper.app` rather than `Python`.

## Notes on no Dock icon

`LSUIElement` in `Info.plist` is used when launching as a bundled app.

When running directly with `python main.py`, Dock behavior can vary by runtime.

The app must be launched from an active macOS desktop session. If you start it from a headless shell or automation runner, AppKit can abort before Python prints a traceback.
