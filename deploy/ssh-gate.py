#!/usr/bin/python3
"""Forced SSH command; CI cannot get a shell, forwarding or an admin action."""
import os
import re
import subprocess
import sys

command = os.environ.get("SSH_ORIGINAL_COMMAND", "")
if not re.fullmatch(r"(?:stage|promote) sha256:[0-9a-f]{64} [0-9a-f]{40}", command):
    print("Only stage/promote of an immutable MIA release is allowed", file=sys.stderr)
    raise SystemExit(1)
raise SystemExit(subprocess.call(["sudo", "-n", "/usr/local/sbin/mia-release", command]))
