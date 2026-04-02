import pytest

from core.tools import joplin


def _cfg_with_perms(
    *,
    allow_create: bool = True,
    allow_update: bool = True,
    allow_delete: bool = False,
    allow_manage_notebooks: bool = False,
):
    return (
        "http://127.0.0.1:41184",
        "tkn",
        {
            "allow_create": allow_create,
            "allow_update": allow_update,
            "allow_delete": allow_delete,
            "allow_manage_notebooks": allow_manage_notebooks,
        },
    )


def test_resolve_joplin_config_prefers_arguments(monkeypatch):
    monkeypatch.setenv("JOPLIN_BASE_URL", "http://env-url:41184")
    monkeypatch.setenv("JOPLIN_API_TOKEN", "env-token")
    monkeypatch.setattr(joplin, "_load_config", lambda: {"base_url": "http://cfg", "token": "cfg-token", "permissions": {}})

    base_url, token, _ = joplin._resolve_joplin_config("http://arg-url:41184", "arg-token")

    assert base_url == "http://arg-url:41184"
    assert token == "arg-token"


def test_resolve_joplin_config_uses_env(monkeypatch):
    monkeypatch.setenv("JOPLIN_BASE_URL", "http://env-url:41184/")
    monkeypatch.setenv("JOPLIN_API_TOKEN", "env-token")
    monkeypatch.setattr(joplin, "_load_config", lambda: {"base_url": "", "token": "", "permissions": {}})

    base_url, token, _ = joplin._resolve_joplin_config("", "")

    assert base_url == "http://env-url:41184"
    assert token == "env-token"


@pytest.mark.asyncio
async def test_joplin_list_notebooks_renders_items(monkeypatch):
    monkeypatch.setattr(joplin, "_resolve_joplin_config", lambda base_url, token: _cfg_with_perms())
    monkeypatch.setattr(
        joplin,
        "_joplin_request",
        lambda method, endpoint, **kwargs: {
            "items": [
                {"id": "n1", "title": "Inbox", "parent_id": ""},
                {"id": "n2", "title": "Projects", "parent_id": ""},
            ]
        },
    )

    result = await joplin.joplin_list_notebooks()

    assert "Inbox" in result
    assert "Projects" in result


@pytest.mark.asyncio
async def test_joplin_search_notes_returns_snippet(monkeypatch):
    monkeypatch.setattr(joplin, "_resolve_joplin_config", lambda base_url, token: _cfg_with_perms())
    monkeypatch.setattr(
        joplin,
        "_joplin_request",
        lambda method, endpoint, **kwargs: {
            "items": [{"id": "n1", "title": "Runbook SAP", "parent_id": "f1", "updated_time": 1, "body": "texto largo"}],
            "has_more": False,
        },
    )

    result = await joplin.joplin_search_notes(query="sap runbook")

    assert "Runbook SAP" in result
    assert "snippet:" in result


@pytest.mark.asyncio
async def test_joplin_create_note_with_tags(monkeypatch):
    monkeypatch.setattr(joplin, "_resolve_joplin_config", lambda base_url, token: _cfg_with_perms())
    calls = []

    def fake_request(method, endpoint, **kwargs):
        calls.append((method, endpoint, kwargs.get("payload")))
        if endpoint == "/notes":
            return {"id": "note-1", "title": "Test Note", "parent_id": "folder-1"}
        if endpoint == "/tags":
            tag_title = kwargs["payload"]["title"]
            return {"id": f"tag-{tag_title}"}
        return {}

    monkeypatch.setattr(joplin, "_joplin_request", fake_request)

    result = await joplin.joplin_create_note(
        title="Test Note",
        body="Body",
        parent_id="folder-1",
        tags_csv="mcp,joplin",
    )

    assert "Nota creada en Joplin" in result
    assert "note-1" in result
    assert any(endpoint == "/notes" for _, endpoint, _ in calls)
    assert any(endpoint == "/tags/tag-mcp/notes" for _, endpoint, _ in calls)


@pytest.mark.asyncio
async def test_joplin_update_requires_permission(monkeypatch):
    monkeypatch.setattr(
        joplin,
        "_resolve_joplin_config",
        lambda base_url, token: _cfg_with_perms(allow_update=False),
    )

    with pytest.raises(RuntimeError):
        await joplin.joplin_update_note(note_id="n1", title="Nuevo")


@pytest.mark.asyncio
async def test_joplin_delete_requires_confirm_and_permission(monkeypatch):
    monkeypatch.setattr(
        joplin,
        "_resolve_joplin_config",
        lambda base_url, token: _cfg_with_perms(allow_delete=False),
    )

    result = await joplin.joplin_delete_note(note_id="n1", confirm=False)
    assert "confirm=true" in result

    with pytest.raises(RuntimeError):
        await joplin.joplin_delete_note(note_id="n1", confirm=True)


@pytest.mark.asyncio
async def test_joplin_set_permissions_persists(monkeypatch):
    saved = {}
    monkeypatch.setattr(joplin, "_load_config", lambda: {"base_url": "http://x", "token": "t", "permissions": {}})
    monkeypatch.setattr(joplin, "_save_config", lambda cfg: saved.setdefault("cfg", cfg))

    result = await joplin.joplin_set_permissions(
        allow_create=True,
        allow_update=False,
        allow_delete=True,
        allow_manage_notebooks=True,
    )

    assert "Permisos Joplin actualizados" in result
    assert saved["cfg"]["permissions"]["allow_delete"] is True
