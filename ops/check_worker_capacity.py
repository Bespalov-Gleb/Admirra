"""Read-only prepared-worker capacity gate; never prints resolved credentials.

Docker Compose resolves only structure (--no-env-resolution/no-interpolate).
This arithmetic gate is necessary, not sufficient: no load/restore acceptance
is inferred from capacity_pass. --with-api2 checks the explicitly sized candidate.
"""
import argparse
import json
import math
from decimal import Decimal
from pathlib import Path
import re
import shlex
import subprocess

ROOT = Path(__file__).resolve().parent


def positive(value, name, *, zero=False):
    if isinstance(value, bool) or int(value) != float(value) or int(value) < (0 if zero else 1):
        raise ValueError("Invalid " + name)
    return int(value)


def memory_bytes(value):
    # --no-interpolate keeps Compose byte values such as "1536m" as strings.
    if isinstance(value, str):
        match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([kmgt]?(?:i?b)?)", value.strip().lower())
        if not match:
            raise ValueError("Invalid memory cap unit")
        number, unit = match.groups()
        power = {"k": 1, "m": 2, "g": 3, "t": 4}.get(unit[:1], 0)
        value = Decimal(number) * (1024 ** power)
    return positive(value, "memory cap")


def worker_concurrency(command):
    args = shlex.split(command) if isinstance(command, str) else command
    if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
        raise ValueError("Explicit worker command required")
    values = []
    for i, arg in enumerate(args):
        if arg.startswith(("--autoscale", "--pool", "-P")):
            raise ValueError("Pool/autoscale override needs a new reviewed capacity model")
        if arg.startswith("--concurrency="):
            values.append(arg.partition("=")[2])
        elif arg in ("--concurrency", "-c"):
            values.append(args[i + 1] if i + 1 < len(args) else None)
    if len(values) != 1 or "automation.work_worker" not in args:
        raise ValueError("Exactly one bounded prefork concurrency is required")
    return positive(values[0], "worker concurrency")


def assess(compose, budget, *, with_api2=False):
    services = compose.get("services", {})
    if set(services) != set(budget["services"]):
        raise ValueError("Service inventory differs from the reviewed capacity manifest")
    memory = cpu = connections = 0
    rows = []
    for name, service in sorted(services.items()):
        replicas = positive((service.get("deploy") or {}).get("replicas", 1), "replicas")
        cap = memory_bytes(service.get("mem_limit", 0))
        cap_mib = math.ceil(cap / 1024**2)
        cores = float(service.get("cpus", 0))
        if not math.isfinite(cores) or cores <= 0:
            raise ValueError("Explicit positive CPU cap required")
        env = service.get("environment") or {}
        role = env.get("APP_PROCESS_ROLE")
        pool = processes = parent_processes = 0
        if role in ("worker", "scheduler"):
            pool = positive(env.get("DB_POOL_SIZE", 0), "DB pool") + positive(
                env.get("DB_MAX_OVERFLOW", -1), "DB overflow", zero=True)
            if role == "worker":
                processes = worker_concurrency(service.get("command"))
                parent_processes = 1
                if pool < 2:
                    raise ValueError("Business operation and heartbeat need at least two child connections")
            else:
                processes = 1
        elif name not in ("broker", "cache"):
            raise ValueError("Unknown runtime SQL role")
        demand = replicas * processes * pool
        rows.append({"service": name, "replicas": replicas, "parent_processes": parent_processes * replicas,
            "sql_processes": processes * replicas, "sql_pool_max": demand, "memory_cap_mib": cap_mib * replicas})
        connections += demand
        memory += replicas * cap_mib
        cpu += replicas * cores
    api_connections = 0
    errors = []
    if with_api2:
        api = budget["api2_candidate"]
        memory += positive(api["memory_mib"], "API memory")
        cpu += float(api["cpus"])
        api_connections = positive(api["processes"], "API processes") * (
            positive(api["db_pool_size"], "API pool") + positive(api["db_max_overflow"], "API overflow", zero=True))
        if api_connections + api["api1_reserved_connections"] + api["api_db_reserve"] > api["api_db_role_limit"]:
            errors.append("API database role connection budget exceeded")
    available = positive(budget["memory_mib"], "host RAM") - positive(budget["os_reserve_mib"], "OS reserve")
    if budget["os_reserve_mib"] < 1536:
        raise ValueError("At least 1536 MiB OS reserve required")
    if memory > available:
        errors.append("Host memory caps plus OS reserve exceed physical RAM")
    if connections + budget["worker_db_reserve"] > budget["worker_db_role_limit"]:
        errors.append("Worker database role connection budget exceeded")
    return {"capacity_pass": not errors, "load_accepted": False, "with_api2": with_api2,
        "memory_caps_mib": memory, "physical_memory_mib": budget["memory_mib"],
        "os_headroom_mib": budget["memory_mib"] - memory, "required_os_reserve_mib": budget["os_reserve_mib"],
        "cpu_caps_sum": round(cpu, 2), "physical_cpus": budget["cpus"],
        "worker_db_pool_max": connections, "worker_db_role_limit": budget["worker_db_role_limit"],
        "api2_db_pool_max": api_connections, "services": rows, "errors": errors,
        "warnings": ["CPU caps may compete; tmpfs is charged to container memory; peak RSS still requires load tests"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compose", type=Path, default=ROOT / "compose.workers.yml")
    parser.add_argument("--budget", type=Path, default=ROOT / "worker_capacity.json")
    parser.add_argument("--with-api2", action="store_true")
    args = parser.parse_args()
    try:
        result = subprocess.run(["docker", "compose", "--env-file", "/dev/null", "-f", str(args.compose),
            "config", "--no-env-resolution", "--no-interpolate", "--format", "json"],
            capture_output=True, timeout=20, check=True)
        if len(result.stdout) > 2 * 1024**2:
            raise ValueError("Compose inventory too large")
        verdict = assess(json.loads(result.stdout), json.loads(args.budget.read_text()), with_api2=args.with_api2)
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        # Compose diagnostics might contain operator environment values.
        raise SystemExit("Capacity check failed; validate the reviewed Compose/manifest privately") from None
    print(json.dumps(verdict, indent=2, sort_keys=True))
    if not verdict["capacity_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
