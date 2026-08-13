from io import BytesIO

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

IMAGE_FORMATS = {"image/png": "PNG", "image/jpeg": "JPEG"}


def validate_image(content: bytes, content_type: str, subject: str) -> None:
    if not content:
        raise HTTPException(status_code=400, detail=f"{subject} ist leer")
    expected_format = IMAGE_FORMATS.get(content_type)
    if expected_format is None:
        raise HTTPException(status_code=400, detail=f"{subject} hat einen ungültigen MIME-Typ")
    try:
        with Image.open(BytesIO(content)) as image:
            actual_format = image.format
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(status_code=400, detail=f"{subject} ist keine gültige Bilddatei")
    if actual_format != expected_format:
        raise HTTPException(
            status_code=400,
            detail=f"Dateiinhalt und MIME-Typ von {subject} stimmen nicht überein",
        )


def validate_pdf(content: bytes, subject: str) -> None:
    if not content.startswith(b"%PDF-") or b"%%EOF" not in content[-1024:]:
        raise HTTPException(status_code=400, detail=f"{subject} ist keine gültige PDF-Datei")
