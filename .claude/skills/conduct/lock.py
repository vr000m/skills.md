"""Advisory lockfile helper for the conduct skill.

Primary mechanism: ``fcntl.flock`` on a lockfile fd — portable across macOS and
Linux with no external dependency. ``flock(1)`` is not used because it is not
present on macOS by default. Fallback if ``fcntl`` is unavailable: atomic
``mkdir`` lockdir.

Stale locks older than ``STALE_SECONDS`` are broken with a warning printed to
stderr.

CLI usage:

    python3 lock.py acquire <lockfile>   # exit 0 on acquire; prints pid
    python3 lock.py release <lockfile>   # exit 0 on release
    python3 lock.py status  <lockfile>   # exit 0 if free, 1 if held

Python usage::

    from lock import StateLock
    with StateLock(path) as lock:
        # ... exclusive section ...
"""

from __future__ import annotations

import errno
import os
import sys
import time
from pathlib import Path

try:
    import fcntl  # POSIX only
except ImportError:  # pragma: no cover - Windows has no fcntl
    fcntl = None  # type: ignore[assignment]

STALE_SECONDS = 60 * 60  # 1 hour


class LockError(RuntimeError):
    pass


class StateLock:
    """Advisory lock on a given lockfile path.

    Prefers ``fcntl.flock``. Falls back to atomic ``mkdir`` of ``<path>.lockdir``
    when ``fcntl`` is unavailable.
    """

    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)
        self._fd: int | None = None
        self._lockdir: Path | None = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._break_stale()

        if fcntl is not None:
            self._acquire_flock()
        else:
            self._acquire_mkdir()

    def release(self) -> None:
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)  # type: ignore[union-attr]
            finally:
                os.close(self._fd)
                self._fd = None
                try:
                    self.path.unlink()
                except FileNotFoundError:
                    pass
        if self._lockdir is not None:
            try:
                self._lockdir.rmdir()
            except FileNotFoundError:
                pass
            self._lockdir = None

    def __enter__(self) -> "StateLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()

    def _acquire_flock(self) -> None:
        fd = os.open(str(self.path), os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[union-attr]
        except OSError as err:
            os.close(fd)
            if err.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                raise LockError(f"Lock held: {self.path}") from None
            raise
        os.write(fd, f"{os.getpid()}\n".encode())
        os.fsync(fd)
        self._fd = fd

    def _acquire_mkdir(self) -> None:
        lockdir = self.path.with_suffix(self.path.suffix + ".lockdir")
        try:
            lockdir.mkdir()
        except FileExistsError:
            raise LockError(f"Lock held: {lockdir}") from None
        (lockdir / "pid").write_text(f"{os.getpid()}\n")
        self._lockdir = lockdir

    def _break_stale(self) -> None:
        candidates: list[Path] = []
        if self.path.exists():
            candidates.append(self.path)
        lockdir = self.path.with_suffix(self.path.suffix + ".lockdir")
        if lockdir.exists():
            candidates.append(lockdir)

        now = time.time()
        for candidate in candidates:
            try:
                age = now - candidate.stat().st_mtime
            except FileNotFoundError:
                continue
            if age <= STALE_SECONDS:
                continue
            sys.stderr.write(
                f"conduct: breaking stale lock {candidate} (age={int(age)}s)\n"
            )
            if candidate.is_dir():
                for child in candidate.iterdir():
                    child.unlink()
                candidate.rmdir()
            else:
                candidate.unlink()


def _cli_acquire(path: str) -> int:
    lock = StateLock(path)
    try:
        lock.acquire()
    except LockError as err:
        sys.stderr.write(f"{err}\n")
        return 1
    sys.stdout.write(f"{os.getpid()}\n")
    return 0


def _cli_release(path: str) -> int:
    lock = StateLock(path)
    lock._fd = None  # release-only path does not reacquire
    lock._lockdir = None
    lock_path = Path(path)
    lockdir = lock_path.with_suffix(lock_path.suffix + ".lockdir")
    if lockdir.exists():
        for child in lockdir.iterdir():
            child.unlink()
        lockdir.rmdir()
    elif lock_path.exists():
        lock_path.unlink()
    return 0


def _cli_status(path: str) -> int:
    lock_path = Path(path)
    lockdir = lock_path.with_suffix(lock_path.suffix + ".lockdir")
    if lockdir.exists():
        return 1
    if not lock_path.exists():
        return 0
    if fcntl is None:
        return 1
    fd = os.open(str(lock_path), os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[union-attr]
        fcntl.flock(fd, fcntl.LOCK_UN)  # type: ignore[union-attr]
        return 0
    except OSError:
        return 1
    finally:
        os.close(fd)


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in {"acquire", "release", "status"}:
        sys.stderr.write("usage: lock.py {acquire|release|status} <lockfile>\n")
        return 2
    action, path = argv[1], argv[2]
    if action == "acquire":
        return _cli_acquire(path)
    if action == "release":
        return _cli_release(path)
    return _cli_status(path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
