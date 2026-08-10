"""Load PDF, image, and text media for multimodal prompts."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from openprompt.core.ast.models import MediaAttachment, MediaType


def load_media(path: str | Path, *, use_vision: bool = False) -> MediaAttachment:
    """Load a file into a MediaAttachment with optional text extraction."""
    file_path = Path(path).resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"Media not found: {file_path}")

    mime, _ = mimetypes.guess_type(str(file_path))
    suffix = file_path.suffix.lower()

    if suffix == ".pdf" or (mime and "pdf" in mime):
        return _load_pdf(file_path, mime, use_vision=use_vision)
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".tiff", ".bmp"} or (
        mime and mime.startswith("image/")
    ):
        return _load_image(file_path, mime, use_vision=use_vision)

    text = file_path.read_text(encoding="utf-8", errors="replace")
    return MediaAttachment(
        path=str(file_path),
        mime_type=mime or "text/plain",
        media_type=MediaType.TEXT,
        label=file_path.name,
        extracted_text=text,
        use_vision=False,
    )


def load_media_batch(paths: list[str | Path], *, use_vision: bool = False) -> list[MediaAttachment]:
    return [load_media(p, use_vision=use_vision) for p in paths]


def media_to_base64(attachment: MediaAttachment) -> tuple[str, str]:
    """Return (base64_data, mime_type) for vision APIs."""
    if not attachment.path:
        raise ValueError("Media attachment has no path.")
    data = Path(attachment.path).read_bytes()
    mime = attachment.mime_type or mimetypes.guess_type(attachment.path)[0] or "application/octet-stream"
    return base64.standard_b64encode(data).decode("ascii"), mime


def _load_pdf(path: Path, mime: str | None, *, use_vision: bool) -> MediaAttachment:
    extracted = _extract_pdf_text(path)
    return MediaAttachment(
        path=str(path),
        mime_type=mime or "application/pdf",
        media_type=MediaType.PDF,
        label=path.name,
        extracted_text=extracted,
        use_vision=use_vision,
    )


def _load_image(path: Path, mime: str | None, *, use_vision: bool) -> MediaAttachment:
    return MediaAttachment(
        path=str(path),
        mime_type=mime or "image/png",
        media_type=MediaType.IMAGE,
        label=path.name,
        use_vision=use_vision or True,
    )


def _extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(p.strip() for p in pages if p.strip())
        if text.strip():
            return text
    except ImportError:
        pass
    except Exception:
        pass

    return (
        f"[PDF: {path.name} — install pypdf for text extraction: pip install 'openprompt[media]'. "
        "Enable use_vision on the attachment or provider vision model for image-based PDF parsing.]"
    )
