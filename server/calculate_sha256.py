#!/usr/bin/env python3
"""
Helper script to calculate SHA256 hash of files.
Useful for preparing app_version.json.

Usage:
    python calculate_sha256.py path/to/file.exe
    python calculate_sha256.py path/to/file.rar
"""
import hashlib
import sys
from pathlib import Path
from venv import logger
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
        return ""

    sha256_hash = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        result = sha256_hash.hexdigest()
       
        return result
    except Exception as e:
       
        raise



def main():
    if len(sys.argv) < 2:
        print("Usage: python calculate_sha256.py <file_path>")
        print("\nExample:")
        print("  python calculate_sha256.py apps/MyApp_v1.0.exe")
        sys.exit(1)

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    print(f"Calculating SHA256 for: {file_path}")
    print(f"File size: {file_path.stat().st_size / (1024*1024):.2f} MB")

    sha256 = calculate_sha256(file_path)

    print("\n" + "="*60)
    print("SHA256:")
    print(sha256)
    print("="*60)

    print("\nCopy the above hash and paste it into app_version.json:")
    print(f'  "sha256": "{sha256}"')


if __name__ == "__main__":
    main()
