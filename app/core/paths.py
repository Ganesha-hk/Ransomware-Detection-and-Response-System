import os
import stat
from pathlib import Path


def approved(path, root, exclusions=()):
    p, r = Path(path).absolute(), Path(root).resolve()
    if ".." in p.parts or not p.is_relative_to(r):
        return False
    if not p.resolve().is_relative_to(r):
        return False
    if any(p == Path(x) or p.is_relative_to(Path(x)) for x in exclusions):
        return False
    return not any(x.is_symlink() for x in [p, *p.parents] if x.is_relative_to(r))


def safe_open(path, root, exclusions=()):
    if not approved(path, root, exclusions):
        raise ValueError("Unsafe path")
    # Open each component relative to pinned directory descriptors, without symlinks.
    parts = Path(path).absolute().relative_to(Path(root).resolve()).parts
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        result = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        if not stat.S_ISREG(os.fstat(result).st_mode):
            os.close(result)
            raise ValueError("Not a regular file")
        return os.fdopen(result, "rb")
    finally:
        os.close(fd)
