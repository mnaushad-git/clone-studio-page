#!/usr/bin/env python3
"""Isolated Terrific Bites integration stack on native Windows services, no Docker needed.

Runs its own PostgreSQL data directory, Odoo process and Memurai instance from the binaries
already installed, on ports nothing else uses. It never touches the shared odoo-server-19.0
or postgresql-x64-16 services, their databases, or the Memurai on 6379. All state lives in
.local-integration/ (git-ignored); delete that folder to start again from nothing.

    backend/.venv/Scripts/python deploy/native/native_stack.py up
    ... app --stage local_integration | status | stop odoo | start odoo | stop all
    ... run --role worker -- python -m app.scripts.process_order_outbox

See docs/deployment/native-integration.md.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
# Overridable so a clean cluster can be built beside one that can't be started or removed.
STATE = Path(os.environ.get("TB_NATIVE_STATE", REPO / ".local-integration"))
RUN = STATE / "run"
LOGS = STATE / "logs"
SECRETS = STATE / "secrets.json"
ODOO_CONF = STATE / "odoo.conf"

PG_BIN = Path(r"C:\Program Files\PostgreSQL\16\bin")
ODOO_HOME = Path(r"C:\Program Files\Odoo 19.0.20260720")
ODOO_PYTHON = ODOO_HOME / "python" / "python.exe"
ODOO_BIN = ODOO_HOME / "server" / "odoo-bin"
ODOO_ADDONS = ODOO_HOME / "server" / "odoo" / "addons"
MEMURAI = Path(r"C:\Program Files\Memurai\memurai.exe")
VENV_PYTHON = BACKEND / ".venv" / "Scripts" / "python.exe"

PG_PORT = int(os.environ.get("TB_NATIVE_PG_PORT", "55440"))
ODOO_PORT = 18069
REDIS_PORT = 16379
API_PORT = 18020
DEMO_API_PORT = 18021
FRONTEND_PORT = 18081
ODOO_DB = "terrific_odoo"
APP_DB = "terrific_bites"
TEST_DB = "terrific_bites_test"
# initdb refuses any role name that starts with "pg_".
ADMIN_ROLE = "tb_admin_role"
# 127.0.0.1, because on Windows "localhost" tries ::1 first and costs 2s on every call.
ODOO_BASE_URL = f"http://127.0.0.1:{ODOO_PORT}"
ORDER_SYNC_LOGIN = "terrific-order-sync"
CATALOGUE_IMPORT_LOGIN = "terrific-catalogue-import"
NATIVE_ADMIN_EMAIL = "native-admin@example.test"
SECRET_NAMES = (
    "pg_admin",
    "app_db",
    "odoo_db",
    "odoo_master",
    "order_sync",
    "catalogue_import",
    "redis",
    "admin_jwt",
    "native_admin",
)
DETACHED = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
ODOO_MODULES = "sale_management,stock,account,website_sale,terrific_order_sync"


def load_secrets() -> dict[str, str]:
    values = json.loads(SECRETS.read_text()) if SECRETS.exists() else {}
    missing = [name for name in SECRET_NAMES if name not in values]
    if missing:
        values.update({name: secrets.token_hex(24) for name in missing})
        STATE.mkdir(parents=True, exist_ok=True)
        SECRETS.write_text(json.dumps(values, indent=2))
    return values


def port_open(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def wait_port(port: int, name: str, timeout: float = 120) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if port_open(port):
            return
        time.sleep(0.5)
    raise SystemExit(
        f"{name} did not open port {port} within {timeout:.0f}s; see {LOGS}"
    )


def run(cmd: list[Any], *, env: dict[str, str] | None = None, **kwargs: Any) -> None:
    subprocess.run([str(part) for part in cmd], check=True, env=env, **kwargs)


def psql(sql: str, secret: dict[str, str], database: str = "postgres") -> None:
    run(
        [
            PG_BIN / "psql.exe",
            "-h", "127.0.0.1", "-p", PG_PORT, "-U", ADMIN_ROLE, "-d", database,
            "-v", "ON_ERROR_STOP=1", "-q", "-c", sql,
        ],
        env={**os.environ, "PGPASSWORD": secret["pg_admin"]},
    )  # fmt: skip


def start_postgres() -> None:
    if port_open(PG_PORT):
        return
    run(
        [
            PG_BIN / "pg_ctl.exe", "-D", STATE / "pg", "-l", LOGS / "postgres.log", "-w", "start",
            "-o", f"-p {PG_PORT} -c listen_addresses=127.0.0.1",
        ],
        creationflags=DETACHED,
    )  # fmt: skip


def init_postgres(secret: dict[str, str]) -> None:
    if (STATE / "pg" / "PG_VERSION").exists():
        start_postgres()
        return
    pwfile = STATE / "pgadmin.pw"
    pwfile.write_text(secret["pg_admin"])
    try:
        run(
            [
                PG_BIN / "initdb.exe", "-D", STATE / "pg", "-U", ADMIN_ROLE, "-A", "scram-sha-256",
                "--pwfile", pwfile, "-E", "UTF8", "--locale=C",
            ]
        )  # fmt: skip
    finally:
        pwfile.unlink()
    start_postgres()
    # Same layout as deploy/postgres-init: one non-superuser role per database.
    for role, key in ((APP_DB, "app_db"), (ODOO_DB, "odoo_db")):
        psql(
            f"CREATE ROLE {role} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
            f"PASSWORD '{secret[key]}'",
            secret,
        )
        psql(
            f"CREATE DATABASE {role} OWNER {role} ENCODING 'UTF8' TEMPLATE template0",
            secret,
        )
        psql(f"REVOKE ALL ON DATABASE {role} FROM PUBLIC", secret)


def write_odoo_conf(secret: dict[str, str]) -> None:
    ODOO_CONF.write_text(
        "[options]\n"
        f"addons_path = {ODOO_ADDONS},{REPO / 'deploy' / 'odoo' / 'addons'}\n"
        f"data_dir = {STATE / 'odoo-data'}\n"
        "db_host = 127.0.0.1\n"
        f"db_port = {PG_PORT}\n"
        f"db_user = {ODOO_DB}\n"
        f"db_password = {secret['odoo_db']}\n"
        f"db_name = {ODOO_DB}\n"
        f"dbfilter = ^{ODOO_DB}$\n"
        "list_db = False\n"
        f"admin_passwd = {secret['odoo_master']}\n"
        "http_interface = 127.0.0.1\n"
        f"http_port = {ODOO_PORT}\n"
        "gevent_port = 18072\n"
        "workers = 0\n"
        "max_cron_threads = 0\n"
        "limit_time_real = 300\n"
        f"logfile = {LOGS / 'odoo.log'}\n"
    )


def odoo_cmd(*args: str) -> list[Any]:
    return [ODOO_PYTHON, ODOO_BIN, *args]


def init_odoo(secret: dict[str, str]) -> None:
    write_odoo_conf(secret)
    marker = STATE / "odoo.initialized"
    env = {
        **os.environ,
        "ODOO_ORDER_SYNC_LOGIN": ORDER_SYNC_LOGIN,
        "ODOO_ORDER_SYNC_PASSWORD": secret["order_sync"],
        "ODOO_CATALOGUE_IMPORT_LOGIN": CATALOGUE_IMPORT_LOGIN,
        "ODOO_CATALOGUE_IMPORT_PASSWORD": secret["catalogue_import"],
    }
    if not marker.exists():
        run(
            odoo_cmd(
                "-c",
                str(ODOO_CONF),
                "-i",
                ODOO_MODULES,
                "--without-demo=all",
                "--stop-after-init",
            )
        )
    else:
        # Picks up changes to the addon. Harmless when there are none.
        run(
            odoo_cmd(
                "-c", str(ODOO_CONF), "-u", "terrific_order_sync", "--stop-after-init"
            )
        )
    bootstrap = (REPO / "deploy" / "odoo" / "bootstrap.py").read_text()
    run(
        odoo_cmd("shell", "-c", str(ODOO_CONF), "--no-http"),
        env=env,
        input=bootstrap,
        text=True,
    )
    marker.write_text("ok\n")


def role_env(role: str, stage: str = "local_integration") -> dict[str, str]:
    """Each process gets only the credentials its job needs.

    Blank values are explicit so that nothing falls through from backend/.env.
    """
    secret = load_secrets()
    redis = f"redis://:{secret['redis']}@127.0.0.1:{REDIS_PORT}"
    env = {
        **os.environ,
        "SERVICE_ROLE": role,
        "APP_ENV": "development",
        "DEBUG": "false",
        "LOG_LEVEL": "INFO",
        "DEPLOYMENT_STAGE": stage,
        "PAYMENT_PROVIDER": "stub",
        "NOTIFICATION_PROVIDER": "stub",
        "ODOO_ORDER_PUSH_PROVIDER": "live" if stage == "local_integration" else "stub",
        "DATABASE_URL": (
            f"postgresql+psycopg://{APP_DB}:{secret['app_db']}@127.0.0.1:{PG_PORT}/{APP_DB}"
        ),
        "REDIS_URL": f"{redis}/0",
        "CELERY_BROKER_URL": f"{redis}/1",
        "CELERY_RESULT_BACKEND": f"{redis}/2",
        "ADMIN_JWT_SECRET": secret["admin_jwt"],
        "CORS_ALLOWED_ORIGINS": f"http://localhost:{FRONTEND_PORT}",
        "TRUSTED_HOSTS": "localhost,127.0.0.1",
        "MEDIA_ROOT": str(STATE / "media"),
        "MEDIA_BASE_URL": f"http://localhost:{API_PORT}/media",
        "RATE_LIMIT_ENABLED": "false",
        # Short backoff, so a downtime test takes seconds, not hours. A refused connection
        # fails at once whatever the timeout; creating a product with images can take 10s.
        "ODOO_TIMEOUT_SECONDS": "30",
        "ODOO_MAX_RETRIES": "1",
        "ODOO_VERIFY_SSL": "false",
        "ORDER_SYNC_RETRY_BASE_SECONDS": "2",
        "ORDER_SYNC_RETRY_MAX_SECONDS": "20",
        "ORDER_SYNC_MAX_ATTEMPTS": "4",
        "ODOO_BASE_URL": ODOO_BASE_URL,
        "ODOO_DATABASE": ODOO_DB,
        "ODOO_WRITE_APPROVED_TARGET": f"{ODOO_BASE_URL}#{ODOO_DB}",
        "ODOO_USERNAME": "",
        "ODOO_PASSWORD": "",
        "ODOO_API_KEY": "",
    }
    if role == "worker":
        env.update(ODOO_USERNAME=ORDER_SYNC_LOGIN, ODOO_PASSWORD=secret["order_sync"])
    elif role == "catalogue_import":
        env.update(
            ODOO_USERNAME=CATALOGUE_IMPORT_LOGIN,
            ODOO_PASSWORD=secret["catalogue_import"],
        )
    elif role == "migrate":
        env.update(
            ODOO_BASE_URL="",
            ODOO_DATABASE="",
            ODOO_WRITE_APPROVED_TARGET="",
            ODOO_ORDER_PUSH_PROVIDER="stub",
            DEPLOYMENT_STAGE="development",
        )
    return env


def process_table(stage: str) -> dict[str, dict[str, Any]]:
    python = str(VENV_PYTHON)
    api_port = DEMO_API_PORT if stage == "demo" else API_PORT
    # A demo API can run beside the integration API, so its name and pidfile differ.
    api_name = "api-demo" if stage == "demo" else "api"
    vite = str(REPO / "node_modules" / "vite" / "bin" / "vite.js")
    frontend_env = {
        **os.environ,
        "VITE_API_BASE_URL": f"http://localhost:{API_PORT}",
        "API_INTERNAL_BASE_URL": f"http://localhost:{API_PORT}",
        "VITE_DEMO_MODE": "false",
    }
    return {
        api_name: {
            "cmd": [python, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                    "--port", str(api_port)],
            "env": role_env("api", stage), "cwd": BACKEND, "port": api_port,
            "marker": f"--port {api_port}",
        },
        "worker": {
            "cmd": [python, "-m", "celery", "-A", "app.workers.celery_app", "worker",
                    "--pool=solo", "--loglevel=INFO", "-n", "tbnative@%h"],
            "env": role_env("worker", stage), "cwd": BACKEND, "marker": "tbnative@",
        },
        "beat": {
            "cmd": [python, "-m", "celery", "-A", "app.workers.celery_app", "beat",
                    "--loglevel=INFO", f"--schedule={RUN / 'celerybeat-schedule'}"],
            "env": role_env("beat", stage), "cwd": BACKEND, "marker": "celerybeat-schedule",
        },
        "frontend": {
            "cmd": ["node", vite, "dev", "--port", str(FRONTEND_PORT), "--strictPort"],
            "env": frontend_env, "cwd": REPO, "port": FRONTEND_PORT,
            "marker": f"--port {FRONTEND_PORT}",
        },
    }  # fmt: skip


def infra_table() -> dict[str, dict[str, Any]]:
    secret = load_secrets()
    return {
        "redis": {
            "cmd": [str(MEMURAI), "--port", str(REDIS_PORT), "--bind", "127.0.0.1",
                    "--dir", str(STATE / "redis"), "--requirepass", secret["redis"],
                    "--save", "", "--appendonly", "no"],
            "env": dict(os.environ), "cwd": STATE, "port": REDIS_PORT,
            "marker": f"--port {REDIS_PORT}",
        },
        "odoo": {
            "cmd": [str(part) for part in odoo_cmd("-c", str(ODOO_CONF))],
            "env": dict(os.environ), "cwd": STATE, "port": ODOO_PORT,
            "marker": str(ODOO_CONF),
        },
    }  # fmt: skip


def pidfile(name: str) -> Path:
    return RUN / f"{name}.pid"


def command_line(pid: int) -> str:
    script = f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True, check=False
    )
    return result.stdout.strip()


def running_pid(name: str, spec: dict[str, Any]) -> int | None:
    path = pidfile(name)
    if not path.exists():
        return None
    pid = int(path.read_text())
    # The marker stops a recycled PID from being mistaken for, or killed as, our process.
    return pid if str(spec["marker"]) in command_line(pid) else None


def start_process(name: str, spec: dict[str, Any]) -> None:
    if running_pid(name, spec):
        return
    port = spec.get("port")
    if isinstance(port, int) and port_open(port):
        raise SystemExit(f"Port {port} for {name} is already in use by something else.")
    log = (LOGS / f"{name}.log").open("ab")
    process = subprocess.Popen(
        spec["cmd"],
        env=spec["env"],
        cwd=spec["cwd"],
        stdout=log,
        stderr=log,
        creationflags=DETACHED,
    )
    pidfile(name).write_text(str(process.pid))
    if isinstance(port, int):
        wait_port(port, name)


def stop_process(name: str, spec: dict[str, Any]) -> None:
    pid = running_pid(name, spec)
    if pid:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, check=False)
    pidfile(name).unlink(missing_ok=True)


def all_processes() -> dict[str, dict[str, Any]]:
    return {
        **process_table("local_integration"),
        "api-demo": process_table("demo")["api-demo"],
        **infra_table(),
    }


def cmd_up(_: argparse.Namespace) -> None:
    for folder in (
        STATE,
        RUN,
        LOGS,
        STATE / "redis",
        STATE / "odoo-data",
        STATE / "media",
    ):
        folder.mkdir(parents=True, exist_ok=True)
    secret = load_secrets()
    init_postgres(secret)
    start_process("redis", infra_table()["redis"])
    stop_process("odoo", infra_table()["odoo"])
    init_odoo(secret)
    start_process("odoo", infra_table()["odoo"])
    run(
        [VENV_PYTHON, "-m", "alembic", "upgrade", "head"],
        env=role_env("migrate"),
        cwd=BACKEND,
    )
    print("infrastructure ready")


def cmd_app(args: argparse.Namespace) -> None:
    table = process_table(args.stage)
    for name in args.only or table:
        start_process(name, table[name])
    print(f"application started in stage {args.stage}")


def cmd_start(args: argparse.Namespace) -> None:
    start_process(args.name, all_processes()[args.name])


def cmd_stop(args: argparse.Namespace) -> None:
    table = all_processes()
    for name in table if args.name == "all" else [args.name]:
        stop_process(name, table[name])
    if args.name == "all" and (STATE / "pg" / "postmaster.pid").exists():
        run([PG_BIN / "pg_ctl.exe", "-D", STATE / "pg", "-m", "fast", "-w", "stop"])


def cmd_status(_: argparse.Namespace) -> None:
    for name, spec in all_processes().items():
        print(f"{name:10} {'running' if running_pid(name, spec) else 'stopped'}")
    print(f"{'postgres':10} {'running' if port_open(PG_PORT) else 'stopped'}")


def ensure_native_admin() -> dict[str, str]:
    """A throwaway admin for this stack's tests, with a password generated per stack."""
    secret = load_secrets()
    env = {**role_env("migrate"), "ADMIN_BOOTSTRAP_PASSWORD": secret["native_admin"]}
    result = subprocess.run(
        [
            str(VENV_PYTHON), "-m", "app.scripts.create_admin_user", "--email", NATIVE_ADMIN_EMAIL,
            "--full-name", "Native Test Admin", "--role", "SUPER_ADMIN",
        ],
        env=env,
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )  # fmt: skip
    if result.returncode and "already exists" not in result.stderr:
        raise SystemExit(result.stderr)
    return {
        "NATIVE_ADMIN_EMAIL": NATIVE_ADMIN_EMAIL,
        "NATIVE_ADMIN_PASSWORD": secret["native_admin"],
    }


def cmd_verify(_: argparse.Namespace) -> int:
    env = {**role_env("worker"), **ensure_native_admin()}
    script = REPO / "deploy" / "native" / "verify_integration.py"
    return subprocess.call([str(VENV_PYTHON), str(script)], env=env, cwd=BACKEND)


def cmd_verify_financials(_: argparse.Namespace) -> int:
    env = {**role_env("worker"), **ensure_native_admin()}
    script = REPO / "deploy" / "native" / "verify_financials.py"
    return subprocess.call([str(VENV_PYTHON), str(script)], env=env, cwd=BACKEND)


def cmd_verify_prices(args: argparse.Namespace) -> int:
    env = {**role_env("worker"), "TB_NATIVE_STATE_DIR": str(STATE)}
    script = REPO / "deploy" / "native" / "verify_variant_prices.py"
    command = [str(VENV_PYTHON), str(script), "--label", args.label, "--sync", str(args.sync)]
    return subprocess.call(command, env=env, cwd=BACKEND)


def cmd_browser(_: argparse.Namespace) -> int:
    env = {
        **os.environ,
        **ensure_native_admin(),
        "E2E_FRONTEND_URL": f"http://localhost:{FRONTEND_PORT}",
        "E2E_API_URL": f"http://localhost:{API_PORT}",
        "E2E_OUTPUT_DIR": str(STATE / "browser"),
        "E2E_DEMO": "false",
    }
    return subprocess.call(
        ["node", str(REPO / "tests" / "browser" / "journey.mjs")], env=env
    )


def test_env() -> dict[str, str]:
    """The pytest suite, on its own database in this cluster and its own Redis indexes."""
    secret = load_secrets()
    redis = f"redis://:{secret['redis']}@127.0.0.1:{REDIS_PORT}"
    role = f"{ADMIN_ROLE}:{secret['pg_admin']}"
    return {
        **os.environ,
        "DATABASE_URL": f"postgresql+psycopg://{role}@127.0.0.1:{PG_PORT}/{TEST_DB}",
        "REDIS_URL": f"{redis}/15",
        "CELERY_BROKER_URL": f"{redis}/14",
        "CELERY_RESULT_BACKEND": f"{redis}/13",
    }


def ensure_test_db(secret: dict[str, str]) -> None:
    exists = subprocess.run(
        [
            str(PG_BIN / "psql.exe"), "-h", "127.0.0.1", "-p", str(PG_PORT), "-U", ADMIN_ROLE,
            "-d", "postgres", "-Atc", f"select 1 from pg_database where datname='{TEST_DB}'",
        ],
        env={**os.environ, "PGPASSWORD": secret["pg_admin"]},
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()  # fmt: skip
    if not exists:
        psql(f"CREATE DATABASE {TEST_DB} ENCODING 'UTF8' TEMPLATE template0", secret)
    run([VENV_PYTHON, "-m", "alembic", "upgrade", "head"], env=test_env(), cwd=BACKEND)


def cmd_test(args: argparse.Namespace) -> int:
    ensure_test_db(load_secrets())
    extra = [a for a in args.pytest_args if a != "--"]
    command = [str(VENV_PYTHON), "-m", "pytest", *extra]
    return subprocess.call(command, env=test_env(), cwd=BACKEND)


def cmd_run(args: argparse.Namespace) -> int:
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if command and command[0] == "python":
        command[0] = str(VENV_PYTHON)
    return subprocess.call(command, env=role_env(args.role, args.stage), cwd=BACKEND)


def main() -> int:
    stages = ("local_integration", "demo")
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("up").set_defaults(func=cmd_up)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("verify").set_defaults(func=cmd_verify)
    sub.add_parser("verify-financials").set_defaults(func=cmd_verify_financials)
    prices = sub.add_parser("verify-prices")
    prices.add_argument("--label", default="check")
    prices.add_argument("--sync", type=int, default=0)
    prices.set_defaults(func=cmd_verify_prices)
    tests = sub.add_parser("test")
    tests.add_argument("pytest_args", nargs=argparse.REMAINDER)
    tests.set_defaults(func=cmd_test)
    sub.add_parser("browser").set_defaults(func=cmd_browser)
    app = sub.add_parser("app")
    app.add_argument("--stage", choices=stages, default="local_integration")
    app.add_argument("--only", nargs="*")
    app.set_defaults(func=cmd_app)
    start = sub.add_parser("start")
    start.add_argument("name")
    start.set_defaults(func=cmd_start)
    stop = sub.add_parser("stop")
    stop.add_argument("name")
    stop.set_defaults(func=cmd_stop)
    runner = sub.add_parser("run")
    runner.add_argument("--role", required=True)
    runner.add_argument("--stage", choices=stages, default="local_integration")
    runner.add_argument("command", nargs=argparse.REMAINDER)
    runner.set_defaults(func=cmd_run)
    args = parser.parse_args()
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
