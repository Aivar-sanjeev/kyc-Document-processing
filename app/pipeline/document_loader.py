from typing import Literal

import fitz  # PyMuPDF

MediaType = Literal["image/png", "image/jpeg"]


def bytes_to_png_and_media_type(data: bytes, filename: str | None) -> tuple[bytes, MediaType]:
    name = (filename or "").lower()
    if name.endswith(".pdf") or data[:4] == b"%PDF":
        return _pdf_first_page_to_png(data), "image/png"
    if name.endswith((".jpg", ".jpeg")) or data[:2] == b"\xff\xd8":
        return data, "image/jpeg"
    return data, "image/png"


def _pdf_first_page_to_png(data: bytes) -> bytes:
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        return pix.tobytes("png")
    finally:
        doc.close()
