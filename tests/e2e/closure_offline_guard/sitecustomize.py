"""Validation-only guard: deny external sockets, live models and real Keychain."""

import json
import os
import socket
from pathlib import Path

_connect = socket.socket.connect
_connect_ex = socket.socket.connect_ex


def allowed(address):
    if isinstance(address, tuple):
        host, port = address[:2]
        if host not in {"127.0.0.1", "::1", "localhost"} or port == 11434:
            log = os.environ.get("YIA_NETWORK_GUARD_LOG")
            if log:
                with Path(log).open("a") as stream:
                    stream.write(json.dumps({"host": str(host), "port": port, "blocked": True}) + "\n")
            raise PermissionError("Offline closure network guard")


def connect(self, address):
    allowed(address)
    return _connect(self, address)


def connect_ex(self, address):
    allowed(address)
    return _connect_ex(self, address)


socket.socket.connect = connect
socket.socket.connect_ex = connect_ex

from youtube_intel.model_settings import (  # noqa: E402
    CredentialStoreError,
    MacOSKeychainCredentialStore,
)


def forbidden(*args, **kwargs):
    raise CredentialStoreError()


MacOSKeychainCredentialStore._libraries = forbidden
