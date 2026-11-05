"""Initial install by the administrator. Creates local secrets, never prints them."""
from pathlib import Path
import os
import pwd
import secrets
import shutil
import subprocess
import sys

SOURCE = Path(__file__).resolve().parent
KIT = Path("/usr/local/lib/mia-demodays")
BASE = Path("/srv/mia-demodays")


def run(*args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)


def main():
    if os.geteuid() != 0:
        raise SystemExit("Run as root")
    os.umask(0o077)
    key = Path(sys.argv[1]).read_text().strip()
    if not key.startswith("ssh-ed25519 ") or "\n" in key:
        raise SystemExit("Expected a dedicated public deployment key")
    KIT.mkdir(parents=True, exist_ok=True)
    KIT.chmod(0o755)
    for name in ("compose.yaml", "Caddyfile", "release.py", "backup.py"):
        shutil.copyfile(SOURCE/name, KIT/name)
        (KIT/name).chmod(0o644)
    for environment, origin in (("staging", "http://mia-staging.localhost:18081"), ("production", "https://mia-foyer.com")):
        directory = BASE/environment
        directory.mkdir(parents=True, exist_ok=True)
        directory.chmod(0o700)
        data = directory/"data"
        data.mkdir(exist_ok=True)
        os.chown(data, 10001, 10001)
        data.chmod(0o700)
        env = directory/"app.env"
        if not env.exists():
            env.write_text(f"APP_SECRET={secrets.token_hex(48)}\nPUBLIC_ORIGIN={origin}\n"
                           f"DATABASE_PATH=/data/mia.sqlite3\nTRUST_PROXY={int(environment == 'production')}\n")
            env.chmod(0o600)
    for name in ("caddy-data", "caddy-config"):
        path = BASE/"production"/name
        path.mkdir(exist_ok=True)
        os.chown(path, 10002, 10002)
        path.chmod(0o700)
    Path("/var/backups/mia-demodays").mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        pwd.getpwnam("mia-deploy")
    except KeyError:
        run("useradd", "--create-home", "--shell", "/bin/sh", "mia-deploy")
    home = Path(pwd.getpwnam("mia-deploy").pw_dir)
    os.chown(home, 0, 0)
    home.chmod(0o755)
    ssh = home/".ssh"
    ssh.mkdir(exist_ok=True)
    os.chown(ssh, 0, 0)
    ssh.chmod(0o755)  # Public keys are readable by sshd after dropping to the account.
    authorized = ssh/"authorized_keys"
    authorized.write_text('restrict,command="/usr/local/bin/mia-release-gate" '+key+'\n')
    authorized.chmod(0o644)  # Root owns the non-writable home/key directory.
    shutil.copyfile(SOURCE/"ssh-gate.py", "/usr/local/bin/mia-release-gate")
    Path("/usr/local/bin/mia-release-gate").chmod(0o755)
    launcher = Path("/usr/local/sbin/mia-release")
    launcher.write_text('#!/bin/sh\nexec /usr/bin/python3 /usr/local/lib/mia-demodays/release.py "$@"\n')
    launcher.chmod(0o755)
    sudoers = Path("/etc/sudoers.d/mia-deploy")
    sudoers.write_text('mia-deploy ALL=(root) NOPASSWD: /usr/local/sbin/mia-release *\n')
    sudoers.chmod(0o440)
    run("visudo", "-cf", str(sudoers))
    for name in ("mia-backup.service", "mia-backup.timer"):
        shutil.copyfile(SOURCE/name, Path("/etc/systemd/system")/name)
        (Path("/etc/systemd/system")/name).chmod(0o644)
    run("systemctl", "daemon-reload")
    run("systemctl", "enable", "--now", "mia-backup.timer")
    print("MIA production/staging directories, secrets, restricted deployment key and backup timer installed")


if __name__ == "__main__":
    main()
