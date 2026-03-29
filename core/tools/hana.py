"""
SAPladdin - Tools de gestión SAP HANA Cloud (hdbcli).

Permite conectar, consultar y administrar SAP HANA Cloud desde SAPladdin.
Puede reutilizar la configuración local del propio proyecto y, como fallback,
la de DesktopCommanderPy para facilitar migración entre ambos repos.
"""

import logging
import os
import re
from pathlib import Path
from typing import Annotated

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent.parent


def _candidate_config_paths() -> list[Path]:
    return [
        _PROJECT_ROOT / "config" / "hana_config.yaml",
        Path.home() / "DesktopCommanderPy" / "config" / "hana_config.yaml",
    ]


def _load_hana_config() -> dict:
    """
    Carga configuración HANA desde:
      1. Variables de entorno
      2. config/hana_config.yaml de SAPladdin
      3. config/hana_config.yaml de DesktopCommanderPy
      4. Defaults vacíos
    """
    config = {
        "host": "",
        "port": 443,
        "user": "",
        "password": "",
        "encrypt": True,
        "sslValidateCertificate": True,
        "max_rows": 500,
        "schema": "",
    }

    env_map = {
        "HANA_HOST": "host",
        "HANA_PORT": "port",
        "HANA_USER": "user",
        "HANA_PASSWORD": "password",
        "HANA_SCHEMA": "schema",
    }
    for env_key, cfg_key in env_map.items():
        val = os.environ.get(env_key)
        if val:
            config[cfg_key] = int(val) if cfg_key == "port" else val

    for yaml_path in _candidate_config_paths():
        if not yaml_path.exists():
            continue
        try:
            import yaml

            with open(yaml_path, "r", encoding="utf-8") as f:
                file_cfg = yaml.safe_load(f) or {}
            hana_section = file_cfg.get("hana", {})
            for key, value in hana_section.items():
                if key in config and value not in ("", None):
                    config[key] = value
            logger.debug("HANA config loaded from %s", yaml_path)
        except Exception as exc:
            logger.warning("Could not load %s: %s", yaml_path, exc)

    return config


def _get_connection():
    """Abre y devuelve una conexión hdbcli. Lanza RuntimeError si falla."""
    try:
        from hdbcli import dbapi
    except ImportError:
        raise RuntimeError(
            "hdbcli no está instalado. Ejecuta: "
            "pip install hdbcli  (dentro del venv del proyecto)"
        )

    cfg = _load_hana_config()

    if not cfg["host"] or not cfg["user"] or not cfg["password"]:
        raise RuntimeError(
            "Credenciales HANA no configuradas.\n"
            "Opciones:\n"
            "  A) Variables de entorno: HANA_HOST, HANA_USER, HANA_PASSWORD\n"
            "  B) Fichero config/hana_config.yaml de SAPladdin\n"
            "  C) Fichero config/hana_config.yaml de DesktopCommanderPy"
        )

    conn = dbapi.connect(
        address=cfg["host"],
        port=int(cfg["port"]),
        user=cfg["user"],
        password=cfg["password"],
        encrypt=cfg.get("encrypt", True),
        sslValidateCertificate=cfg.get("sslValidateCertificate", True),
    )
    return conn, cfg


def _format_results(cursor, max_rows: int) -> str:
    """Formatea resultados de cursor como tabla de texto."""
    cols = [d[0] for d in cursor.description] if cursor.description else []
    rows = cursor.fetchmany(max_rows)

    if not rows:
        return "(sin resultados)"

    widths = [len(c) for c in cols]
    str_rows = []
    for row in rows:
        str_row = [str(v) if v is not None else "NULL" for v in row]
        str_rows.append(str_row)
        for i, val in enumerate(str_row):
            widths[i] = max(widths[i], len(val))

    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    header = "| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(cols)) + " |"
    lines = [sep, header, sep]
    for row in str_rows:
        lines.append("| " + " | ".join(v.ljust(widths[i]) for i, v in enumerate(row)) + " |")
    lines.append(sep)
    lines.append(f"({len(rows)} fila(s){'  [LÍMITE ALCANZADO]' if len(rows) == max_rows else ''})")
    return "\n".join(lines)


def _safe_identifier(name: str, label: str = "identifier") -> str:
    value = name.strip()
    if not value:
        raise ValueError(f"{label} vacío.")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_#$]*", value):
        raise ValueError(
            f"{label} inválido: {name!r}. Solo se permiten letras, números, _, # y $."
        )
    return value.upper()


def _escape_like(filter_value: str) -> str:
    return (
        filter_value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def _effective_schema(cursor, cfg: dict, schema: str) -> str:
    if schema:
        return _safe_identifier(schema, "schema")
    configured = cfg.get("schema", "")
    if configured:
        return _safe_identifier(configured, "schema")
    cursor.execute("SELECT CURRENT_SCHEMA FROM DUMMY")
    return _safe_identifier(cursor.fetchone()[0], "schema")


async def hana_test_connection() -> str:
    """Prueba la conexión a SAP HANA Cloud y devuelve información del servidor."""
    try:
        conn, cfg = _get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT VERSION FROM SYS.M_DATABASE")
        version = cursor.fetchone()[0]

        cursor.execute("SELECT CURRENT_USER, CURRENT_SCHEMA FROM DUMMY")
        row = cursor.fetchone()
        current_user = row[0]
        current_schema = row[1]

        cursor.execute("SELECT COUNT(*) FROM SYS.M_CONNECTIONS WHERE OWN = 'TRUE'")
        own_connections = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return (
            f"✓ Conexión exitosa a SAP HANA Cloud\n"
            f"  Host:           {cfg['host']}:{cfg['port']}\n"
            f"  Usuario:        {current_user}\n"
            f"  Schema actual:  {current_schema}\n"
            f"  Versión HANA:   {version}\n"
            f"  Conexiones propias activas: {own_connections}\n"
            f"  SSL/TLS:        {'activado' if cfg.get('encrypt') else 'desactivado'}"
        )
    except Exception as exc:
        logger.error("hana_test_connection failed: %s", exc)
        return f"✗ Error de conexión: {exc}"


async def hana_execute_query(
    sql: Annotated[str, "Sentencia SQL a ejecutar (SELECT, CALL, etc.). Una sola sentencia."],
    schema: Annotated[str, "Schema a usar. Vacío = usar el configurado por defecto."] = "",
    max_rows: Annotated[int, "Máximo de filas a devolver. Default 200."] = 200,
) -> str:
    """Ejecuta una sentencia SQL en SAP HANA Cloud y devuelve los resultados."""
    try:
        conn, cfg = _get_connection()
        cursor = conn.cursor()

        effective_schema = _effective_schema(cursor, cfg, schema) if schema or cfg.get("schema") else ""
        if effective_schema:
            cursor.execute(f'SET SCHEMA "{effective_schema}"')

        cursor.execute(sql)

        if cursor.description:
            result = _format_results(cursor, max_rows)
        else:
            rows_affected = cursor.rowcount
            conn.commit()
            result = f"OK — {rows_affected} fila(s) afectada(s)."

        cursor.close()
        conn.close()
        return result

    except Exception as exc:
        logger.error("hana_execute_query failed: %s", exc)
        return f"Error ejecutando SQL: {exc}\n\nSQL: {sql}"


async def hana_list_schemas(
    filter_name: Annotated[str, "Filtro por nombre de schema (substring). Vacío = todos los visibles."] = "",
) -> str:
    """Lista los schemas visibles para el usuario actual en SAP HANA Cloud."""
    try:
        conn, _ = _get_connection()
        cursor = conn.cursor()

        sql = """
            SELECT SCHEMA_NAME, SCHEMA_OWNER,
                   CASE WHEN SCHEMA_NAME LIKE '_SYS%' OR SCHEMA_NAME IN ('SYS','SYSTEM','PUBLIC')
                        THEN 'SÍ' ELSE 'NO' END AS IS_SYSTEM
            FROM SYS.SCHEMAS
            WHERE HAS_PRIVILEGES = 'TRUE'
        """
        params: list[str] = []
        if filter_name:
            sql += " AND UPPER(SCHEMA_NAME) LIKE UPPER(?) ESCAPE '\\'"
            params.append(f"%{_escape_like(filter_name)}%")
        sql += " ORDER BY IS_SYSTEM, SCHEMA_NAME"

        cursor.execute(sql, params)
        result = _format_results(cursor, 200)
        cursor.close()
        conn.close()
        return result

    except Exception as exc:
        return f"Error listando schemas: {exc}"


async def hana_list_tables(
    schema: Annotated[str, "Schema del que listar tablas. Vacío = schema actual del usuario."] = "",
    filter_name: Annotated[str, "Filtro por nombre de tabla (substring, case-insensitive)."] = "",
    table_type: Annotated[str, "Tipo: TABLE, VIEW, CALC VIEW, o vacío para todos."] = "",
) -> str:
    """Lista tablas, vistas y Calculation Views de un schema en SAP HANA Cloud."""
    try:
        conn, cfg = _get_connection()
        cursor = conn.cursor()

        effective_schema = _effective_schema(cursor, cfg, schema)
        sql = """
            SELECT T.TABLE_NAME, T.TABLE_TYPE,
                   COUNT(C.COLUMN_NAME) AS NUM_COLUMNS,
                   T.COMMENTS
            FROM SYS.TABLES T
            LEFT JOIN SYS.TABLE_COLUMNS C
                ON T.SCHEMA_NAME = C.SCHEMA_NAME AND T.TABLE_NAME = C.TABLE_NAME
            WHERE T.SCHEMA_NAME = ?
        """
        params: list[str] = [effective_schema]
        if filter_name:
            sql += " AND UPPER(T.TABLE_NAME) LIKE UPPER(?) ESCAPE '\\'"
            params.append(f"%{_escape_like(filter_name)}%")
        if table_type:
            sql += " AND T.TABLE_TYPE = ?"
            params.append(table_type.strip().upper())

        sql += " GROUP BY T.TABLE_NAME, T.TABLE_TYPE, T.COMMENTS ORDER BY T.TABLE_TYPE, T.TABLE_NAME"

        cursor.execute(sql, params)
        result = _format_results(cursor, 300)
        cursor.close()
        conn.close()
        return f"Schema: {effective_schema}\n\n{result}"

    except Exception as exc:
        return f"Error listando tablas: {exc}"


async def hana_describe_table(
    table_name: Annotated[str, "Nombre de la tabla o vista."],
    schema: Annotated[str, "Schema. Vacío = schema actual."] = "",
) -> str:
    """Describe la estructura de una tabla en SAP HANA Cloud."""
    try:
        conn, cfg = _get_connection()
        cursor = conn.cursor()

        effective_schema = _effective_schema(cursor, cfg, schema)
        effective_table = _safe_identifier(table_name, "table_name")

        sql = """
            SELECT
                C.POSITION,
                C.COLUMN_NAME,
                C.DATA_TYPE_NAME,
                CASE WHEN C.LENGTH IS NOT NULL THEN CAST(C.LENGTH AS VARCHAR)
                     ELSE '' END AS LENGTH,
                CASE WHEN C.SCALE IS NOT NULL THEN CAST(C.SCALE AS VARCHAR)
                     ELSE '' END AS SCALE,
                C.IS_NULLABLE,
                CASE WHEN K.COLUMN_NAME IS NOT NULL THEN 'PK' ELSE '' END AS PK,
                COALESCE(C.COMMENTS, '') AS COMMENTS
            FROM SYS.TABLE_COLUMNS C
            LEFT JOIN (
                SELECT COLUMN_NAME FROM SYS.CONSTRAINTS
                WHERE SCHEMA_NAME = ?
                  AND TABLE_NAME  = ?
                  AND IS_PRIMARY_KEY = 'TRUE'
            ) K ON C.COLUMN_NAME = K.COLUMN_NAME
            WHERE C.SCHEMA_NAME = ?
              AND C.TABLE_NAME  = ?
            ORDER BY C.POSITION
        """
        cursor.execute(sql, [effective_schema, effective_table, effective_schema, effective_table])
        result = _format_results(cursor, 500)
        cursor.close()
        conn.close()
        return f"Tabla: {effective_schema}.{effective_table}\n\n{result}"

    except Exception as exc:
        return f"Error describiendo tabla: {exc}"


async def hana_get_row_count(
    tables: Annotated[str, "Tabla o tablas separadas por coma. Ej: ORDERS,ITEMS,CUSTOMERS"],
    schema: Annotated[str, "Schema. Vacío = schema actual."] = "",
) -> str:
    """Devuelve el número de filas de una o varias tablas."""
    try:
        conn, cfg = _get_connection()
        cursor = conn.cursor()

        effective_schema = _effective_schema(cursor, cfg, schema)
        table_list = [_safe_identifier(t, "table_name") for t in tables.split(",") if t.strip()]
        if not table_list:
            return "Error obteniendo row counts: no se proporcionaron tablas válidas."

        placeholders = ", ".join("?" for _ in table_list)
        sql = f"""
            SELECT TABLE_NAME,
                   TO_BIGINT(RECORD_COUNT) AS ROW_COUNT,
                   TO_BIGINT(TABLE_SIZE / 1024 / 1024) AS SIZE_MB
            FROM SYS.M_TABLE_STATISTICS
            WHERE SCHEMA_NAME = ?
              AND TABLE_NAME IN ({placeholders})
            ORDER BY TABLE_NAME
        """
        cursor.execute(sql, [effective_schema, *table_list])
        result = _format_results(cursor, 100)
        cursor.close()
        conn.close()
        return f"Schema: {effective_schema}\n\n{result}"

    except Exception as exc:
        return f"Error obteniendo row counts: {exc}"


async def hana_get_system_info() -> str:
    """Devuelve información del sistema SAP HANA Cloud: memoria, CPU, alertas activas."""
    try:
        conn, _ = _get_connection()
        cursor = conn.cursor()
        sections = []

        cursor.execute("SELECT SECTION, NAME, STATUS, VALUE FROM SYS.M_SYSTEM_OVERVIEW ORDER BY SECTION, NAME")
        rows = cursor.fetchall()
        sections.append("=== SYSTEM OVERVIEW ===")
        current_section = None
        for row in rows:
            if row[0] != current_section:
                current_section = row[0]
                sections.append(f"  [{current_section}]")
            status_str = f" [{row[2]}]" if row[2] else ""
            sections.append(f"    {row[1]}: {row[3]}{status_str}")

        cursor.execute("SELECT COUNT(*) FROM SYS.M_CONNECTIONS WHERE CONNECTION_STATUS = 'RUNNING'")
        active_conn = cursor.fetchone()[0]
        sections.append(f"\n=== CONEXIONES ACTIVAS: {active_conn} ===")

        cursor.close()
        conn.close()
        return "\n".join(sections)

    except Exception as exc:
        return f"Error obteniendo info del sistema: {exc}"


async def hana_execute_ddl(
    sql: Annotated[str, "Sentencia DDL (CREATE, ALTER, DROP, GRANT, REVOKE...)."],
    confirm: Annotated[bool, "Debes pasar confirm=True explícitamente para ejecutar DDL. Medida de seguridad."] = False,
) -> str:
    """Ejecuta una sentencia DDL en SAP HANA Cloud (CREATE, ALTER, DROP, GRANT...)."""
    if not confirm:
        return (
            "⚠ Operación DDL NO ejecutada.\n"
            "Las operaciones DDL (CREATE/ALTER/DROP/GRANT/TRUNCATE) requieren "
            "confirmación explícita.\n"
            "Vuelve a llamar con confirm=True si estás seguro.\n\n"
            f"SQL pendiente:\n{sql}"
        )

    try:
        conn, _ = _get_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("DDL ejecutado: %s", sql[:100])
        return f"DDL ejecutado correctamente.\n\nSQL: {sql}"

    except Exception as exc:
        return f"Error ejecutando DDL: {exc}\n\nSQL: {sql}"
