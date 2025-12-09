"""
File utilities for app updates.
- Calculate SHA256 hash
- Extract .rar files
- Run .exe installers
"""
import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from logger_config import logger


def calculate_sha256(filepath: Path | str) -> str:
    """
    Calculate SHA256 hash of a file.
    
    Args:
        filepath: Path to the file
        
    Returns:
        SHA256 hex digest (lowercase)
    """
    path = Path(filepath)
    if not path.exists():
        logger.error("File not found for hashing: %s", path)
        return ""

    sha256_hash = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        result = sha256_hash.hexdigest()
        logger.debug("SHA256 for %s: %s", path.name, result)
        return result
    except Exception as e:
        logger.error("Failed to calculate SHA256 for %s: %s", path, e)
        raise


def extract_rar(rar_path: Path | str, extract_to: Path | str) -> None:
    """
    Extract a .rar file to target directory.
    Requires WinRAR or 7-Zip to be installed on Windows.
    
    Args:
        rar_path: Path to the .rar file
        extract_to: Target directory for extraction
        
    Raises:
        FileNotFoundError: If rar file doesn't exist
        Exception: If extraction fails
    """
    rar_path = Path(rar_path)
    extract_to = Path(extract_to)

    if not rar_path.exists():
        logger.error("RAR file not found: %s", rar_path)
        raise FileNotFoundError(f"RAR file not found: {rar_path}")

    extract_to.mkdir(parents=True, exist_ok=True)

    logger.info("Extracting RAR: %s -> %s", rar_path, extract_to)

    try:
        # Try using 7-Zip first (usually available on Windows)
        try:
            subprocess.run(
                ["7z", "x", str(rar_path), f"-o{str(extract_to)}", "-y"],
                check=True,
                capture_output=True,
                timeout=300
            )
            logger.info("RAR extracted successfully using 7-Zip")
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

        # Fallback to WinRAR
        try:
            subprocess.run(
                ["rar", "x", "-y", str(rar_path), str(extract_to)],
                check=True,
                capture_output=True,
                timeout=300
            )
            logger.info("RAR extracted successfully using WinRAR")
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

        # Last resort: try with ShellExecute on Windows
        import ctypes
        try:
            # Use Windows Shell to extract RAR (requires WinRAR installed)
            shell = ctypes.windll.shell.ShellExecuteW
            shell(
                None, "open", "rar.exe",
                f'x -y "{rar_path}" "{extract_to}"',
                None, 1
            )
            logger.info("RAR extraction initiated via ShellExecute")
            return
        except Exception:
            logger.error("All extraction methods failed for: %s", rar_path)
            raise Exception(
                f"Could not extract RAR file. Please install 7-Zip or WinRAR.\n"
                f"File: {rar_path}"
            )

    except Exception as e:
        logger.error("Failed to extract RAR file: %s", e)
        raise


def run_exe_installer(exe_path: Path | str) -> subprocess.Popen:
    """
    Run an .exe installer or application.
    Runs asynchronously without blocking.
    
    Args:
        exe_path: Path to the .exe file
        
    Returns:
        Popen process object
        
    Raises:
        FileNotFoundError: If exe doesn't exist
        Exception: If execution fails
    """
    exe_path = Path(exe_path)

    if not exe_path.exists():
        logger.error("EXE file not found: %s", exe_path)
        raise FileNotFoundError(f"EXE file not found: {exe_path}")

    logger.info("Running EXE installer: %s", exe_path)

    try:
        # On Windows, use shell=False for security and reliability
        process = subprocess.Popen(
            [str(exe_path)],
            cwd=str(exe_path.parent),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logger.info("EXE process started with PID: %d", process.pid)
        return process
    except Exception as e:
        logger.error("Failed to run EXE: %s", e)
        raise


def verify_file_integrity(filepath: Path | str, expected_sha256: str) -> bool:
    """
    Verify file integrity by comparing SHA256 hash.
    
    Args:
        filepath: Path to the file
        expected_sha256: Expected SHA256 hex string (can be uppercase or lowercase)
        
    Returns:
        True if hash matches, False otherwise
    """
    actual_sha256 = calculate_sha256(filepath)
    expected_sha256_lower = expected_sha256.lower()
    
    if actual_sha256 == expected_sha256_lower:
        logger.info("File integrity verified: %s", Path(filepath).name)
        return True
    else:
        logger.error(
            "File integrity check failed for %s\nExpected: %s\nActual: %s",
            filepath, expected_sha256_lower, actual_sha256
        )
        return False


def remove_file(filepath: Path | str) -> None:
    """
    Safely remove a file.
    
    Args:
        filepath: Path to the file
    """
    path = Path(filepath)
    try:
        if path.exists():
            path.unlink()
            logger.info("File removed: %s", path)
    except Exception as e:
        logger.error("Failed to remove file %s: %s", path, e)
        raise


def remove_directory(dirpath: Path | str) -> None:
    """
    Recursively remove a directory.
    
    Args:
        dirpath: Path to the directory
    """
    path = Path(dirpath)
    try:
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
            logger.info("Directory removed: %s", path)
    except Exception as e:
        logger.error("Failed to remove directory %s: %s", path, e)
        raise
