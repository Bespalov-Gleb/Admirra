"""Generate Redis service credentials on the worker host, never in git/stdout.

Idempotent, refuses conflicting files. This prepares files only; no containers
or production workers are started. Rotate credentials as an explicit operation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets

ROOT = Path("/etc/admirra")
USERS = ("broker_api", "broker_worker", "limiter_api", "limiter_worker",
         "cache_api", "cache_worker", "health")
COMMON = "+ping +hello +select +client|setname +client|setinfo +client|id"
BROKER = ("+get +mget +set +setnx +setex +psetex +del +exists +expire +pexpire +ttl +pttl "
          "+incr +incrby +decr +lpush +rpush +lpop +rpop +brpop +llen +lrange +lrem +ltrim "
          "+sadd +srem +smembers +sismember +scard +hset +hget +hgetall +hdel +hlen "
          "+zadd +zrem +zrangebyscore +zrevrangebyscore +zrange +zcard +zcount +zscore "
          "+watch +unwatch +multi +exec +discard +eval +evalsha +script|load +script|exists "
          "+publish +subscribe +unsubscribe +psubscribe +punsubscribe")


def acl_line(user, password, keys="", commands="+ping", channels=""):
    digest = hashlib.sha256(password.encode()).hexdigest()
    return f"user {user} reset on #{digest} -@all resetkeys resetchannels {keys} {channels} {commands}".strip()


def acl_files(passwords, db=0):
    if not isinstance(db, int) or not 0 <= db <= 15:
        raise ValueError("Unexpected Redis database")
    broker = ["user default off", acl_line("health", passwords["health"], commands="+ping +client|setinfo")]
    cache = list(broker)
    for actor in ("api", "worker"):
        user = "broker_" + actor
        # Redis PSUBSCRIBE checks literal pattern equality, not whether the
        # requested subscription is a subset of a broader ACL glob.
        channels = (f"&admirra:task:* &admirra:task:/{db}.celery.pidbox "
                    f"&admirra:task:/{db}.celeryev/* &admirra:task:/{db}.celeryev/worker.*")
        broker.append(acl_line(user, passwords[user], "~admirra:task:*", COMMON + " " + BROKER, channels))
        user = "limiter_" + actor
        broker.append(acl_line(user, passwords[user], "~admirra:rate:v1:*",
                               COMMON + " +get +psetex +time +eval +evalsha +script|load +script|exists"))
        user = "cache_" + actor
        cache.append(acl_line(user, passwords[user], "~admirra:read:v1:*",
                              COMMON + " +get +set +del +eval +evalsha +script|load +script|exists"))
    return {"redis-broker-users.acl": "\n".join(broker) + "\n",
            "redis-cache-users.acl": "\n".join(cache) + "\n"}


def environments(passwords):
    result = {}
    for actor, broker, cache in (("api", "10.77.0.2:6379", "10.77.0.2:6380"),
                                  ("worker", "broker:6379", "cache:6379")):
        def url(service, host):
            user = service + "_" + actor
            return f"redis://{user}:{passwords[user]}@{host}/0"
        result[f"redis-{actor}.env"] = (
            f"CELERY_BROKER_URL={url('broker', broker)}\n"
            f"RATE_LIMIT_REDIS_URL={url('limiter', broker)}\n"
            f"READ_CACHE_REDIS_URL={url('cache', cache)}\n"
            "TASK_BROKER_PREFIX=admirra:task:\n"
        )
    result["redis-health.env"] = f"REDISCLI_AUTH={passwords['health']}\n"
    return result


def write_once(path, data, mode):
    if path.is_symlink():
        raise RuntimeError("Refusing symlink: " + str(path))
    if path.exists():
        if path.read_text() != data or path.stat().st_mode & 0o777 != mode:
            raise RuntimeError("Existing file differs; explicit rotation/review required: " + str(path))
        return
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
    with os.fdopen(fd, "w") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def provision(root, refresh_acl=False):
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.is_symlink() or root.stat().st_mode & 0o077 or root.stat().st_uid != os.geteuid():
        raise RuntimeError("Credential directory must be private (0700)")
    path = root / "redis-credentials.json"
    if path.exists():
        if path.is_symlink() or path.stat().st_mode & 0o077:
            raise RuntimeError("Credential state must be a private regular file")
        passwords = json.loads(path.read_text())
        if set(passwords) != set(USERS) or any(not isinstance(p, str) or not re.fullmatch(r"[A-Za-z0-9_-]{40,128}", p) for p in passwords.values()):
            raise RuntimeError("Unexpected credential state")
    else:
        passwords = {user: secrets.token_urlsafe(32) for user in USERS}
        write_once(path, json.dumps(passwords), 0o600)
    for name, content in acl_files(passwords).items():
        # Hashes only; readable by the non-root Redis process through bind mount.
        path = root / name
        if refresh_acl and path.exists() and path.read_text() != content:
            if path.is_symlink() or path.stat().st_uid != os.geteuid():
                raise RuntimeError("Unexpected ACL file owner/type")
            old = path.read_text()
            digest = hashlib.sha256(old.encode()).hexdigest()[:12]
            write_once(root / (name + ".before-" + digest), old, 0o444)
            next_path = root / (name + ".next")
            write_once(next_path, content, 0o444)
            os.replace(next_path, path)
        write_once(root / name, content, 0o444)
    for name, content in environments(passwords).items():
        write_once(root / name, content, 0o600)
    for name in ("redis-broker.conf", "redis-cache.conf"):
        write_once(root / name, Path(__file__).with_name(name).read_text(), 0o444)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-acl", action="store_true", help="Explicit ACL-only update; backs up old file; requires container recreation")
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("Root required on worker host")
    provision(ROOT, refresh_acl=args.refresh_acl)
    print("Redis credentials/configuration prepared; no secrets emitted; no services started")


if __name__ == "__main__":
    main()
