"""
SAPladdin - SSH tools para acceso remoto a Linux/Windows.

Permite conectar a múltiples hosts simultáneamente, ejecutar comandos,
transferir ficheros y gestionar las conexiones activas.

Dependencia: pip install paramiko
Integración con hosts.yaml: usa el alias del host para conectar.
"""
import logging
import os
import threading
from pathlib import Path
from typing import Annotated, Optional

logger = logging.getLogger(__name__)

# Pool de conexiones SSH activas {alias_o_key: paramiko.SSHClient}
_ssh_pool: dict[str, object] = {}
_pool_lock = threading.Lock()


def _get_paramiko():
    try:
        import paramiko
        return paramiko
    except ImportError:
        raise RuntimeError("paramiko no instalado. Ejecuta: pip install paramiko")


def _conn_key(host: str, port: int, user: str) -> str:
    return f"{user}@{host}:{port}"


async def ssh_connect(
    host: Annotated[str, "IP o hostname del servidor remoto. O alias definido en hosts.yaml."] = "",
    user: Annotated[str, "Usuario SSH."] = "root",
    port: Annotated[int, "Puerto SSH. Default 22."] = 22,
    password: Annotated[str, "Contraseña. Vacío si usas clave privada."] = "",
    key_path: Annotated[str, "Ruta a clave privada SSH (~/.ssh/id_rsa). Vacío si usas password."] = "",
    alias: Annotated[str, "Nombre corto para identificar esta conexión. Default = user@host."] = "",
    timeout: Annotated[int, "Timeout de conexión en segundos. Default 15."] = 15,
) -> str:
    """Establece una conexión SSH a un servidor remoto y la mantiene en el pool.

    Puedes usar password o clave privada. La conexión queda activa para
    ssh_execute, ssh_upload, ssh_download. Usa ssh_disconnect para cerrarla.
    """
    # Resolver alias desde hosts.yaml si se proporciona
    host_resolved, port_resolved, user_resolved = host, port, user
    if alias or (host and not host.replace(".", "").replace(":", "").isdigit() and len(host) < 20):
        try:
            from core.hosts import get_host_config
            cfg = get_host_config(alias or host)
            if cfg:
                host_resolved = cfg.get("ip") or cfg.get("host") or host
                port_resolved = cfg.get("port", port)
                user_resolved = cfg.get("user", user)
                if not password and not key_path:
                    password = cfg.get("password", "")
                    key_path = cfg.get("key_path", "")
        except Exception:
            pass  # Si no hay hosts.yaml, usamos los parámetros directos

    if not host_resolved:
        lookup_name = alias or host or "<vacío>"
        return (
            "✗ No se pudo resolver el host SSH.\n"
            "Pasa host explícito o usa un alias existente en hosts.yaml.\n"
            f"Valor recibido: {lookup_name}"
        )

    paramiko = _get_paramiko()
    conn_key = alias if alias else _conn_key(host_resolved, port_resolved, user_resolved)

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_kwargs: dict = {
            "hostname": host_resolved,
            "port": port_resolved,
            "username": user_resolved,
            "timeout": timeout,
            "allow_agent": True,
            "look_for_keys": True,
        }
        if password:
            connect_kwargs["password"] = password
        if key_path:
            key_expanded = os.path.expanduser(key_path)
            connect_kwargs["key_filename"] = key_expanded
        client.connect(**connect_kwargs)
        with _pool_lock:
            _ssh_pool[conn_key] = client
        transport = client.get_transport()
        remote_version = transport.remote_version if transport else "?"
        return (
            f"✓ SSH conectado: {conn_key}\n"
            f"  Host:    {host_resolved}:{port_resolved}\n"
            f"  Usuario: {user_resolved}\n"
            f"  Versión: {remote_version}\n"
            f"  Clave:   {'SSH key' if key_path else 'password' if password else 'agent/default'}\n"
            f"  Pool ID: {conn_key}"
        )
    except Exception as exc:
        logger.error("ssh_connect %s: %s", conn_key, exc)
        return f"✗ Error conectando a {host_resolved}:{port_resolved} como {user_resolved}: {exc}"

async def ssh_execute(
    connection: Annotated[str, "Pool ID (alias o user@host:port) de la conexión activa."],
    command: Annotated[str, "Comando shell a ejecutar en el servidor remoto."],
    timeout: Annotated[int, "Timeout en segundos. Default 60."] = 60,
    get_pty: Annotated[bool, "Solicitar pseudo-terminal (necesario para sudo interactivo)."] = False,
) -> str:
    """Ejecuta un comando en un servidor remoto vía SSH y devuelve stdout+stderr.

    Ideal para: df -h, ps aux, tail -f logs, service status, sapcontrol, etc.
    Para comandos interactivos complejos usa start_process con SSH.
    """
    with _pool_lock:
        client = _ssh_pool.get(connection)
    if client is None:
        return f"[ERROR] No hay conexión activa '{connection}'. Usa ssh_connect primero.\nConexiones activas: {list(_ssh_pool.keys())}"
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout, get_pty=get_pty)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        exit_code = stdout.channel.recv_exit_status()
        result = f"[{connection}] $ {command}\n"
        if out: result += out.rstrip() + "\n"
        if err: result += f"[stderr]\n{err.rstrip()}\n"
        if exit_code != 0: result += f"[Exit code: {exit_code}]"
        return result.rstrip()
    except Exception as exc:
        logger.error("ssh_execute on %s: %s", connection, exc)
        return f"[ERROR] ssh_execute falló en '{connection}': {exc}"


def _normalize_remote_script(script: str) -> str:
    """Evita problemas típicos de CRLF al pegar scripts desde Windows."""
    return script.replace("\r\n", "\n").replace("\r", "\n")


async def ssh_run_bash_script(
    connection: Annotated[str, "Pool ID (alias o user@host:port) de la conexión activa."],
    script: Annotated[str, "Script bash completo; se envía por stdin a `bash -s` (sin quoting frágil)."],
    timeout: Annotated[int, "Timeout en segundos. Default 120."] = 120,
) -> str:
    """Ejecuta un script remoto vía `bash -s` leyendo el cuerpo por stdin.

    Equivalente robusto a: `ssh user@host 'bash -s' < script.sh`
    Úsalo para bloques medianos/largos en lugar de embebidos en una sola línea
    (evita quoting roto PowerShell → SSH → bash y CRLF raros).
    """
    with _pool_lock:
        client = _ssh_pool.get(connection)
    if client is None:
        return f"[ERROR] No hay conexión activa '{connection}'. Usa ssh_connect primero.\nConexiones activas: {list(_ssh_pool.keys())}"
    body = _normalize_remote_script(script)
    if not body.strip():
        return "[ERROR] script vacío."
    try:
        stdin, stdout, stderr = client.exec_command("bash -s", timeout=timeout, get_pty=False)
        stdin.write(body.encode("utf-8"))
        stdin.channel.shutdown_write()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        exit_code = stdout.channel.recv_exit_status()
        preview = body[:200].replace("\n", "\\n")
        if len(body) > 200:
            preview += "..."
        result = (
            f"[{connection}] bash -s (stdin, {len(body)} bytes)\n"
            f"[script preview] {preview}\n"
        )
        if out.strip():
            result += out.rstrip() + "\n"
        if err.strip():
            result += f"[stderr]\n{err.rstrip()}\n"
        if exit_code != 0:
            result += f"[Exit code: {exit_code}]"
        return result.rstrip()
    except Exception as exc:
        logger.error("ssh_run_bash_script on %s: %s", connection, exc)
        return f"[ERROR] ssh_run_bash_script falló en '{connection}': {exc}"


async def ssh_upload(
    connection: Annotated[str, "Pool ID de la conexión activa."],
    local_path: Annotated[str, "Ruta local del fichero a subir."],
    remote_path: Annotated[str, "Ruta destino en el servidor remoto."],
) -> str:
    """Sube un fichero local al servidor remoto vía SFTP."""
    with _pool_lock:
        client = _ssh_pool.get(connection)
    if client is None:
        return f"[ERROR] No hay conexión activa '{connection}'."
    try:
        sftp = client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
        stat = Path(local_path).stat()
        size = stat.st_size
        return f"✓ Subido: {local_path} → {connection}:{remote_path}  ({size:,} bytes)"
    except Exception as exc:
        return f"[ERROR] sftp upload falló: {exc}"


async def ssh_download(
    connection: Annotated[str, "Pool ID de la conexión activa."],
    remote_path: Annotated[str, "Ruta del fichero en el servidor remoto."],
    local_path: Annotated[str, "Ruta local donde guardar el fichero."],
) -> str:
    """Descarga un fichero del servidor remoto vía SFTP."""
    with _pool_lock:
        client = _ssh_pool.get(connection)
    if client is None:
        return f"[ERROR] No hay conexión activa '{connection}'."
    try:
        sftp = client.open_sftp()
        sftp.get(remote_path, local_path)
        sftp.close()
        size = Path(local_path).stat().st_size
        return f"✓ Descargado: {connection}:{remote_path} → {local_path}  ({size:,} bytes)"
    except Exception as exc:
        return f"[ERROR] sftp download falló: {exc}"


async def ssh_list_connections() -> str:
    """Lista todas las conexiones SSH activas en el pool."""
    with _pool_lock:
        if not _ssh_pool:
            return "No hay conexiones SSH activas. Usa ssh_connect para conectar."
        lines = ["Conexiones SSH activas:", "-" * 40]
        for key, client in _ssh_pool.items():
            try:
                transport = client.get_transport()
                active = "activa" if transport and transport.is_active() else "cerrada"
            except Exception:
                active = "?"
            lines.append(f"  {key}  [{active}]")
        return "\n".join(lines)


async def ssh_disconnect(
    connection: Annotated[str, "Pool ID de la conexión a cerrar. 'all' para cerrar todas."],
) -> str:
    """Cierra una conexión SSH activa (o todas con 'all')."""
    with _pool_lock:
        if connection == "all":
            keys = list(_ssh_pool.keys())
            for k in keys:
                try: _ssh_pool[k].close()
                except Exception: pass
                del _ssh_pool[k]
            return f"Cerradas {len(keys)} conexión(es): {keys}"
        if connection not in _ssh_pool:
            return f"[ERROR] No existe conexión '{connection}'. Activas: {list(_ssh_pool.keys())}"
        try: _ssh_pool[connection].close()
        except Exception: pass
        del _ssh_pool[connection]
        return f"✓ Conexión '{connection}' cerrada."
