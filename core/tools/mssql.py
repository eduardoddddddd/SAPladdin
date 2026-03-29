"""
SAPladdin - SQL Server tools (pyodbc).

Soporta SQL Server on-premise (Windows/Linux) y Azure SQL.
Múltiples conexiones simultáneas identificadas por alias.

Dependencia: pip install pyodbc
  Windows: driver ODBC 17/18 for SQL Server (viene con SQL Server o descargable)
  Linux:   apt install unixodbc-dev + msodbcsql18
"""
import logging
import re
from typing import Annotated

logger = logging.getLogger(__name__)
_mssql_pool: dict[str, object] = {}


def _get_pyodbc():
    try:
        import pyodbc
        return pyodbc
    except ImportError:
        raise RuntimeError(
            "pyodbc no instalado. Ejecuta: pip install pyodbc\n"
            "También necesitas el driver ODBC: https://docs.microsoft.com/sql/connect/odbc/"
        )


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
    return value


async def mssql_test_connection(
    alias: Annotated[str, "Nombre para identificar esta conexión."],
    host: Annotated[str, "IP/hostname del servidor SQL Server."] = "",
    port: Annotated[int, "Puerto. Default 1433."] = 1433,
    database: Annotated[str, "Base de datos. Default master."] = "master",
    user: Annotated[str, "Usuario SQL. Vacío = Windows Auth."] = "",
    password: Annotated[str, "Contraseña. Vacío = Windows Auth."] = "",
    driver: Annotated[str, "Driver ODBC. Default = ODBC Driver 18 for SQL Server."] = "",
) -> str:
    """Conecta a SQL Server y verifica. Guarda la conexión en el pool bajo el alias."""
    pyodbc = _get_pyodbc()
    h, p, db, u, pw = host, port, database, user, password
    if not host:
        try:
            from core.hosts import get_host_config
            cfg = get_host_config(alias)
            if cfg:
                h = cfg.get("host") or cfg.get("ip", "")
                p = cfg.get("port", 1433)
                db = cfg.get("database", "master")
                u = cfg.get("user", "")
                pw = cfg.get("password", "")
        except Exception:
            pass
    if not h:
        return "✗ Falta host. Proporciona host o configura el alias en hosts.yaml"
    # Detectar driver disponible
    available_drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
    if not driver:
        preferred = ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server",
                     "SQL Server Native Client 11.0", "SQL Server"]
        for pref in preferred:
            if pref in available_drivers:
                driver = pref
                break
        if not driver:
            return (
                f"✗ No se encontró driver ODBC para SQL Server.\n"
                f"Drivers disponibles: {pyodbc.drivers()}\n"
                f"Instala: https://docs.microsoft.com/sql/connect/odbc/"
            )
    try:
        if u and pw:
            conn_str = (f"DRIVER={{{driver}}};SERVER={h},{p};DATABASE={db};"
                        f"UID={u};PWD={pw};TrustServerCertificate=yes;")
        else:
            conn_str = (f"DRIVER={{{driver}}};SERVER={h},{p};DATABASE={db};"
                        f"Trusted_Connection=yes;TrustServerCertificate=yes;")
        conn = pyodbc.connect(conn_str, timeout=15)
        _mssql_pool[alias] = conn
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION, @@SERVERNAME, DB_NAME()")
        row = cursor.fetchone()
        version_short = row[0].split("\n")[0] if row else "?"
        server_name = row[1] if row else "?"
        db_name = row[2] if row else "?"
        cursor.execute("SELECT COUNT(*) FROM sys.dm_exec_sessions WHERE is_user_process = 1")
        sessions = cursor.fetchone()[0]
        cursor.close()
        return (
            f"✓ Conectado a SQL Server [{alias}]\n"
            f"  Host:     {h}:{p}\n"
            f"  Server:   {server_name}\n"
            f"  DB:       {db_name}\n"
            f"  Versión:  {version_short}\n"
            f"  Driver:   {driver}\n"
            f"  Sesiones: {sessions}"
        )
    except Exception as exc:
        return f"✗ Error conectando SQL Server [{alias}] {h}:{p}: {exc}"

async def mssql_execute_query(
    alias: Annotated[str, "Alias de la conexión SQL Server activa."],
    sql: Annotated[str, "SQL a ejecutar."],
    max_rows: Annotated[int, "Máximo de filas. Default 200."] = 200,
    confirm_dml: Annotated[bool, "True para ejecutar INSERT/UPDATE/DELETE."] = False,
) -> str:
    """Ejecuta SQL en SQL Server y devuelve resultados formateados."""
    conn = _mssql_pool.get(alias)
    if conn is None:
        return f"[ERROR] Sin conexión '{alias}'. Usa mssql_test_connection primero.\nActivas: {list(_mssql_pool.keys())}"
    sql_upper = sql.strip().upper()
    is_dml = any(sql_upper.startswith(k) for k in ("INSERT", "UPDATE", "DELETE", "TRUNCATE", "DROP"))
    if is_dml and not confirm_dml:
        return f"⚠ DML no ejecutado. Pasa confirm_dml=True.\nSQL pendiente:\n{sql}"
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
        return f"Error SQL Server [{alias}]: {exc}\n\nSQL: {sql}"


async def mssql_list_databases(
    alias: Annotated[str, "Alias de la conexión SQL Server."],
) -> str:
    """Lista bases de datos del servidor SQL Server con estado y tamaño."""
    conn = _mssql_pool.get(alias)
    if conn is None: return f"[ERROR] Sin conexión '{alias}'."
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT d.name AS DATABASE_NAME, d.state_desc AS STATUS,
                   d.recovery_model_desc AS RECOVERY,
                   ROUND(SUM(mf.size) * 8.0 / 1024, 2) AS SIZE_MB,
                   d.create_date
            FROM sys.databases d
            JOIN sys.master_files mf ON d.database_id = mf.database_id
            GROUP BY d.name, d.state_desc, d.recovery_model_desc, d.create_date
            ORDER BY d.name
        """)
        result = _format_rows(cursor, 100)
        cursor.close()
        return f"Bases de datos en [{alias}]:\n\n{result}"
    except Exception as exc:
        return f"Error listando DBs SQL Server [{alias}]: {exc}"


async def mssql_describe_table(
    alias: Annotated[str, "Alias de la conexión SQL Server."],
    table_name: Annotated[str, "Nombre de la tabla. Ej: dbo.Customer o solo Customer."],
    database: Annotated[str, "Base de datos. Vacío = la conectada por defecto."] = "",
) -> str:
    """Describe estructura de una tabla SQL Server (columnas, tipos, PK, nullable)."""
    conn = _mssql_pool.get(alias)
    if conn is None: return f"[ERROR] Sin conexión '{alias}'."
    try:
        cursor = conn.cursor()
        safe_database = _safe_identifier(database, "database") if database else ""
        db_prefix = f"[{safe_database}]." if safe_database else ""
        # Separar schema.tabla si viene con punto
        parts = table_name.split(".")
        schema = _safe_identifier(parts[0], "schema") if len(parts) > 1 else "dbo"
        tname = _safe_identifier(parts[-1], "table_name")
        sql = f"""
            SELECT c.COLUMN_NAME, c.DATA_TYPE,
                   ISNULL(CAST(c.CHARACTER_MAXIMUM_LENGTH AS VARCHAR), '') AS MAX_LEN,
                   c.IS_NULLABLE,
                   ISNULL(c.COLUMN_DEFAULT, '') AS DEFAULT_VAL,
                   CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 'PK' ELSE '' END AS PK
            FROM {db_prefix}INFORMATION_SCHEMA.COLUMNS c
            LEFT JOIN (
                SELECT ku.COLUMN_NAME FROM {db_prefix}INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                JOIN {db_prefix}INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku
                    ON tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
                WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                  AND ku.TABLE_NAME = ?
                  AND ku.TABLE_SCHEMA = ?
            ) pk ON c.COLUMN_NAME = pk.COLUMN_NAME
            WHERE c.TABLE_NAME = ? AND c.TABLE_SCHEMA = ?
            ORDER BY c.ORDINAL_POSITION
        """
        cursor.execute(sql, (tname, schema, tname, schema))
        result = _format_rows(cursor, 500)
        cursor.close()
        return f"Tabla: {schema}.{tname}\n\n{result}"
    except Exception as exc:
        return f"Error describiendo tabla SQL Server [{alias}]: {exc}"


async def mssql_check_agent_jobs(
    alias: Annotated[str, "Alias de la conexión SQL Server."],
    days_back: Annotated[int, "Historial de los últimos N días. Default 1."] = 1,
    filter_name: Annotated[str, "Filtrar por nombre de job (substring). Vacío = todos."] = "",
    only_failed: Annotated[bool, "True = mostrar solo jobs fallidos. Default False."] = False,
) -> str:
    """Estado de SQL Server Agent Jobs: historial, éxitos/fallos, duración.

    Consulta msdb.dbo.sysjobhistory + sysjobs.
    Útil para verificar backups, mantenimiento y jobs programados.
    """
    conn = _mssql_pool.get(alias)
    if conn is None:
        return f"[ERROR] Sin conexión '{alias}'. Usa mssql_test_connection primero."
    try:
        cursor = conn.cursor()
        sections = []

        # Filtros dinámicos
        name_filter = f"AND j.name LIKE ?" if filter_name else ""
        status_filter = "AND h.run_status = 0" if only_failed else ""
        params = []
        if filter_name:
            params.append(f"%{filter_name}%")

        # Historial de jobs
        cursor.execute(f"""
            SELECT TOP 50
                j.name AS JOB_NAME,
                CASE h.run_status
                    WHEN 0 THEN 'FAILED'
                    WHEN 1 THEN 'SUCCEEDED'
                    WHEN 2 THEN 'RETRY'
                    WHEN 3 THEN 'CANCELLED'
                    WHEN 4 THEN 'RUNNING'
                    ELSE 'UNKNOWN'
                END AS STATUS,
                CONVERT(VARCHAR,
                    DATEADD(s,
                        (h.run_duration/10000*3600 + h.run_duration%10000/100*60 + h.run_duration%100),
                        0), 108) AS DURATION_HMS,
                CAST(h.run_date AS VARCHAR) AS RUN_DATE,
                CAST(h.run_time AS VARCHAR) AS RUN_TIME,
                LEFT(h.message, 100) AS MESSAGE
            FROM msdb.dbo.sysjobhistory h
            JOIN msdb.dbo.sysjobs j ON h.job_id = j.job_id
            WHERE h.step_id = 0
              AND CAST(
                    CAST(h.run_date AS VARCHAR) AS DATE
                  ) >= CAST(DATEADD(day, -{days_back}, GETDATE()) AS DATE)
              {name_filter}
              {status_filter}
            ORDER BY h.run_date DESC, h.run_time DESC
        """, params)
        history = _format_rows(cursor, 50)
        title = f"últimos {days_back} día(s)"
        title += f" | filtro: {filter_name}" if filter_name else ""
        title += " | solo FAILED" if only_failed else ""
        sections.append(f"=== SQL AGENT JOBS ({title}) ===\n" + history)

        # Resumen por estado
        cursor.execute(f"""
            SELECT
                CASE h.run_status
                    WHEN 0 THEN 'FAILED' WHEN 1 THEN 'SUCCEEDED'
                    WHEN 2 THEN 'RETRY'  WHEN 3 THEN 'CANCELLED'
                    ELSE 'OTHER'
                END AS STATUS,
                COUNT(*) AS COUNT
            FROM msdb.dbo.sysjobhistory h
            JOIN msdb.dbo.sysjobs j ON h.job_id = j.job_id
            WHERE h.step_id = 0
              AND CAST(CAST(h.run_date AS VARCHAR) AS DATE) >=
                  CAST(DATEADD(day, -{days_back}, GETDATE()) AS DATE)
              {name_filter}
            GROUP BY h.run_status
            ORDER BY STATUS
        """, params)
        summary = _format_rows(cursor, 10)
        sections.append("=== RESUMEN POR ESTADO ===\n" + summary)

        # Jobs activos ahora mismo
        cursor.execute("""
            SELECT j.name AS JOB_NAME, ja.start_execution_date AS STARTED_AT
            FROM msdb.dbo.sysjobactivity ja
            JOIN msdb.dbo.sysjobs j ON ja.job_id = j.job_id
            WHERE ja.start_execution_date IS NOT NULL
              AND ja.stop_execution_date IS NULL
              AND ja.session_id = (
                SELECT MAX(session_id) FROM msdb.dbo.sysjobactivity
              )
        """)
        running = _format_rows(cursor, 10)
        sections.append("=== JOBS EN EJECUCIÓN AHORA ===\n" + running)

        cursor.close()
        return "\n\n".join(sections)
    except Exception as exc:
        return f"Error mssql_check_agent_jobs [{alias}]: {exc}"
