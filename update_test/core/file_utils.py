# core/file_utils.py
import hashlib
import subprocess
from pathlib import Path

import rarfile  # pip install rarfile


def calculate_sha256(filepath: str | Path) -> str:
    """
    Calculate SHA256 hash for a file.
    Returns empty string if file does not exist.
    """
    path = Path(filepath)
    if not path.exists():
        return ""
    sha256 = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def extract_rar(rar_path: str | Path, extract_to: str | Path) -> None:
    """
    Extract a .rar file to a target directory.
    """
    rar_path = Path(rar_path)
    extract_to = Path(extract_to)
    extract_to.mkdir(parents=True, exist_ok=True)

    with rarfile.RarFile(rar_path) as rf:
        rf.extractall(path=extract_to)


def run_exe(exe_path: str | Path) -> None:
    """
    Run an .exe installer or app.
    """
    exe_path = str(Path(exe_path))
    subprocess.Popen([exe_path], shell=True)
