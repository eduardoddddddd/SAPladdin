"""
SAPladdin - SQL Server tools (pyodbc).

Soporta SQL Server on-premise (Windows/Linux) y Azure SQL.
Múltiples conexiones simultáneas identificadas por alias.

Dependencia: pip install pyodbc
  Windows: driver ODBC 17/18 for SQL Server (viene con SQL Server o descargable)
  Linux:   apt install unixodbc-dev + msodbcsql18
"""
import logging
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
        db_prefix = f"[{database}]." if database else ""
        # Separar schema.tabla si viene con punto
        parts = table_name.split(".")
        schema = parts[0] if len(parts) > 1 else "dbo"
        tname = parts[-1]
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
                  AND ku.TABLE_NAME = '{tname}'
                  AND ku.TABLE_SCHEMA = '{schema}'
            ) pk ON c.COLUMN_NAME = pk.COLUMN_NAME
            WHERE c.TABLE_NAME = '{tname}' AND c.TABLE_SCHEMA = '{schema}'
            ORDER BY c.ORDINAL_POSITION
        """
        cursor.execute(sql)
        result = _format_rows(cursor, 500)
        cursor.close()
        return f"Tabla: {schema}.{tname}\n\n{result}"
    except Exception as exc:
        return f"Error describiendo tabla SQL Server [{alias}]: {exc}"
