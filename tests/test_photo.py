"""Test della lettura da foto (endpoint HTTP, servizio e logica della proposta)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components import image
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.rilevatore_consumi.const import DOMAIN
from custom_components.rilevatore_consumi.meter import PHOTO_STRUCTURE, _to_int

from .conftest import make_entry

JPEG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
SENSOR = "sensor.gas_meter_reading"
IMAGE = "image.gas_last_photo"
GENERATE = "homeassistant.components.ai_task.async_generate_data"


def _ai(data) -> AsyncMock:
    return AsyncMock(return_value=SimpleNamespace(data=data, conversation_id="x"))


async def _setup(hass: HomeAssistant, reading: int = 5726, **options):
    hass.config.components.add("ai_task")
    entry = make_entry(reading)
    entry.add_to_hass(hass)
    if options:
        hass.config_entries.async_update_entry(entry, options=options)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _post(client, entry, body=JPEG, content_type="image/jpeg"):
    return await client.post(
        f"/api/rilevatore_consumi/photo/{entry.entry_id}",
        data=body,
        headers={"Content-Type": content_type},
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (5726, 5726),
        (5726.9, 5726),
        ("05726", 5726),
        ("5726,7", 5726),
        (0, 0),
        (None, None),
        (True, None),
        ("abc", None),
        (-1, None),
        (10**9, None),
    ],
)
def test_to_int(raw, expected) -> None:
    """Solo la parte intera, senza decimali né zeri iniziali."""
    assert _to_int(raw) == expected


async def test_photo_proposal_ok(hass: HomeAssistant, hass_client) -> None:
    """Foto leggibile: proposta senza avvisi, nulla viene salvato."""
    entry = await _setup(hass)
    client = await hass_client()
    with patch(GENERATE, _ai({"readable": True, "reading": 5730})):
        resp = await _post(client, entry)
    assert resp.status == 200
    assert await resp.json() == {
        "readable": True,
        "reading": 5730,
        "current": 5726,
        "warning": None,
    }
    assert hass.states.get(SENSOR).state == "5726"  # solo proposta


async def test_photo_is_given_to_ai_as_image_entity(
    hass: HomeAssistant, hass_client
) -> None:
    """L'AI riceve la foto tramite l'entità immagine, con istruzioni e struttura."""
    entry = await _setup(hass)
    client = await hass_client()
    seen: dict = {}

    async def fake_generate(hass_, **kwargs):
        media_id = kwargs["attachments"][0]["media_content_id"]
        entity_id = media_id.removeprefix("media-source://image/")
        got = await image.async_get_image(hass_, entity_id)
        seen.update(kwargs, content=got.content, content_type=got.content_type)
        return SimpleNamespace(data={"readable": True, "reading": 5727})

    with patch(GENERATE, fake_generate):
        resp = await _post(client, entry)
    assert resp.status == 200
    assert seen["attachments"][0]["media_content_id"] == f"media-source://image/{IMAGE}"
    assert seen["content"] == JPEG
    assert seen["content_type"] == "image/jpeg"
    assert seen["structure"] is PHOTO_STRUCTURE
    assert "intera" in seen["instructions"]
    assert seen["entity_id"] is None  # usa l'AI Task predefinito


async def test_configured_ai_entity_is_used(hass: HomeAssistant, hass_client) -> None:
    """Se l'opzione è impostata, si usa quell'entità AI Task."""
    entry = await _setup(hass, ai_task_entity="ai_task.gemini")
    client = await hass_client()
    mock = _ai({"readable": True, "reading": 5730})
    with patch(GENERATE, mock):
        await _post(client, entry)
    assert mock.call_args.kwargs["entity_id"] == "ai_task.gemini"


async def test_water_uses_water_instructions(hass: HomeAssistant, hass_client) -> None:
    """Il contatore dell'acqua usa le istruzioni dei rulli."""
    hass.config.components.add("ai_task")
    entry = make_entry(364, "water", "Acqua")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_client()
    mock = _ai({"readable": True, "reading": 365})
    with patch(GENERATE, mock):
        resp = await _post(client, entry)
    assert (await resp.json())["reading"] == 365
    assert "acqua" in mock.call_args.kwargs["instructions"]


@pytest.mark.parametrize(
    ("ai_data", "reading", "warning"),
    [
        ({"readable": True, "reading": 5000}, 5000, "lower"),
        ({"readable": True, "reading": 5726 + 301}, 6027, "jump"),
        ({"readable": True, "reading": 5726 + 300}, 6026, None),
        ({"readable": True, "reading": 5726}, 5726, None),
        ({"readable": True, "reading": 5730.8}, 5730, None),
    ],
)
async def test_photo_warnings(
    hass: HomeAssistant, hass_client, ai_data, reading, warning
) -> None:
    """Avvisi su letture più basse o con un salto troppo grande."""
    entry = await _setup(hass)
    client = await hass_client()
    with patch(GENERATE, _ai(ai_data)):
        data = await (await _post(client, entry)).json()
    assert data["readable"] is True
    assert data["reading"] == reading
    assert data["warning"] == warning


@pytest.mark.parametrize(
    "ai_data",
    [
        {"readable": False},
        {"readable": False, "reading": 5730},
        {"readable": True},
        {"readable": True, "reading": None},
        {"readable": True, "reading": "n.d."},
        {"readable": True, "reading": -4},
        None,
        "testo qualunque",
    ],
)
async def test_photo_unreadable(hass: HomeAssistant, hass_client, ai_data) -> None:
    """Se l'AI non è sicura (o risponde male) non si propone nulla."""
    entry = await _setup(hass)
    client = await hass_client()
    with patch(GENERATE, _ai(ai_data)):
        resp = await _post(client, entry)
    assert resp.status == 200
    assert await resp.json() == {
        "readable": False,
        "reading": None,
        "current": 5726,
        "warning": "unreadable",
    }


async def test_ai_error_returns_message(hass: HomeAssistant, hass_client) -> None:
    """Un errore dell'AI diventa un messaggio chiaro, non un'eccezione."""
    entry = await _setup(hass)
    client = await hass_client()
    with patch(GENERATE, AsyncMock(side_effect=HomeAssistantError("boom"))):
        resp = await _post(client, entry)
    assert resp.status == 400
    assert "boom" in (await resp.json())["message"]


async def test_ai_task_missing(hass: HomeAssistant, hass_client) -> None:
    """Senza AI Task si spiega cosa manca."""
    entry = make_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert "ai_task" not in hass.config.components
    client = await hass_client()
    resp = await _post(client, entry)
    assert resp.status == 400
    assert "AI" in (await resp.json())["message"]


async def test_http_validation(hass: HomeAssistant, hass_client) -> None:
    """Controlli sul corpo e sul contatore."""
    entry = await _setup(hass)
    client = await hass_client()
    with patch(GENERATE, _ai({"readable": True, "reading": 5730})) as mock:
        assert (await _post(client, entry, b"hello", "text/plain")).status == 400
        assert (await _post(client, entry, b"")).status == 400
        resp = await client.post(
            "/api/rilevatore_consumi/photo/non-esiste",
            data=JPEG,
            headers={"Content-Type": "image/jpeg"},
        )
        assert resp.status == 404
        with patch("custom_components.rilevatore_consumi.views.MAX_PHOTO_BYTES", 5):
            assert (await _post(client, entry)).status == 413
        mock.assert_not_called()


async def test_http_requires_auth(hass: HomeAssistant, hass_client_no_auth) -> None:
    """Senza accesso non si possono caricare foto."""
    entry = await _setup(hass)
    client = await hass_client_no_auth()
    resp = await _post(client, entry)
    assert resp.status == 401


async def test_photo_entity_state(hass: HomeAssistant, hass_client) -> None:
    """L'entità foto è sconosciuta finché non arriva una foto."""
    entry = await _setup(hass)
    assert hass.states.get(IMAGE).state == "unknown"
    client = await hass_client()
    with patch(GENERATE, _ai({"readable": True, "reading": 5730})):
        await _post(client, entry)
    assert hass.states.get(IMAGE).state != "unknown"


async def test_read_from_photo_service(hass: HomeAssistant) -> None:
    """Il servizio restituisce una proposta e non salva nulla."""
    await _setup(hass)
    mock = _ai({"readable": True, "reading": 5731})
    with patch(GENERATE, mock):
        response = await hass.services.async_call(
            DOMAIN,
            "read_from_photo",
            {
                "media": {
                    "entity_id": "camera.contatore",
                    "media_content_id": "media-source://camera/camera.contatore",
                    "media_content_type": "image/jpeg",
                }
            },
            target={"entity_id": SENSOR},
            blocking=True,
            return_response=True,
        )
    assert response[SENSOR] == {
        "readable": True,
        "reading": 5731,
        "current": 5726,
        "warning": None,
    }
    assert mock.call_args.kwargs["attachments"][0]["media_content_id"] == (
        "media-source://camera/camera.contatore"
    )
    assert hass.states.get(SENSOR).state == "5726"


async def test_read_from_photo_service_needs_media(hass: HomeAssistant) -> None:
    """Senza immagine il servizio rifiuta."""
    import voluptuous as vol
    await _setup(hass)
    with pytest.raises((vol.Invalid, ServiceValidationError)):
        await hass.services.async_call(
            DOMAIN,
            "read_from_photo",
            {"media": {}},
            target={"entity_id": SENSOR},
            blocking=True,
            return_response=True,
        )
