"""Installed root-owned. The CI key can only deploy validated immutable images."""
from contextlib import contextmanager
from pathlib import Path
from urllib.request import Request, urlopen
import fcntl
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time

from backup import backup, BASE

REGISTRY = "ghcr.io/agentdouble/mia-demodays"
KIT = Path("/usr/local/lib/mia-demodays")


def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, capture_output=True, **kwargs).stdout.strip()


def compose(environment, args):
    directory = BASE / environment
    return run(["docker", "compose", "-p", f"mia-{environment}",
                "--project-directory", str(directory), "--env-file", str(directory/"release.env"),
                "-f", str(KIT/"compose.yaml"), *args])


def save(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(data)
    temporary.chmod(0o600)
    temporary.replace(path)


def main():
    if os.geteuid() != 0:
        raise ValueError("Root required")
    os.umask(0o077)
    words = shlex.split(sys.argv[1]) if len(sys.argv) == 2 else []
    if words == ["validate-staging"]:
        state_path = BASE/"staging/release.json"
        state = json.loads(state_path.read_text())
        if state.get("health") != "passed":
            raise ValueError("Staging is not healthy")
        state["validated"] = True
        save(state_path, json.dumps(state))
        print("Staging marked validated by the deployment operator")
        return
    if len(words) != 3 or words[0] not in ("stage", "promote"):
        raise ValueError("Expected stage/promote, image digest and source commit")
    operation, digest, commit = words
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid digest or commit")
    environment = "staging" if operation == "stage" else "production"
    if operation == "promote":
        stage = json.loads((BASE/"staging/release.json").read_text())
        if not stage.get("validated") or stage["digest"] != digest or stage["commit"] != commit:
            raise ValueError("Production must reuse the exact validated staging release")
    token = sys.stdin.readline(1024).strip()
    if not token or len(token) < 20:
        raise ValueError("A temporary repository registry token is required on stdin")
    image = REGISTRY + "@" + digest
    with tempfile.TemporaryDirectory(prefix="mia-registry-") as config:
        env = dict(os.environ, DOCKER_CONFIG=config)
        run(["docker", "login", "ghcr.io", "-u", "agentdouble", "--password-stdin"], input=token+"\n", env=env)
        run(["docker", "pull", image], env=env)
    metadata = json.loads(run(["docker", "image", "inspect", image]))[0]
    labels = metadata["Config"].get("Labels") or {}
    if labels.get("org.opencontainers.image.revision") != commit or metadata["Architecture"] != "amd64":
        raise ValueError("Image revision or architecture mismatch")
    directory = BASE/environment
    if environment == "production":
        backup()
    release_env = directory/"release.env"
    previous = release_env.read_text() if release_env.exists() else None
    port = 18081 if environment == "staging" else 18080
    save(release_env, f"APP_IMAGE={image}\nAPP_PORT={port}\n")
    try:
        compose(environment, ["up", "-d", "--wait", "--wait-timeout", "90", "app"])
        host = "mia-staging.localhost:18081" if environment == "staging" else "mia-foyer.com"
        for game in ("recommander", "fraude"):
            request = Request(f"http://127.0.0.1:{port}/{game}/api/health", headers={"Host": host})
            with urlopen(request, timeout=10) as response:
                assert response.status == 200
        if environment == "production":
            compose(environment, ["--profile", "public", "up", "-d", "caddy"])
    except BaseException:
        if previous:
            save(release_env, previous)
            compose(environment, ["up", "-d", "--wait", "app"])
        raise
    state = {"digest": digest, "commit": commit, "health": "passed", "validated": False,
             "deployed_at": int(time.time()), "image": image}
    save(directory/"release.json", json.dumps(state))
    print(f"{environment}: {commit} {digest}; HTTP and SQLite health passed")


if __name__ == "__main__":
    try:
        with open("/var/lock/mia-release.lock", "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            main()
    except Exception as error:
        # Never dump registry login subprocess output or private environment.
        print(f"Deployment refused/failed: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
