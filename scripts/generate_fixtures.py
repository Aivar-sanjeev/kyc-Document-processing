"""
Generate small synthetic PNG fixtures for manual NIM runs and demo documentation.
Does not contain real identity data — only layout-like cues for local testing.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter


def _try_font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf", "calibri.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def write_card(path: Path, title: str, lines: list[str], size: tuple[int, int]) -> None:
    img = Image.new("RGB", size, color=(248, 250, 252))
    d = ImageDraw.Draw(img)
    font_title = _try_font(28)
    font_body = _try_font(20)
    d.text((24, 20), title, fill=(15, 23, 42), font=font_title)
    y = 70
    for line in lines:
        d.text((24, y), line, fill=(30, 41, 59), font=font_body)
        y += 32
    img.save(path, format="PNG")


def degrade(in_path: Path, out_path: Path) -> None:
    img = Image.open(in_path).convert("RGB")
    img = img.resize((img.width // 3, img.height // 3), Image.Resampling.BILINEAR)
    img = img.resize((img.width * 3, img.height * 3), Image.Resampling.BILINEAR)
    img = img.filter(ImageFilter.GaussianBlur(radius=1.2))
    img.save(out_path, format="PNG", optimize=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("tests/fixtures"))
    args = ap.parse_args()
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)

    write_card(
        out / "synthetic_pan.png",
        "INCOME TAX DEPARTMENT (SYNTHETIC)",
        [
            "Permanent Account Number Card",
            "Name: DEMO USER",
            "Father's Name: DEMO PARENT",
            "DOB: 01/01/1990",
            "PAN: ABCDE1234F",
        ],
        (900, 520),
    )

    write_card(
        out / "synthetic_aadhaar.png",
        "Government of India (SYNTHETIC)",
        [
            "Aadhaar is a proof of identity, not citizenship",
            "Name: DEMO RESIDENT",
            "DOB: 01/01/1990",
            "Gender: X",
            "Aadhaar: 1234 5678 9012",
        ],
        (900, 520),
    )

    write_card(
        out / "synthetic_voter.png",
        "ELECTOR PHOTO IDENTITY CARD (SYNTHETIC)",
        [
            "Name: DEMO VOTER",
            "Father's Name: DEMO GUARDIAN",
            "EPIC: ABC1234567",
            "Constituency: DEMO-01",
        ],
        (900, 520),
    )

    degrade(out / "synthetic_voter.png", out / "synthetic_voter_degraded.png")
    print("Wrote fixtures to", out.resolve())


if __name__ == "__main__":
    main()
