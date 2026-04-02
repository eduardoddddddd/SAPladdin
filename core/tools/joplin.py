"""
SAPladdin - Joplin Web Clipper tools (lectura, búsqueda y CRUD).
"""

import json
import os
from pathlib import Path
from typing import Annotated, Any
from urllib import error, parse, request

import yaml

_DEFAULT_BASE_URL = "http://127.0.0.1:41184"
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config" / "joplin_config.yaml"
_DEFAULT_SETTINGS_PATHS = (
    Path.home() / ".config" / "joplin-desktop" / "settings.json",
    Path(os.environ.get("APPDATA", "")) / "Joplin-desktop" / "settings.json",
)


def _default_config() -> dict[str, Any]:
    return {
        "base_url": _DEFAULT_BASE_URL,
        "token": "",
        "permissions": {
            "allow_create": True,
            "allow_update": True,
            "allow_delete": False,
            "allow_manage_notebooks": False,
        },
    }


def _load_config() -> dict[str, Any]:
    cfg = _default_config()
    if _CONFIG_PATH.exists():
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
                loaded = yaml.safe_load(fh) or {}
            section = loaded.get("joplin", {})
            if isinstance(section, dict):
                cfg["base_url"] = section.get("base_url", cfg["base_url"]) or cfg["base_url"]
                cfg["token"] = section.get("token", cfg["token"]) or cfg["token"]
                perms = section.get("permissions", {})
                if isinstance(perms, dict):
                    cfg["permissions"].update(
                        {
                            "allow_create": bool(perms.get("allow_create", cfg["permissions"]["allow_create"])),
                            "allow_update": bool(perms.get("allow_update", cfg["permissions"]["allow_update"])),
                            "allow_delete": bool(perms.get("allow_delete", cfg["permissions"]["allow_delete"])),
                            "allow_manage_notebooks": bool(
                                perms.get(
                                    "allow_manage_notebooks",
                                    cfg["permissions"]["allow_manage_notebooks"],
                                )
                            ),
                        }
                    )
        except Exception:
            pass
    return cfg


def _save_config(cfg: dict[str, Any]) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "joplin": {
            "base_url": cfg.get("base_url", _DEFAULT_BASE_URL),
            "token": cfg.get("token", ""),
            "permissions": cfg.get("permissions", {}),
        }
    }
    with open(_CONFIG_PATH, "w", encoding="utf-8") as fh:
        yaml.safe_dump(payload, fh, sort_keys=False, allow_unicode=True)


def _load_joplin_token_from_settings() -> str:
    for path in _DEFAULT_SETTINGS_PATHS:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        token = payload.get("api.token", "")
        if isinstance(token, str) and token.strip():
            return token.strip()
    return ""


def _resolve_joplin_config(base_url: str, token: str) -> tuple[str, str, dict[str, bool]]:
    cfg = _load_config()
    resolved_base_url = (
        base_url
        or os.environ.get("JOPLIN_BASE_URL")
        or cfg.get("base_url", "")
        or _DEFAULT_BASE_URL
    ).strip().rstrip("/")
    resolved_token = (
        token
        or os.environ.get("JOPLIN_API_TOKEN")
        or cfg.get("token", "")
        or _load_joplin_token_from_settings()
    ).strip()
    permissions = cfg.get("permissions", {})
    return resolved_base_url, resolved_token, {
        "allow_create": bool(permissions.get("allow_create", True)),
        "allow_update": bool(permissions.get("allow_update", True)),
        "allow_delete": bool(permissions.get("allow_delete", False)),
        "allow_manage_notebooks": bool(permissions.get("allow_manage_notebooks", False)),
    }


def _require_permission(permissions: dict[str, bool], key: str, action_name: str) -> None:
    if permissions.get(key, False):
        return
    raise RuntimeError(
        f"Acción bloqueada por permisos: {action_name}. "
        f"Usa joplin_set_permissions para habilitar {key}=true."
    )


def _joplin_request(
    method: str,
    endpoint: str,
    *,
    base_url: str,
    token: str,
    timeout_seconds: int = 15,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    query_sep = "&" if "?" in endpoint else "?"
    url = f"{base_url}{endpoint}{query_sep}token={parse.quote(token)}"
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, method=method.upper(), data=data, headers=headers)
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Joplin HTTP {exc.code} en {endpoint}: {detail[:400]}") from exc
    except error.URLError as exc:
        raise RuntimeError(
            "No se pudo conectar con Joplin Web Clipper. "
            "Verifica que Joplin esté abierto y el clipper habilitado."
        ) from exc
    if not body.strip():
        return {}
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Respuesta JSON inválida de Joplin: {body[:400]}") from exc


def _mask_token(value: str) -> str:
    if not value:
        return "(vacío)"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def _ensure_token(token: str) -> None:
    if token.strip():
        return
    raise RuntimeError(
        "No se encontró token API de Joplin. "
        "Pásalo por parámetro, JOPLIN_API_TOKEN o joplin_set_config."
    )


async def joplin_status(
    base_url: Annotated[str, "URL base del Web Clipper. Default: http://127.0.0.1:41184"] = "",
    token: Annotated[str, "Token API de Joplin. Vacío = auto-resolver desde env/config/settings.json"] = "",
) -> str:
    """Valida conectividad con Joplin Web Clipper y estado general."""
    resolved_base_url, resolved_token, permissions = _resolve_joplin_config(base_url, token)
    try:
        req = request.Request(f"{resolved_base_url}/ping", method="GET")
        with request.urlopen(req, timeout=5) as response:
            ping_body = response.read().decode("utf-8", errors="replace").strip()
    except Exception as exc:
        return f"Joplin no accesible en {resolved_base_url}: {exc}"
    if "JoplinClipperServer" not in ping_body:
        return f"Ping inesperado desde Joplin ({resolved_base_url}): {ping_body}"
    return (
        "Joplin Web Clipper OK\n"
        f"  base_url: {resolved_base_url}\n"
        f"  token: {'presente' if bool(resolved_token) else 'ausente'}\n"
        f"  allow_create: {permissions['allow_create']}\n"
        f"  allow_update: {permissions['allow_update']}\n"
        f"  allow_delete: {permissions['allow_delete']}\n"
        f"  allow_manage_notebooks: {permissions['allow_manage_notebooks']}"
    )


async def joplin_get_config() -> str:
    """Muestra configuración efectiva de Joplin (sin exponer token completo)."""
    base_url, token, permissions = _resolve_joplin_config("", "")
    return (
        "Joplin config efectiva\n"
        f"  base_url: {base_url}\n"
        f"  token: {_mask_token(token)}\n"
        f"  allow_create: {permissions['allow_create']}\n"
        f"  allow_update: {permissions['allow_update']}\n"
        f"  allow_delete: {permissions['allow_delete']}\n"
        f"  allow_manage_notebooks: {permissions['allow_manage_notebooks']}\n"
        f"  config_file: {_CONFIG_PATH}"
    )


async def joplin_set_config(
    base_url: Annotated[str, "Nueva base URL. Vacío = no cambiar."] = "",
    token: Annotated[str, "Nuevo token API. Vacío = no cambiar."] = "",
) -> str:
    """Guarda configuración local de Joplin en config/joplin_config.yaml."""
    cfg = _load_config()
    changes = []
    if base_url.strip():
        cfg["base_url"] = base_url.strip().rstrip("/")
        changes.append("base_url")
    if token.strip():
        cfg["token"] = token.strip()
        changes.append("token")
    if not changes:
        return "No se aplicaron cambios. Pasa base_url y/o token."
    _save_config(cfg)
    return (
        "✓ Configuración Joplin actualizada\n"
        f"  cambios: {', '.join(changes)}\n"
        f"  archivo: {_CONFIG_PATH}"
    )


async def joplin_set_permissions(
    allow_create: Annotated[bool, "Permitir creación de notas/libretas."] = True,
    allow_update: Annotated[bool, "Permitir actualización de notas/libretas."] = True,
    allow_delete: Annotated[bool, "Permitir borrado de notas/libretas."] = False,
    allow_manage_notebooks: Annotated[bool, "Permitir crear/renombrar/borrar libretas."] = False,
) -> str:
    """Edita autorizaciones de escritura de la integración Joplin."""
    cfg = _load_config()
    cfg["permissions"] = {
        "allow_create": bool(allow_create),
        "allow_update": bool(allow_update),
        "allow_delete": bool(allow_delete),
        "allow_manage_notebooks": bool(allow_manage_notebooks),
    }
    _save_config(cfg)
    return (
        "✓ Permisos Joplin actualizados\n"
        f"  allow_create: {cfg['permissions']['allow_create']}\n"
        f"  allow_update: {cfg['permissions']['allow_update']}\n"
        f"  allow_delete: {cfg['permissions']['allow_delete']}\n"
        f"  allow_manage_notebooks: {cfg['permissions']['allow_manage_notebooks']}"
    )


async def joplin_list_notebooks(
    limit: Annotated[int, "Número máximo de libretas. Default 100."] = 100,
    base_url: Annotated[str, "URL base del Web Clipper."] = "",
    token: Annotated[str, "Token API de Joplin. Vacío = auto-resolver."] = "",
) -> str:
    """Lista libretas (folders) con id y padre."""
    resolved_base_url, resolved_token, _ = _resolve_joplin_config(base_url, token)
    _ensure_token(resolved_token)
    safe_limit = max(1, min(limit, 200))
    response = _joplin_request(
        "GET",
        f"/folders?fields=id,title,parent_id&limit={safe_limit}",
        base_url=resolved_base_url,
        token=resolved_token,
    )
    items = response.get("items", [])
    if not isinstance(items, list) or not items:
        return "No se encontraron libretas en Joplin."
    lines = [f"Libretas Joplin ({len(items)}):", "=" * 70]
    for item in items:
        lines.append(
            f"- {item.get('title', '(sin título)')} | id={item.get('id', '?')} | parent={item.get('parent_id', '-')}"
        )
    return "\n".join(lines)


async def joplin_create_notebook(
    title: Annotated[str, "Título de la libreta."],
    parent_id: Annotated[str, "ID de la libreta padre. Opcional."] = "",
    base_url: Annotated[str, "URL base del Web Clipper."] = "",
    token: Annotated[str, "Token API de Joplin."] = "",
) -> str:
    """Crea una libreta en Joplin."""
    resolved_base_url, resolved_token, permissions = _resolve_joplin_config(base_url, token)
    _ensure_token(resolved_token)
    _require_permission(permissions, "allow_manage_notebooks", "joplin_create_notebook")
    clean_title = title.strip()
    if not clean_title:
        return "title no puede estar vacío."
    payload: dict[str, Any] = {"title": clean_title}
    if parent_id.strip():
        payload["parent_id"] = parent_id.strip()
    folder = _joplin_request("POST", "/folders", base_url=resolved_base_url, token=resolved_token, payload=payload)
    return f"✓ Libreta creada: {folder.get('title', clean_title)} | id={folder.get('id', '?')}"


async def joplin_rename_notebook(
    folder_id: Annotated[str, "ID de la libreta."],
    new_title: Annotated[str, "Nuevo título."],
    base_url: Annotated[str, "URL base del Web Clipper."] = "",
    token: Annotated[str, "Token API de Joplin."] = "",
) -> str:
    """Renombra una libreta existente."""
    resolved_base_url, resolved_token, permissions = _resolve_joplin_config(base_url, token)
    _ensure_token(resolved_token)
    _require_permission(permissions, "allow_manage_notebooks", "joplin_rename_notebook")
    fid = folder_id.strip()
    if not fid:
        return "folder_id no puede estar vacío."
    title = new_title.strip()
    if not title:
        return "new_title no puede estar vacío."
    _joplin_request(
        "PUT",
        f"/folders/{parse.quote(fid)}",
        base_url=resolved_base_url,
        token=resolved_token,
        payload={"title": title},
    )
    return f"✓ Libreta actualizada: id={fid} | title={title}"


async def joplin_delete_notebook(
    folder_id: Annotated[str, "ID de libreta a borrar."],
    confirm: Annotated[bool, "Confirmar borrado con true."] = False,
    base_url: Annotated[str, "URL base del Web Clipper."] = "",
    token: Annotated[str, "Token API de Joplin."] = "",
) -> str:
    """Borra una libreta de Joplin (requiere permisos y confirmación)."""
    if not confirm:
        return "Borrado no ejecutado. Pasa confirm=true."
    resolved_base_url, resolved_token, permissions = _resolve_joplin_config(base_url, token)
    _ensure_token(resolved_token)
    _require_permission(permissions, "allow_delete", "joplin_delete_notebook")
    _require_permission(permissions, "allow_manage_notebooks", "joplin_delete_notebook")
    fid = folder_id.strip()
    if not fid:
        return "folder_id no puede estar vacío."
    _joplin_request("DELETE", f"/folders/{parse.quote(fid)}", base_url=resolved_base_url, token=resolved_token)
    return f"✓ Libreta eliminada: id={fid}"


async def joplin_list_notes(
    limit: Annotated[int, "Máximo de notas. Default 50."] = 50,
    page: Annotated[int, "Página de resultados (1..n)."] = 1,
    parent_id: Annotated[str, "Filtrar por libreta (folder id). Opcional."] = "",
    include_body: Annotated[bool, "Incluir cuerpo en la salida (puede ser largo)."] = False,
    base_url: Annotated[str, "URL base del Web Clipper."] = "",
    token: Annotated[str, "Token API de Joplin."] = "",
) -> str:
    """Lista notas con resumen y metadatos."""
    resolved_base_url, resolved_token, _ = _resolve_joplin_config(base_url, token)
    _ensure_token(resolved_token)
    safe_limit = max(1, min(limit, 100))
    safe_page = max(1, page)
    fields = "id,title,parent_id,updated_time"
    if include_body:
        fields += ",body"
    endpoint = f"/notes?fields={fields}&limit={safe_limit}&page={safe_page}&order_by=updated_time&order_dir=DESC"
    if parent_id.strip():
        endpoint += f"&parent_id={parse.quote(parent_id.strip())}"
    response = _joplin_request("GET", endpoint, base_url=resolved_base_url, token=resolved_token)
    items = response.get("items", [])
    if not isinstance(items, list) or not items:
        return "No se encontraron notas."
    lines = [f"Notas Joplin ({len(items)}):", "=" * 90]
    for item in items:
        lines.append(
            f"- {item.get('title', '(sin título)')} | id={item.get('id', '?')} | parent={item.get('parent_id', '-')} | updated={item.get('updated_time', '-')}"
        )
        if include_body:
            body = (item.get("body", "") or "").replace("\r", " ").replace("\n", " ")
            lines.append(f"  body: {body[:300]}{'...' if len(body) > 300 else ''}")
    lines.append(f"has_more: {bool(response.get('has_more', False))}")
    return "\n".join(lines)


async def joplin_get_note(
    note_id: Annotated[str, "ID de la nota."],
    include_body: Annotated[bool, "Incluir contenido completo de body."] = True,
    base_url: Annotated[str, "URL base del Web Clipper."] = "",
    token: Annotated[str, "Token API de Joplin."] = "",
) -> str:
    """Obtiene una nota concreta por id."""
    resolved_base_url, resolved_token, _ = _resolve_joplin_config(base_url, token)
    _ensure_token(resolved_token)
    nid = note_id.strip()
    if not nid:
        return "note_id no puede estar vacío."
    fields = "id,title,parent_id,updated_time,created_time"
    if include_body:
        fields += ",body"
    note = _joplin_request(
        "GET",
        f"/notes/{parse.quote(nid)}?fields={fields}",
        base_url=resolved_base_url,
        token=resolved_token,
    )
    lines = [
        f"id: {note.get('id', nid)}",
        f"title: {note.get('title', '(sin título)')}",
        f"parent_id: {note.get('parent_id', '-')}",
        f"created_time: {note.get('created_time', '-')}",
        f"updated_time: {note.get('updated_time', '-')}",
    ]
    if include_body:
        lines.append("body:")
        lines.append(note.get("body", ""))
    return "\n".join(lines)


async def joplin_search_notes(
    query: Annotated[str, "Consulta Joplin. Acepta sintaxis avanzada (tag:, notebook:, any:, etc)."],
    limit: Annotated[int, "Máximo de resultados por página."] = 25,
    page: Annotated[int, "Página de resultados."] = 1,
    include_body: Annotated[bool, "Incluir snippet del body para revisión profunda."] = True,
    base_url: Annotated[str, "URL base del Web Clipper."] = "",
    token: Annotated[str, "Token API de Joplin."] = "",
) -> str:
    """Busca notas en profundidad usando /search del Web Clipper."""
    resolved_base_url, resolved_token, _ = _resolve_joplin_config(base_url, token)
    _ensure_token(resolved_token)
    q = query.strip()
    if not q:
        return "query no puede estar vacío."
    safe_limit = max(1, min(limit, 100))
    safe_page = max(1, page)
    fields = "id,title,parent_id,updated_time"
    if include_body:
        fields += ",body"
    endpoint = (
        f"/search?query={parse.quote(q)}&type=note&fields={fields}"
        f"&limit={safe_limit}&page={safe_page}"
    )
    response = _joplin_request("GET", endpoint, base_url=resolved_base_url, token=resolved_token)
    items = response.get("items", [])
    if not isinstance(items, list) or not items:
        return f"Sin resultados para query: {q}"
    lines = [f"Resultados Joplin ({len(items)}) para: {q}", "=" * 95]
    for item in items:
        lines.append(
            f"- {item.get('title', '(sin título)')} | id={item.get('id', '?')} | parent={item.get('parent_id', '-')} | updated={item.get('updated_time', '-')}"
        )
        if include_body:
            body = (item.get("body", "") or "").replace("\r", " ").replace("\n", " ")
            lines.append(f"  snippet: {body[:350]}{'...' if len(body) > 350 else ''}")
    lines.append(f"has_more: {bool(response.get('has_more', False))}")
    return "\n".join(lines)


async def joplin_create_note(
    title: Annotated[str, "Título de la nota."],
    body: Annotated[str, "Contenido Markdown de la nota."] = "",
    parent_id: Annotated[str, "ID de libreta destino (folder). Vacío = libreta por defecto."] = "",
    tags_csv: Annotated[str, "Tags separados por coma. Opcional."] = "",
    base_url: Annotated[str, "URL base del Web Clipper."] = "",
    token: Annotated[str, "Token API de Joplin. Vacío = auto-resolver."] = "",
) -> str:
    """Crea una nota y opcionalmente agrega tags."""
    resolved_base_url, resolved_token, permissions = _resolve_joplin_config(base_url, token)
    _ensure_token(resolved_token)
    _require_permission(permissions, "allow_create", "joplin_create_note")
    clean_title = title.strip()
    if not clean_title:
        return "title no puede estar vacío."

    payload: dict[str, Any] = {"title": clean_title, "body": body}
    if parent_id.strip():
        payload["parent_id"] = parent_id.strip()

    note = _joplin_request(
        "POST",
        "/notes",
        base_url=resolved_base_url,
        token=resolved_token,
        payload=payload,
    )
    note_id = note.get("id", "")
    if not note_id:
        return f"Joplin respondió sin id de nota: {note}"

    tag_names = [tag.strip() for tag in tags_csv.split(",") if tag.strip()]
    created_tags = []
    for tag_name in tag_names:
        tag_obj = _joplin_request(
            "POST",
            "/tags",
            base_url=resolved_base_url,
            token=resolved_token,
            payload={"title": tag_name},
        )
        tag_id = tag_obj.get("id")
        if tag_id:
            _joplin_request(
                "POST",
                f"/tags/{tag_id}/notes",
                base_url=resolved_base_url,
                token=resolved_token,
                payload={"id": note_id},
            )
            created_tags.append(tag_name)

    return (
        "✓ Nota creada en Joplin\n"
        f"  title: {note.get('title', clean_title)}\n"
        f"  id: {note_id}\n"
        f"  parent_id: {note.get('parent_id', '-')}\n"
        f"  tags: {', '.join(created_tags) if created_tags else '-'}"
    )


async def joplin_update_note(
    note_id: Annotated[str, "ID de la nota a actualizar."],
    title: Annotated[str, "Nuevo título. Vacío = no cambiar."] = "",
    body: Annotated[str, "Nuevo body markdown. Vacío = no cambiar."] = "",
    parent_id: Annotated[str, "Nuevo parent_id. Vacío = no cambiar."] = "",
    base_url: Annotated[str, "URL base del Web Clipper."] = "",
    token: Annotated[str, "Token API de Joplin."] = "",
) -> str:
    """Actualiza campos de una nota existente."""
    resolved_base_url, resolved_token, permissions = _resolve_joplin_config(base_url, token)
    _ensure_token(resolved_token)
    _require_permission(permissions, "allow_update", "joplin_update_note")
    nid = note_id.strip()
    if not nid:
        return "note_id no puede estar vacío."
    payload: dict[str, Any] = {}
    if title.strip():
        payload["title"] = title.strip()
    if body.strip():
        payload["body"] = body
    if parent_id.strip():
        payload["parent_id"] = parent_id.strip()
    if not payload:
        return "No hay cambios para aplicar. Pasa title, body o parent_id."
    updated = _joplin_request(
        "PUT",
        f"/notes/{parse.quote(nid)}",
        base_url=resolved_base_url,
        token=resolved_token,
        payload=payload,
    )
    return f"✓ Nota actualizada: id={updated.get('id', nid)} | title={updated.get('title', title or '(sin cambio)')}"


async def joplin_delete_note(
    note_id: Annotated[str, "ID de la nota a borrar."],
    confirm: Annotated[bool, "Confirmar borrado con true."] = False,
    base_url: Annotated[str, "URL base del Web Clipper."] = "",
    token: Annotated[str, "Token API de Joplin."] = "",
) -> str:
    """Elimina una nota de Joplin (requiere permiso + confirmación)."""
    if not confirm:
        return "Borrado no ejecutado. Pasa confirm=true."
    resolved_base_url, resolved_token, permissions = _resolve_joplin_config(base_url, token)
    _ensure_token(resolved_token)
    _require_permission(permissions, "allow_delete", "joplin_delete_note")
    nid = note_id.strip()
    if not nid:
        return "note_id no puede estar vacío."
    _joplin_request("DELETE", f"/notes/{parse.quote(nid)}", base_url=resolved_base_url, token=resolved_token)
    return f"✓ Nota eliminada: id={nid}"
