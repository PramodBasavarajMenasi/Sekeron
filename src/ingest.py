from __future__ import annotations

import mimetypes
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from .schemas import ArtistInventory

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
TEXT_EXTS = {".txt", ".md", ".rtf"}
PROFILE_EXTS = TEXT_EXTS | {".docx"}


def resolve_dataset_root(path: str | Path) -> Path:
    root = Path(path)
    if root.exists():
        return root
    fallback = Path("Data set")
    if fallback.exists():
        return fallback
    raise FileNotFoundError(f"Dataset folder not found: {path}")


def artist_root(data_root: Path) -> Path:
    for candidate in (data_root / "artists", data_root / "artist_profiles"):
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Expected artists/ or artist_profiles/ under dataset root")


def briefs_root(data_root: Path) -> Path:
    for candidate in (data_root / "briefs", data_root / "hirer_conversations"):
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Expected briefs/ or hirer_conversations/ under dataset root")


def follow_up_file(data_root: Path) -> Path | None:
    candidates = [
        data_root / "follow_up" / "updated_brief.txt",
        data_root / "follow_up_update",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
        if candidate.is_dir():
            files = sorted(candidate.glob("*.txt"))
            if files:
                return files[0]
    return None


def detect_file_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTS:
        return "image"
    if suffix in AUDIO_EXTS:
        return "audio"
    if suffix in VIDEO_EXTS:
        return "video"
    if suffix in PROFILE_EXTS:
        return "profile"
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "unknown"


def read_text(path: Path) -> tuple[str, str | None]:
    try:
        if path.suffix.lower() == ".docx":
            return read_docx_text(path), None
        return path.read_text(encoding="utf-8", errors="replace"), None
    except Exception as exc:  # damaged/unreadable files should not stop the run
        return "", f"{path}: {exc}"


def read_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as docx:
        xml = docx.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace))
        if text.strip():
            paragraphs.append(text.strip())
    return "\n".join(paragraphs)


def build_artist_inventory(data_root: Path) -> list[ArtistInventory]:
    root = artist_root(data_root)
    inventories: list[ArtistInventory] = []
    for category_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        category = category_dir.name
        for folder in sorted(p for p in category_dir.iterdir() if p.is_dir()):
            profile_files: list[str] = []
            media_files: list[str] = []
            damaged_files: list[str] = []
            for file_path in sorted(p for p in folder.rglob("*") if p.is_file()):
                if should_ignore_file(file_path):
                    continue
                rel = str(file_path)
                kind = detect_file_type(file_path)
                if kind == "profile":
                    profile_files.append(rel)
                    _, error = read_text(file_path)
                    if error:
                        damaged_files.append(error)
                elif kind in {"image", "audio", "video"}:
                    media_files.append(rel)
                else:
                    damaged_files.append(f"Unsupported file type: {file_path}")
            inventories.append(
                ArtistInventory(
                    artist_id=folder.name,
                    name=folder.name.replace("_", " "),
                    category=category,
                    folder=str(folder),
                    profile_files=profile_files,
                    media_files=media_files,
                    damaged_files=damaged_files,
                )
            )
    return inventories


def should_ignore_file(path: Path) -> bool:
    ignored_names = {".DS_Store", "Thumbs.db", "desktop.ini"}
    return path.name in ignored_names or any(part.startswith("__MACOSX") for part in path.parts)
