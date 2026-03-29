"""
SAPladdin - Oracle Database tools (oracledb thin mode).

Thin mode = no Oracle Client instalado, puro Python.
Soporta múltiples conexiones simultáneas identificadas por alias.

Dependencia: pip install oracledb
"""
import logging
import re
from typing import Annotated

logger = logging.getLogger(__name__)
_oracle_pool: dict[str, object] = {}


def _get_oracledb():
    try:
        import oracledb
        return oracledb
    except ImportError:
        raise RuntimeError("oracledb no instalado. Ejecuta: pip install oracledb")


def _format_rows(cursor, max_rows: int) -> str:
    cols = [d[0] for d in cursor.description] if cursor.description else []
    rows = cursor.fetchmany(max_rows)
    if not rows: return "(sin resultados)"
    widths = [len(c) for c in cols]
    str_rows = []
    for row in rows:
        sr = [str(v) if v is not None else "NULL" for v in row]
        str_rows.append(sr)
        for i, v in enumerate(sr): widths[i] = max(widths[i], len(v))
    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    hdr = "| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(cols)) + " |"
    lines = [sep, hdr, sep]
    for row in str_rows:
        lines.append("| " + " | ".join(v.ljust(widths[i]) for i, v in enumerate(row)) + " |")
    lines.append(sep)
    lines.append(f"({len(rows)} fila(s){'  [LÍMITE]' if len(rows) == max_rows else ''})")
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


async def oracle_test_connection(
    alias: Annotated[str, "Alias de la conexión (definido en hosts.yaml o nombre libre)."],
    host: Annotated[str, "IP/hostname del servidor Oracle."] = "",
    port: Annotated[int, "Puerto. Default 1521."] = 1521,
    service: Annotated[str, "Service name o SID. Ej: ORCL, PRD."] = "",
    user: Annotated[str, "Usuario Oracle."] = "",
    password: Annotated[str, "Contraseña Oracle."] = "",
) -> str:
    """Conecta a Oracle y verifica la conexión. Guarda la conexión en el pool bajo el alias."""
    oracledb = _get_oracledb()
    # Intentar cargar desde hosts.yaml si no se pasan parámetros
    h, p, s, u, pw = host, port, service, user, password
    if not host:
        try:
            from core.hosts import get_host_config
            cfg = get_host_config(alias)
            if cfg:
                h = cfg.get("host") or cfg.get("ip", "")
                p = cfg.get("port", 1521)
                s = cfg.get("service") or cfg.get("database", "")
                u = cfg.get("user", "")
                pw = cfg.get("password", "")
        except Exception:
            pass
    if not h or not s or not u:
        return (
            "✗ Parámetros insuficientes.\n"
            "Proporciona host, service y user, o configura el alias en hosts.yaml"
        )
    try:
        dsn = oracledb.makedsn(h, p, service_name=s)
        conn = oracledb.connect(user=u, password=pw, dsn=dsn)
        _oracle_pool[alias] = conn
        cursor = conn.cursor()
        cursor.execute("SELECT BANNER FROM V$VERSION WHERE ROWNUM = 1")
        banner = cursor.fetchone()[0]
        cursor.execute("SELECT SYS_CONTEXT('USERENV','DB_NAME') FROM DUAL")
        db_name = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM V$SESSION WHERE STATUS='ACTIVE'")
        active_sessions = cursor.fetchone()[0]
        cursor.close()
        return (
            f"✓ Conectado a Oracle [{alias}]\n"
            f"  Host:    {h}:{p}/{s}\n"
            f"  Usuario: {u}\n"
            f"  DB:      {db_name}\n"
            f"  Versión: {banner}\n"
            f"  Sesiones activas: {active_sessions}"
        )
    except Exception as exc:
        return f"✗ Error conectando a Oracle [{alias}] {h}:{p}/{s}: {exc}"

async def oracle_execute_query(
    alias: Annotated[str, "Alias de la conexión Oracle activa (ver oracle_test_connection)."],
    sql: Annotated[str, "Sentencia SQL. SELECT, CALL, DML con confirm=True."],
    max_rows: Annotated[int, "Máximo de filas a devolver. Default 200."] = 200,
    confirm_dml: Annotated[bool, "True para ejecutar INSERT/UPDATE/DELETE. Protección DML."] = False,
) -> str:
    """Ejecuta SQL en Oracle y devuelve resultados formateados.

    SELECTs: tabla formateada. DML: requiere confirm_dml=True. Auto-commit en DML.
    Útil para consultar tablas SAP: MARA, VBAK, BKPF, EKKO, etc.
    """
    conn = _oracle_pool.get(alias)
    if conn is None:
        return f"[ERROR] Sin conexión '{alias}'. Usa oracle_test_connection primero.\nActivas: {list(_oracle_pool.keys())}"
    sql_upper = sql.strip().upper()
    is_dml = any(sql_upper.startswith(k) for k in ("INSERT", "UPDATE", "DELETE", "MERGE", "TRUNCATE"))
    if is_dml and not confirm_dml:
        return (
            f"⚠ DML no ejecutado. Pasa confirm_dml=True para confirmar.\n"
            f"SQL pendiente:\n{sql}"
        )
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        if cursor.description:
            result = _format_rows(cursor, max_rows)
        else:
            conn.commit()
            result = f"OK — {cursor.rowcount} fila(s) afectada(s)."
        cursor.close()
        return result
    except Exception as exc:
        return f"Error ejecutando SQL en Oracle [{alias}]: {exc}\n\nSQL: {sql}"


async def oracle_list_schemas(
    alias: Annotated[str, "Alias de la conexión Oracle."],
    filter_name: Annotated[str, "Filtro por nombre (substring). SAP schemas típicos: SAPR3, SAPABAP1."] = "",
) -> str:
    """Lista usuarios/schemas en Oracle. Muestra espacio usado y estado."""
    conn = _oracle_pool.get(alias)
    if conn is None: return f"[ERROR] Sin conexión '{alias}'."
    try:
        cursor = conn.cursor()
        sql = """
            SELECT U.USERNAME, U.ACCOUNT_STATUS, U.DEFAULT_TABLESPACE,
                   ROUND(SUM(S.BYTES)/1024/1024, 2) AS MB_USED
            FROM DBA_USERS U
            LEFT JOIN DBA_SEGMENTS S ON S.OWNER = U.USERNAME
        """
        params: list[str] = []
        if filter_name:
            sql += " WHERE UPPER(U.USERNAME) LIKE UPPER(:filter_name) ESCAPE '\\'"
            params.append(f"%{_escape_like(filter_name)}%")
        sql += " GROUP BY U.USERNAME, U.ACCOUNT_STATUS, U.DEFAULT_TABLESPACE ORDER BY U.USERNAME"
        cursor.execute(sql, params)
        return _format_rows(cursor, 200)
    except Exception as exc:
        return f"Error listando schemas Oracle [{alias}]: {exc}"


async def oracle_describe_table(
    alias: Annotated[str, "Alias de la conexión Oracle."],
    table_name: Annotated[str, "Nombre de tabla. Ej: MARA, VBAK, BKPF."],
    owner: Annotated[str, "Schema/owner. Vacío = usuario conectado."] = "",
) -> str:
    """Describe estructura de una tabla Oracle (columnas, tipos, PK, nullable)."""
    conn = _oracle_pool.get(alias)
    if conn is None: return f"[ERROR] Sin conexión '{alias}'."
    try:
        cursor = conn.cursor()
        effective_owner = _safe_identifier(owner, "owner") if owner else ""
        effective_table = _safe_identifier(table_name, "table_name")
        owner_filter = "AND C.OWNER = :owner" if effective_owner else "AND C.OWNER = USER"
        pk_owner_filter = "AND CON.OWNER = :owner" if effective_owner else "AND CON.OWNER = USER"
        sql = f"""
            SELECT C.COLUMN_ID, C.COLUMN_NAME, C.DATA_TYPE,
                   NVL(TO_CHAR(C.DATA_LENGTH),'') AS LENGTH,
                   C.NULLABLE,
                   CASE WHEN P.COLUMN_NAME IS NOT NULL THEN 'PK' ELSE '' END AS PK,
                   NVL(C.DATA_DEFAULT,'') AS DEFAULT_VAL
            FROM ALL_TAB_COLUMNS C
            LEFT JOIN (
                SELECT CC.COLUMN_NAME FROM ALL_CONSTRAINTS CON
                JOIN ALL_CONS_COLUMNS CC ON CON.CONSTRAINT_NAME = CC.CONSTRAINT_NAME
                    AND CON.OWNER = CC.OWNER
                WHERE CON.CONSTRAINT_TYPE = 'P'
                  AND CC.TABLE_NAME = :table_name
                  {pk_owner_filter}
            ) P ON C.COLUMN_NAME = P.COLUMN_NAME
            WHERE C.TABLE_NAME = :table_name
            {owner_filter}
            ORDER BY C.COLUMN_ID
        """
        params = {"table_name": effective_table}
        if effective_owner:
            params["owner"] = effective_owner
        cursor.execute(sql, params)
        result = _format_rows(cursor, 500)
        cursor.close()
        schema_label = effective_owner or "current user"
        return f"Tabla: {schema_label}.{effective_table}\n\n{result}"
    except Exception as exc:
        return f"Error describiendo tabla Oracle [{alias}]: {exc}"


async def oracle_get_system_info(alias: Annotated[str, "Alias de la conexión Oracle."]) -> str:
    """Información del sistema Oracle: versión, tablespaces, sesiones, SGA."""
    conn = _oracle_pool.get(alias)
    if conn is None: return f"[ERROR] Sin conexión '{alias}'."
    try:
        cursor = conn.cursor()
        sections = []
        cursor.execute("SELECT BANNER FROM V$VERSION")
        sections.append("=== VERSIÓN ===")
        for row in cursor.fetchall(): sections.append(f"  {row[0]}")
        cursor.execute("SELECT NAME, OPEN_MODE, DB_UNIQUE_NAME FROM V$DATABASE")
        row = cursor.fetchone()
        sections.append(f"\n=== BASE DE DATOS: {row[0]} | Modo: {row[1]} | Unique: {row[2]} ===")
        cursor.execute("""
            SELECT TABLESPACE_NAME,
                   ROUND((TOTAL_SPACE - FREE_SPACE)/1024, 2) AS USED_GB,
                   ROUND(TOTAL_SPACE/1024, 2) AS TOTAL_GB,
                   ROUND(FREE_SPACE/1024, 2) AS FREE_GB
            FROM (SELECT TABLESPACE_NAME,
                         SUM(BYTES)/1024/1024 AS TOTAL_SPACE
                  FROM DBA_DATA_FILES GROUP BY TABLESPACE_NAME) T
            JOIN (SELECT TABLESPACE_NAME,
                         SUM(BYTES)/1024/1024 AS FREE_SPACE
                  FROM DBA_FREE_SPACE GROUP BY TABLESPACE_NAME) F USING (TABLESPACE_NAME)
            ORDER BY USED_GB DESC
        """)
        sections.append("\n=== TABLESPACES (GB) ===")
        sections.append(_format_rows(cursor, 30))
        cursor.execute("SELECT STATUS, COUNT(*) FROM V$SESSION GROUP BY STATUS ORDER BY STATUS")
        sections.append("\n=== SESIONES ===")
        sections.append(_format_rows(cursor, 20))
        cursor.close()
        return "\n".join(sections)
    except Exception as exc:
        return f"Error obteniendo system info Oracle [{alias}]: {exc}"


async def oracle_check_tablespace_sap(
    alias: Annotated[str, "Alias de la conexión Oracle."],
    threshold_pct: Annotated[int, "Alertar si el uso supera este porcentaje. Default 80."] = 80,
    schema_owner: Annotated[str, "Owner SAP para filtrar. Ej: SAPR3, SAPABAP1. Vacío = todos."] = "",
) -> str:
    """Monitorización de tablespaces optimizada para landscapes SAP.

    Muestra: uso %, espacio libre, autoextend, segmentos más grandes del owner SAP.
    Especialmente útil para monitorizar PSAP*, TEMP, UNDO en producción.
    """
    from core.tools.oracle import _oracle_pool, _format_rows
    conn = _oracle_pool.get(alias)
    if conn is None:
        return f"[ERROR] Sin conexión Oracle '{alias}'. Usa oracle_test_connection primero."
    try:
        cursor = conn.cursor()
        sections = []

        # Tablespace usage con autoextend info
        cursor.execute("""
            SELECT
                df.TABLESPACE_NAME,
                ROUND(df.TOTAL_MB, 0)                          AS TOTAL_MB,
                ROUND(df.TOTAL_MB - NVL(fs.FREE_MB, 0), 0)    AS USED_MB,
                ROUND(NVL(fs.FREE_MB, 0), 0)                   AS FREE_MB,
                ROUND((1 - NVL(fs.FREE_MB,0)/df.TOTAL_MB)*100, 1) AS USED_PCT,
                df.AUTOEXTEND,
                ROUND(df.MAX_MB, 0)                            AS MAX_MB
            FROM
                (SELECT TABLESPACE_NAME,
                        SUM(BYTES)/1024/1024 AS TOTAL_MB,
                        MAX(AUTOEXTENSIBLE)  AS AUTOEXTEND,
                        SUM(DECODE(AUTOEXTENSIBLE,'YES',MAXBYTES,BYTES))/1024/1024 AS MAX_MB
                 FROM DBA_DATA_FILES GROUP BY TABLESPACE_NAME) df
            LEFT JOIN
                (SELECT TABLESPACE_NAME, SUM(BYTES)/1024/1024 AS FREE_MB
                 FROM DBA_FREE_SPACE GROUP BY TABLESPACE_NAME) fs
            ON df.TABLESPACE_NAME = fs.TABLESPACE_NAME
            ORDER BY USED_PCT DESC NULLS LAST
        """)
        ts_result = _format_rows(cursor, 50)
        sections.append("=== TABLESPACES ===\n" + ts_result)

        # Tablespaces críticos por encima del threshold
        cursor.execute(f"""
            SELECT df.TABLESPACE_NAME,
                   ROUND((1 - NVL(fs.FREE_MB,0)/df.TOTAL_MB)*100, 1) AS USED_PCT
            FROM
                (SELECT TABLESPACE_NAME, SUM(BYTES)/1024/1024 AS TOTAL_MB
                 FROM DBA_DATA_FILES GROUP BY TABLESPACE_NAME) df
            LEFT JOIN
                (SELECT TABLESPACE_NAME, SUM(BYTES)/1024/1024 AS FREE_MB
                 FROM DBA_FREE_SPACE GROUP BY TABLESPACE_NAME) fs
            ON df.TABLESPACE_NAME = fs.TABLESPACE_NAME
            WHERE ROUND((1 - NVL(fs.FREE_MB,0)/df.TOTAL_MB)*100, 1) >= {threshold_pct}
            ORDER BY USED_PCT DESC
        """)
        critical = cursor.fetchall()
        if critical:
            alert_lines = [f"  ⚠ {row[0]}: {row[1]}%" for row in critical]
            sections.append(
                f"=== ALERTAS (>{threshold_pct}%) ===\n" + "\n".join(alert_lines)
            )
        else:
            sections.append(f"=== Sin tablespaces por encima de {threshold_pct}% ✓ ===")

        # Top 10 segmentos del owner SAP
        if schema_owner:
            owner_safe = schema_owner.strip().upper()
            cursor.execute(f"""
                SELECT SEGMENT_NAME, SEGMENT_TYPE,
                       ROUND(BYTES/1024/1024, 1) AS MB
                FROM DBA_SEGMENTS
                WHERE OWNER = '{owner_safe}'
                ORDER BY BYTES DESC FETCH FIRST 10 ROWS ONLY
            """)
            top_seg = _format_rows(cursor, 10)
            sections.append(f"=== TOP 10 SEGMENTOS ({owner_safe}) ===\n" + top_seg)

        cursor.close()
        return "\n\n".join(sections)
    except Exception as exc:
        return f"Error en oracle_check_tablespace_sap [{alias}]: {exc}"
