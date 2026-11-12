import json
import re
from pathlib import Path

import pytest

import app as z407_app

HTML = Path("templates/index.html").read_text(encoding="utf-8")
SCRIPT = Path("static/app.js").read_text(encoding="utf-8")
TRANSLATIONS = json.loads(Path("static/i18n.json").read_text(encoding="utf-8"))


def test_every_language_has_the_same_keys_and_no_empty_strings():
    english = TRANSLATIONS["en"]
    for language, strings in TRANSLATIONS.items():
        assert set(strings) == set(english), f"{language} keys differ from en"
        assert all(value.strip() for value in strings.values()), f"{language} has an empty string"


def test_placeholders_match_between_languages():
    for key, english in TRANSLATIONS["en"].items():
        expected = set(re.findall(r"\{(\w+)\}", english))
        for language, strings in TRANSLATIONS.items():
            assert set(re.findall(r"\{(\w+)\}", strings[key])) == expected, f"{language}:{key}"


def test_every_key_used_by_the_page_exists():
    used = set(re.findall(r'data-i18n(?:-aria)?="([^"]+)"', HTML))
    used |= set(re.findall(r"""\bt\('([\w.]+)'""", SCRIPT))
    assert used, "no keys found — the regex is out of date"
    missing = used - set(TRANSLATIONS["en"])
    assert not missing, f"missing translations: {sorted(missing)}"


def test_dynamic_key_families_are_complete():
    english = TRANSLATIONS["en"]
    for state in ("connected", "searching", "connecting", "disconnected", "error", "offline"):
        assert f"state.{state}" in english
    for name in ("calibrate", "pair", "reset", "quit"):
        for part in ("title", "body", "ok"):
            assert f"confirm.{name}.{part}" in english
    for busy in ("calibrating", "adjusting"):
        assert f"busy.{busy}" in english
    for input_name in z407_app.VALID_INPUTS:
        assert f"input.{input_name}" in english


def test_every_button_command_is_supported_by_the_server():
    commands = set(re.findall(r'data-(?:command|repeat)="([^"]+)"', HTML))
    commands |= {f"input_{name}" for name in re.findall(r'data-input="([^"]+)"', HTML)}
    assert commands
    assert commands <= z407_app.SUPPORTED_COMMANDS


def test_page_sends_the_client_header_and_has_no_inline_handlers():
    assert z407_app.CLIENT_HEADER in SCRIPT
    assert not re.search(r"\son\w+=", HTML), "inline handlers are blocked by the CSP"
    assert "style=" not in HTML


@pytest.mark.asyncio
async def test_page_embeds_translations_and_sets_a_strict_csp(client):
    response = await client.get("/")
    body = await response.get_data(as_text=True)

    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    embedded = re.search(r'<script type="application/json" id="i18n">(.*?)</script>', body, re.S).group(1)
    assert json.loads(embedded)["zh-TW"]["state.connected"] == "已連線"
