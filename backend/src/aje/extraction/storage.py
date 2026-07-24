import hashlib
from pathlib import Path

from aje.config import get_settings


def compute_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def save_upload(content: bytes, filename: str) -> tuple[Path, str]:
    digest = compute_hash(content)
    ext = Path(filename).suffix.lower()
    uploads = get_settings().data_dir / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    dest = uploads / f"{digest}{ext}"
    dest.write_bytes(content)
    return dest, digest
