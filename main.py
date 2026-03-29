"""
SAPladdin - MCP Server para SAP Basis / Linux Admin / DBA

Arranque:
    python main.py                    # stdio (Claude Desktop)
    python main.py --http             # HTTP/SSE (clientes remotos)
    python main.py --http --port 8080

El servidor carga security_config.yaml y hosts.yaml al arrancar.
"""

import argparse
import logging
import sys
from pathlib import Path


def _setup_logging(level: str = "INFO") -> None:
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SAPladdin MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--http", action="store_true",
        help="HTTP/SSE transport en lugar de stdio.")
    parser.add_argument("--port", type=int, default=8080,
        help="Puerto HTTP (default: 8080).")
    parser.add_argument("--host", type=str, default="127.0.0.1",
        help="Host HTTP (default: 127.0.0.1).")
    parser.add_argument("--log-level", type=str, default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--config", type=str,
        default=str(Path(__file__).parent / "config" / "security_config.yaml"))
    args = parser.parse_args()

    _setup_logging(args.log_level)
    logger = logging.getLogger("sapladdin")

    from core.server import get_server
    mcp = get_server()

    if args.http:
        logger.info("SAPladdin arrancando en http://%s:%d (SSE)", args.host, args.port)
        mcp.run(transport="sse", host=args.host, port=args.port, show_banner=False)
    else:
        logger.info("SAPladdin arrancando en stdio")
        # CRITICO: show_banner=False obligatorio en stdio
        # Claude Desktop comunica via JSON-RPC por stdout.
        # Cualquier output no-JSON (banner) corrompe el canal.
        mcp.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
