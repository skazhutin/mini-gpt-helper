# mini-gpt-helper

`mini-gpt-helper` is a native macOS menu bar app that sends clipboard text or images to ChatGPT or Gemini and writes the model response back to the clipboard.

## What It Does

- Lives in the macOS menu bar with no Dock icon when bundled
- Processes clipboard text and images
- Supports `chatgpt` and `gemini`
- Lets you add an optional instruction before sending
- Opens the config file directly from a small `Cfg` button in the menu
- Shows the latest output in a separate window
- Supports a global hotkey: `Control + Shift + <configured key>`
- Persists theme changes back to the config file

## Quick Start

1. Create a virtual environment and install dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Create a local config:

```bash
cp config.json.example config.json
```

3. Fill in either `openai_api_key` or `gemini_api_key`, or export env vars.

4. Run the app:

```bash
python main.py
```

## Configuration

Default config:

```json
{
  "provider": "chatgpt",
  "theme": "light",
  "hotkey_key": "space",
  "logging": 0,
  "prompt": "",
  "openai_model": "gpt-4o-mini",
  "gemini_model": "gemini-2.5-flash",
  "openai_api_key": "",
  "gemini_api_key": ""
}
```

Notes:

- `provider`: `chatgpt` or `gemini`
- `prompt`: base prompt that is prepended to the per-run input from the menu
- `openai_model`: model name for ChatGPT requests
- `gemini_model`: model name for Gemini requests
- `hotkey_key`: examples include `space`, `a`, `b`, `1`, `2`, `-`, `=`
- `logging`: `1` enables verbose logs, `0` disables them
- `config.json` is intentionally gitignored
- `APP_CONFIG_PATH` can point to a config file outside the repo

Supported environment variables:

- `AI_PROVIDER=chatgpt|gemini`
- `APP_THEME=light|dark`
- `HOTKEY_KEY=space|a|...`
- `APP_LOGGING=0|1`
- `APP_PROMPT=...`
- `OPENAI_MODEL=...`
- `GEMINI_MODEL=...`
- `OPENAI_API_KEY=...`
- `GEMINI_API_KEY=...`
- `GOOGLE_API_KEY=...`
- `APP_CONFIG_PATH=/absolute/or/relative/path/to/config.json`

## Providers

- ChatGPT uses the OpenAI Python SDK with `gpt-4o-mini` by default.
- Gemini uses the official `google-genai` SDK with `gemini-2.5-flash` by default.

If Gemini fails with SSL verification errors, make sure your proxy or antivirus root certificate is trusted by the system, or set `SSL_CERT_FILE` to a CA bundle that trusts it.

## Development

Run tests:

```bash
python3 -m unittest
```

Main files:

- `main.py` - app bootstrap and workflow
- `gpt_client.py` - AI provider client
- `clipboard.py` - clipboard read/write
- `popover.py` - menu UI
- `output_window.py` - output window
- `hotkey.py` - global hotkey handling
- `config.py` - config loading and saving

## Build macOS App

Build the app bundle:

```bash
./build_app.sh
```

The result is created at `dist/mini-gpt-helper.app`.

Grant permissions to the built app in:

- `System Settings > Privacy & Security > Accessibility`
- `System Settings > Privacy & Security > Input Monitoring`

You can use app without this permissions, but you will not be able to use shortcuts.

## Limitations

- The app must be launched from an active macOS desktop session.
- When running directly with `python main.py`, Dock behavior may vary by runtime.
- The bundled launcher assumes the repo checkout and `.venv` remain available.
