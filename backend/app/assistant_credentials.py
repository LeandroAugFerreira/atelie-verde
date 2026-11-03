"""Personal credentials outside the project/package, encrypted and never serialized to UI."""

import ctypes
import json
import os
import re
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

_lock = threading.RLock()
_installation_depth = threading.local()


@contextmanager
def installation_lock():
    """Serialize shared settings and quotas across threads and desktop processes."""
    with _lock:
        if getattr(_installation_depth, "active", False):
            yield
            return
        directory = root()
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (directory / "installation-ai.lock").open("a+b") as file:
            file.seek(0, 2)
            if file.tell() == 0:
                file.write(b"0")
                file.flush()
            file.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(file.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                fcntl.flock(file.fileno(), fcntl.LOCK_EX)
            _installation_depth.active = True
            try:
                yield
            finally:
                _installation_depth.active = False
                file.seek(0)
                if os.name == "nt":
                    msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(file.fileno(), fcntl.LOCK_UN)


def root():
    override = os.getenv("RAFINHA_CREDENTIALS_DIR")
    if override:
        return Path(override)
    if os.name == "nt":
        return Path(os.environ["LOCALAPPDATA"]) / "AtelieVerde" / "Rafinha"
    return Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")) / "atelie-verde" / "rafinha"


def private_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(content)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


class Blob(ctypes.Structure):
    _fields_ = [("size", ctypes.c_ulong), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def dpapi(content, decrypt=False):
    buffer = ctypes.create_string_buffer(content)
    incoming = Blob(len(content), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    outgoing = Blob()
    operation = (
        ctypes.windll.crypt32.CryptUnprotectData
        if decrypt
        else ctypes.windll.crypt32.CryptProtectData
    )
    operation.argtypes = [
        ctypes.POINTER(Blob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.POINTER(Blob),
    ]
    operation.restype = ctypes.c_int
    ctypes.windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    ctypes.windll.kernel32.LocalFree.restype = ctypes.c_void_p
    if not operation(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing)):
        raise OSError("Não foi possível acessar as credenciais desta instalação.")
    try:
        return ctypes.string_at(outgoing.data, outgoing.size)
    finally:
        ctypes.windll.kernel32.LocalFree(outgoing.data)


def cipher():
    path = root() / "local-key.bin"
    if not path.exists():
        private_write(path, Fernet.generate_key())
    return Fernet(path.read_bytes())


def seal(value):
    raw = json.dumps(value, ensure_ascii=False).encode()
    return b"DP1" + dpapi(raw) if os.name == "nt" else b"FE1" + cipher().encrypt(raw)


def protected_read(name):
    """Named installation records use the same OS protection as personal accounts."""
    if not re.fullmatch(r"[a-z-]{3,60}", name):
        raise ValueError("Invalid protected record name")
    with _lock:
        path = root() / (name + ".bin")
        if not path.exists():
            return {}
        try:
            content = path.read_bytes()
            raw = (
                dpapi(content[3:], True)
                if content.startswith(b"DP1") and os.name == "nt"
                else cipher().decrypt(content[3:])
                if content.startswith(b"FE1")
                else b""
            )
            value = json.loads(raw)
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError, TypeError, InvalidToken):
            return {}


def protected_save(name, value):
    if not re.fullmatch(r"[a-z-]{3,60}", name):
        raise ValueError("Invalid protected record name")
    with _lock:
        private_write(root() / (name + ".bin"), seal(value))


def protected_remove(name):
    if not re.fullmatch(r"[a-z-]{3,60}", name):
        raise ValueError("Invalid protected record name")
    with _lock:
        (root() / (name + ".bin")).unlink(missing_ok=True)


def load(user_id):
    with _lock:
        path = root() / f"account-{int(user_id)}.bin"
        if not path.exists():
            return None
        try:
            content = path.read_bytes()
            raw = (
                dpapi(content[3:], True)
                if content.startswith(b"DP1") and os.name == "nt"
                else cipher().decrypt(content[3:])
                if content.startswith(b"FE1")
                else b""
            )
            value = json.loads(raw)
            return value if value.get("user_id") == int(user_id) else None
        except (OSError, ValueError, InvalidToken, TypeError):
            return None


def save(user_id, value):
    with _lock:
        value = {**value, "user_id": int(user_id)}
        private_write(root() / f"account-{int(user_id)}.bin", seal(value))


def update(user_id, generation, values):
    with _lock:
        current = load(user_id)
        if not current or current.get("generation") != generation:
            return False
        save(user_id, {**current, **values})
        return True


def remove(user_id):
    with _lock:
        (root() / f"account-{int(user_id)}.bin").unlink(missing_ok=True)


def host_id():
    with _lock:
        path = root() / "host-id.txt"
        if not path.exists():
            private_write(path, ("urn:uuid:" + str(uuid.uuid4())).encode())
        return path.read_text().strip()


def usage(user_id):
    path = root() / f"usage-{int(user_id)}.bin"
    if not path.exists():
        return {}
    with _lock:
        try:
            content = path.read_bytes()
            raw = (
                dpapi(content[3:], True)
                if content.startswith(b"DP1") and os.name == "nt"
                else cipher().decrypt(content[3:])
            )
            value = json.loads(raw)
            return value if value.get("user_id") == int(user_id) else {}
        except (OSError, ValueError, TypeError, InvalidToken):
            return {}


def save_usage(user_id, values):
    with _lock:
        private_write(
            root() / f"usage-{int(user_id)}.bin", seal({**values, "user_id": int(user_id)})
        )
