#!/usr/bin/env python3
"""
SAPladdin - Smoke test de conectividad completo.

Recorre todos los hosts de hosts.yaml y verifica:
  - TCP reachability (todos los tipos)
  - SSH login real (linux_ssh, windows_ssh)
  - DB connection (oracle, mssql, hana)

Uso:
    python scripts/smoke_test.py
    python scripts/smoke_test.py --type linux_ssh
    python scripts/smoke_test.py --alias sapapp1
    python scripts/smoke_test.py --fast   # solo TCP, sin logins
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Asegurar que el proyecto esté en el path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.hosts import _load_hosts
from core.tools.hosts_mgmt import test_host_connection


async def tcp_check(host: dict) -> tuple[str, str, str]:
    """Retorna (alias, tipo, resultado TCP)."""
    from core.tools.hosts_mgmt import test_host_connection
    alias = host.get("alias") or host.get("name", "?")
    htype = host.get("type", "?")
    result = await test_host_connection(alias)
    status = "✓ TCP OK" if "ABIERTO" in result else "✗ TCP FAIL"
    return alias, htype, result


async def ssh_check(host: dict) -> tuple[str, str]:
    """Retorna (alias, resultado SSH login)."""
    from core.tools.ssh import ssh_connect, ssh_execute, ssh_disconnect
    alias = host.get("alias") or host.get("name", "?")
    result = await ssh_connect(alias=alias)
    if result.startswith("✓"):
        # Quick sanity command
        out = await ssh_execute(alias, "uname -a || ver", timeout=10)
        await ssh_disconnect(alias)
        return alias, f"✓ SSH OK | {out.splitlines()[0][:60] if out else ''}"
    return alias, f"✗ SSH FAIL | {result[:80]}"


async def oracle_check(host: dict) -> tuple[str, str]:
    from core.tools.oracle import oracle_test_connection
    alias = host.get("alias") or host.get("name", "?")
    result = await oracle_test_connection(alias=alias)
    status = "✓" if result.startswith("✓") else "✗"
    return alias, f"{status} Oracle | {result.splitlines()[0][:80]}"


async def mssql_check(host: dict) -> tuple[str, str]:
    from core.tools.mssql import mssql_test_connection
    alias = host.get("alias") or host.get("name", "?")
    result = await mssql_test_connection(alias=alias)
    status = "✓" if result.startswith("✓") else "✗"
    return alias, f"{status} MSSQL | {result.splitlines()[0][:80]}"


async def hana_check(host: dict) -> tuple[str, str]:
    from core.tools.hana import hana_test_connection
    alias = host.get("alias") or host.get("name", "?")
    result = await hana_test_connection()
    status = "✓" if result.startswith("✓") else "✗"
    return alias, f"{status} HANA | {result.splitlines()[0][:80]}"


async def run_smoke_test(type_filter: str = "", alias_filter: str = "", fast: bool = False):
    hosts = _load_hosts()
    if not hosts:
        print("⚠ No hay hosts configurados en config/hosts.yaml")
        print("  Copia config/hosts.yaml.example → config/hosts.yaml y rellena tus sistemas.")
        return

    if type_filter:
        hosts = [h for h in hosts if h.get("type") == type_filter]
    if alias_filter:
        hosts = [h for h in hosts if h.get("alias") == alias_filter or h.get("name") == alias_filter]

    if not hosts:
        print(f"⚠ No hay hosts con los filtros: type={type_filter!r} alias={alias_filter!r}")
        return

    print(f"\n{'='*65}")
    print(f"  SAPladdin Smoke Test — {len(hosts)} host(s)")
    print(f"{'='*65}\n")

    results = []

    for host in hosts:
        alias = host.get("alias") or host.get("name", "?")
        htype = host.get("type", "?")
        ip = host.get("ip") or host.get("host", "?")
        port = host.get("port", "?")

        print(f"  [{htype:12s}]  {alias:<20}  {ip}:{port}")

        # TCP check (siempre)
        _, _, tcp_result = await tcp_check(host)
        tcp_ok = "ABIERTO" in tcp_result
        print(f"    TCP:  {'✓ OK' if tcp_ok else '✗ FAIL'}")
        results.append({"alias": alias, "type": htype, "tcp": tcp_ok, "detail": tcp_result})

        if fast or not tcp_ok:
            print()
            continue

        # Login checks según tipo
        try:
            if htype in ("linux_ssh", "windows_ssh"):
                _, ssh_result = await ssh_check(host)
                ok = ssh_result.startswith("✓")
                print(f"    SSH:  {ssh_result[:70]}")
                results[-1]["ssh"] = ok
            elif htype == "oracle":
                _, ora_result = await oracle_check(host)
                ok = ora_result.startswith("✓")
                print(f"    DB:   {ora_result[:70]}")
                results[-1]["db"] = ok
            elif htype == "mssql":
                _, sql_result = await mssql_check(host)
                ok = sql_result.startswith("✓")
                print(f"    DB:   {sql_result[:70]}")
                results[-1]["db"] = ok
            elif htype == "hana":
                _, hana_result = await hana_check(host)
                ok = hana_result.startswith("✓")
                print(f"    DB:   {hana_result[:70]}")
                results[-1]["db"] = ok
        except Exception as exc:
            print(f"    ERR:  {exc}")
        print()

    # Resumen final
    total = len(results)
    tcp_ok = sum(1 for r in results if r.get("tcp"))
    db_ok = sum(1 for r in results if r.get("db") or r.get("ssh"))
    failed = [r["alias"] for r in results if not r.get("tcp")]

    print(f"{'='*65}")
    print(f"  Resumen: {total} hosts | TCP OK: {tcp_ok}/{total}", end="")
    if not fast:
        print(f" | Login OK: {db_ok}/{total}", end="")
    print()
    if failed:
        print(f"  Sin alcanzar (TCP): {', '.join(failed)}")
    print(f"{'='*65}\n")


def main():
    parser = argparse.ArgumentParser(description="SAPladdin smoke test")
    parser.add_argument("--type", default="", help="Filtrar por tipo: linux_ssh, oracle, mssql, hana")
    parser.add_argument("--alias", default="", help="Probar un host concreto por alias")
    parser.add_argument("--fast", action="store_true", help="Solo TCP, sin logins")
    args = parser.parse_args()
    asyncio.run(run_smoke_test(args.type, args.alias, args.fast))


if __name__ == "__main__":
    main()
