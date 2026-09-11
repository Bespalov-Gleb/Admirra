"""Prepare non-superuser runtime DB roles without restarting/changing the app.

Passwords stay in root-only files. SQL receives SCRAM verifiers, not plaintext.
No schema migration, business-row writes, public grants revocation or old-role
changes. Existing roles not created by this tool cause a fail-closed refusal.
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import subprocess

from ops.private_redis import write_once

MARKER = "admirra-managed-runtime-v1"
GATEWAY = "172.18.0.250"
HBA_BLOCK = ("# BEGIN ADMIRRA PRIVATE GATEWAY\n"
             f"host saas_project admirra_api,admirra_worker {GATEWAY}/32 scram-sha-256\n"
             f"host all all {GATEWAY}/32 reject\n"
             "# END ADMIRRA PRIVATE GATEWAY\n")


def ident(value):
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", value):
        raise ValueError("Invalid managed database identifier")
    return '"' + value + '"'


def literal(value):
    return "'" + value.replace("'", "''") + "'"


def scram(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    salted = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 4096)
    stored = hashlib.sha256(hmac.digest(salted, b"Client Key", "sha256")).digest()
    server = hmac.digest(salted, b"Server Key", "sha256")
    b64 = lambda raw: base64.b64encode(raw).decode()
    return f"SCRAM-SHA-256$4096:{b64(salt)}${b64(stored)}:{b64(server)}"


def role_sql(database, schema, owner, passwords, prefix="admirra"):
    database, schema, owner = ident(database), ident(schema), ident(owner)
    group_name = prefix + "_runtime"
    group = ident(group_name)
    result = ["BEGIN; SET LOCAL lock_timeout = '5s'; SET LOCAL statement_timeout = '30s';"]
    roles = [(group_name, None, -1)] + [(prefix + "_" + actor, password, 30 if actor == "api" else 20)
                                      for actor, password in passwords.items()]
    for name, password, limit in roles:
        role = ident(name)
        # A stable comment distinguishes managed roles from a preexisting user.
        result.append(f"""DO $managed$ BEGIN
IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname={literal(name)}) THEN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname={literal(name)}
    AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication AND NOT rolbypassrls
    AND COALESCE(shobj_description(oid, 'pg_authid'), '')={literal(MARKER)}) THEN
    RAISE EXCEPTION 'Managed role conflict';
  END IF;
ELSE
  CREATE ROLE {role} {'LOGIN' if password else 'NOLOGIN'} NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS CONNECTION LIMIT {limit} {('PASSWORD ' + literal(scram(password))) if password else ''};
  COMMENT ON ROLE {role} IS {literal(MARKER)};
END IF; END $managed$;""")
        if password:
            result.extend([f"GRANT {group} TO {role};",
                           f"ALTER ROLE {role} SET statement_timeout = '60s';",
                           f"ALTER ROLE {role} SET lock_timeout = '10s';",
                           f"ALTER ROLE {role} SET idle_in_transaction_session_timeout = '300s';"])
    result.extend([
        f"GRANT CONNECT ON DATABASE {database} TO {group};",
        f"GRANT USAGE ON SCHEMA {schema} TO {group};",
        f"GRANT SELECT ON ALL TABLES IN SCHEMA {schema} TO {group};",
        f"""DO $grants$ DECLARE item record; BEGIN
FOR item IN SELECT tablename FROM pg_tables WHERE schemaname={literal(schema.strip(chr(34)))}
  AND tablename <> 'alembic_version' LOOP
  EXECUTE format('GRANT INSERT, UPDATE, DELETE ON TABLE %I.%I TO %I',
    {literal(schema.strip(chr(34)))}, item.tablename, {literal(group_name)});
END LOOP; END $grants$;""",
        f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {schema} TO {group};",
        f"ALTER DEFAULT PRIVILEGES FOR ROLE {owner} IN SCHEMA {schema} GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {group};",
        f"ALTER DEFAULT PRIVILEGES FOR ROLE {owner} IN SCHEMA {schema} GRANT USAGE, SELECT ON SEQUENCES TO {group};",
        "COMMIT;",
    ])
    return "\n".join(result)


def prepare(root):
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.is_symlink() or root.stat().st_mode & 0o077 or root.stat().st_uid != os.geteuid():
        raise RuntimeError("Private directory required")
    path = root / "db-credentials.json"
    if path.exists():
        if path.is_symlink() or path.stat().st_mode & 0o077:
            raise RuntimeError("Credential state must be private")
        passwords = json.loads(path.read_text())
        if set(passwords) != {"api", "worker"} or any(not isinstance(p, str) or not re.fullmatch(r"[A-Za-z0-9_-]{40,128}", p) for p in passwords.values()):
            raise RuntimeError("Unexpected credential state")
    else:
        passwords = {actor: secrets.token_urlsafe(32) for actor in ("api", "worker")}
        write_once(path, json.dumps(passwords), 0o600)
    for actor, password in passwords.items():
        write_once(root / f"db-{actor}.env",
                   f"DATABASE_URL=postgresql://admirra_{actor}:{password}@10.77.0.1:5432/saas_project\n", 0o600)
    return passwords


def hba_content(original):
    if original.startswith(HBA_BLOCK):
        return original
    if "ADMIRRA PRIVATE GATEWAY" in original:
        raise RuntimeError("Unexpected existing gateway rules")
    return HBA_BLOCK + original


def configure_hba():
    """Allow only runtime roles from the new proxy; existing app IPs unchanged."""
    import ipaddress
    network = json.loads(subprocess.check_output(["docker", "network", "inspect", "admirra_default"], text=True))[0]
    if not any(ipaddress.ip_address(GATEWAY) in ipaddress.ip_network(item["Subnet"])
               for item in network["IPAM"]["Config"]):
        raise RuntimeError("Unexpected Docker subnet")
    for container in network.get("Containers", {}).values():
        if container["IPv4Address"].split("/")[0] == GATEWAY and container["Name"] != "admirra-db-gateway-gateway-1":
            raise RuntimeError("Gateway address is already allocated")
    inspect = json.loads(subprocess.check_output(["docker", "inspect", "admirra-db-1"], text=True))[0]
    mounts = [m for m in inspect["Mounts"] if m["Destination"] == "/var/lib/postgresql/data" and m["Type"] == "volume"]
    if len(mounts) != 1:
        raise RuntimeError("Expected a dedicated PostgreSQL data volume")
    def psql(sql):
        return subprocess.check_output(["docker", "exec", "-u", "postgres", "admirra-db-1",
            "psql", "-X", "-At", "-d", "saas_project", "-c", sql], text=True).strip()
    if psql("SHOW hba_file") != "/var/lib/postgresql/data/pg_hba.conf":
        raise RuntimeError("Unexpected HBA path")
    path = Path(mounts[0]["Source"]) / "pg_hba.conf"
    if path.is_symlink():
        raise RuntimeError("Refusing symlink HBA")
    original, stat = path.read_text(), path.stat()
    desired = hba_content(original)
    if desired == original:
        if psql("SELECT count(*) FROM pg_hba_file_rules WHERE error IS NOT NULL") != "0":
            raise RuntimeError("HBA has parse errors")
        return
    write_once(Path("/etc/admirra/pg_hba.before-private.conf"), original, 0o600)
    def replace(content):
        tmp = path.with_name("pg_hba.conf.admirra-next")
        write_once(tmp, content, stat.st_mode & 0o777)
        os.chown(tmp, stat.st_uid, stat.st_gid)
        os.replace(tmp, path)
    try:
        replace(desired)
        if psql("SELECT count(*) FROM pg_hba_file_rules WHERE error IS NOT NULL") != "0":
            raise RuntimeError("New HBA rejected")
        if psql("SELECT pg_reload_conf()") != "t":
            raise RuntimeError("HBA reload failed")
    except BaseException:
        replace(original)
        psql("SELECT pg_reload_conf()")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Grant roles in the explicitly named production DB")
    parser.add_argument("--apply-hba", action="store_true", help="Restrict the private gateway to runtime roles")
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("Root required on DB host")
    passwords = prepare(Path("/etc/admirra"))
    if args.apply:
        sql = role_sql("saas_project", "public", "postgres", passwords)
        result = subprocess.run(["docker", "exec", "-i", "-u", "postgres", "admirra-db-1",
                                 "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-d", "saas_project"],
                                input=sql, capture_output=True, text=True)
        if result.returncode:
            # SQL error text can contain verifier strings; never print it.
            raise SystemExit("Database role preparation failed; application unchanged; inspect securely on host")
    if args.apply_hba:
        configure_hba()
    print("Private runtime credentials prepared; roles " + ("granted" if args.apply else "not applied") + "; secrets not emitted")


if __name__ == "__main__":
    main()
