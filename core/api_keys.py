# core/api_keys.py
from pathlib import Path


def load_api_key(path: str = "apikeys.properties") -> str:
    """
    Load API_KEY from a properties file.
    Format:
        API_KEY=your_key_here
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Please create it with line: API_KEY=your_key"
        )

    api_key = None
    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("API_KEY="):
                api_key = line.split("=", 1)[1].strip()
                break

    if not api_key:
        raise ValueError("API_KEY not found in apikeys.properties")

    return api_key
