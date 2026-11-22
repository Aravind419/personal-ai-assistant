import pytest
import io
from httpx import AsyncClient
from app.voice.service import VoiceService
from app.voice.schemas import VoicePreferencePayload
from app.database.session import async_session_factory


def test_clean_markdown_for_speech_tables():
    markdown_table = (
        "| Technology | Type | Execution |\n"
        "|---|---|---|\n"
        "| Python | Interpreted | Bytecode VM |\n"
        "| C++ | Compiled | Machine Code |\n"
    )
    cleaned = VoiceService.clean_markdown_for_speech(markdown_table)
    assert "|" not in cleaned
    assert "---" not in cleaned
    assert "Python" in cleaned
    assert "Interpreted" in cleaned
    assert "C++" in cleaned
    assert "Compiled" in cleaned


def test_clean_markdown_for_speech_code_blocks():
    text_with_code = (
        "Here is the sample code:\n"
        "```python\n"
        "def hello_world():\n"
        "    print('Hello World')\n"
        "    return 42\n"
        "```\n"
        "That concludes the example."
    )
    cleaned = VoiceService.clean_markdown_for_speech(text_with_code)
    assert "```" not in cleaned
    assert "Code snippet in python omitted" in cleaned or "Code:" in cleaned
    assert "Here is the sample code" in cleaned


def test_clean_markdown_for_speech_json():
    json_text = '{"name": "Sarguna", "role": "engineer", "city": "Bangalore"}'
    cleaned = VoiceService.clean_markdown_for_speech(json_text)
    assert "{" not in cleaned
    assert "}" not in cleaned
    assert "Sarguna" in cleaned
    assert "engineer" in cleaned
    assert "Bangalore" in cleaned


def test_clean_markdown_for_speech_checklists_and_formatting():
    markdown = (
        "### Project Checklist\n"
        "- [x] Design schema\n"
        "- [ ] Write unit tests\n"
        "Make sure to read the [docs](https://example.com) and use **bold** words."
    )
    cleaned = VoiceService.clean_markdown_for_speech(markdown)
    assert "###" not in cleaned
    assert "- [x]" not in cleaned
    assert "- [ ]" not in cleaned
    assert "**" not in cleaned
    assert "https://" not in cleaned
    assert "Completed task: Design schema" in cleaned
    assert "Pending task: Write unit tests" in cleaned
    assert "bold words" in cleaned


@pytest.mark.asyncio
async def test_voice_transcribe_endpoint(async_client: AsyncClient):
    # Valid audio file upload
    fake_audio = b"RIFF....WAVEfmt ....data....Kasiriganapalli"
    files = {"audio": ("test.wav", fake_audio, "audio/wav")}

    res = await async_client.post("/api/v1/voice/transcribe", files=files)
    assert res.status_code == 200
    data = res.json()
    assert "text" in data
    assert "Kasiriganapalli" in data["text"]
    assert data["language"] == "en"

    # Empty audio upload rejection
    empty_files = {"audio": ("empty.wav", b"", "audio/wav")}
    res_empty = await async_client.post("/api/v1/voice/transcribe", files=empty_files)
    assert res_empty.status_code in [400, 422]


@pytest.mark.asyncio
async def test_voice_clean_endpoint(async_client: AsyncClient):
    payload = {
        "text": (
            "| Item | Price |\n"
            "|---|---|\n"
            "| Laptop | $1000 |\n"
        )
    }
    res = await async_client.post("/api/v1/voice/clean-for-speech", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "clean_text" in data
    assert "|" not in data["clean_text"]
    assert "Laptop" in data["clean_text"]
    assert data["word_count"] > 0


@pytest.mark.asyncio
async def test_voice_preferences_endpoint(async_client: AsyncClient):
    # GET preferences
    get_res = await async_client.get("/api/v1/voice/preferences")
    assert get_res.status_code == 200
    pref = get_res.json()
    assert "enabled" in pref
    assert "speed" in pref

    # PUT preferences
    update_payload = {
        "enabled": True,
        "auto_play": True,
        "speed": 1.25,
        "voice": "Google US English",
        "language": "en-US",
    }
    put_res = await async_client.put("/api/v1/voice/preferences", json=update_payload)
    assert put_res.status_code == 200
    updated = put_res.json()
    assert updated["auto_play"] is True
    assert updated["speed"] == 1.25
    assert updated["voice"] == "Google US English"
