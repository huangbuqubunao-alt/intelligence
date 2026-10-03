"""Task-owned process supervisor: application death cannot orphan heavy children."""

from __future__ import annotations

import os
import signal
import subprocess
import sys


def main() -> None:
    parent = int(sys.argv[1])
    process = subprocess.Popen(sys.argv[2:], stdin=subprocess.DEVNULL)
    while True:
        if os.getppid() != parent:
            os.killpg(os.getpgrp(), signal.SIGKILL)  # our start_new_session group only
        try:
            code = process.wait(timeout=0.2)
            raise SystemExit(code if code >= 0 else 1)
        except subprocess.TimeoutExpired:
            pass


if __name__ == "__main__":
    main()
