"""
SAPladdin - Gestor del inventario de hosts (hosts.yaml).

hosts.yaml define todos los sistemas que SAPladdin puede administrar:
  servidores Linux (SSH), Oracle DBs, SQL Server, HANA Cloud.

Este módulo lo lee, escribe y expone como tools MCP.
"""
import logging
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

_HOSTS_PATH = Path(__file__).parent.parent / "config" / "hosts.yaml"


def _load_hosts() -> list[dict]:
    """Carga hosts.yaml. Devuelve lista vacía si no existe."""
    if not _HOSTS_PATH.exists():
        return []
    try:
        with open(_HOSTS_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("hosts", [])
    except Exception as exc:
        logger.error("Error leyendo hosts.yaml: %s", exc)
        return []


def _save_hosts(hosts: list[dict]) -> None:
    """Guarda la lista de hosts en hosts.yaml."""
    _HOSTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_HOSTS_PATH, "w", encoding="utf-8") as f:
        yaml.dump({"hosts": hosts}, f, default_flow_style=False, allow_unicode=True)


def get_host_config(alias_or_name: str) -> Optional[dict]:
    """Busca un host por alias o name. Devuelve None si no existe."""
    hosts = _load_hosts()
    for h in hosts:
        if h.get("alias") == alias_or_name or h.get("name") == alias_or_name:
            return h
    return None
