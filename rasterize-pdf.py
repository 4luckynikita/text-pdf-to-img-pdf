

#!/usr/bin/env python3
"""rasterize-pdf.py

Converts normally formatted PDFs into image-only by grabbing screenshots of every page and putting a new pdf together.

Visually, the output PDF will look identical to the input, but it will contain no text or formatting data.

Built to test OCR implementation in a closed-source software that processes PDFs.

See README.md for usage instructions.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path

import fitz  # PyMuPDF import
from PIL import Image, ImageFilter # Pillow import(s)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def rasterize_pdf(
    in_path: Path,
    out_path: Path,
    dpi: int = 200,
    downscale: float = 1.0,
    jpeg_quality: int = 70,
    blur: float = 0.0,
    rotate: float = 0.0,
    noise: float = 0.0,
    grayscale: bool = False,
) -> None:
    if not in_path.exists():
        raise FileNotFoundError(f"Input PDF not found: {in_path}")

    dpi = int(_clamp(dpi, 72, 600))
    downscale = float(_clamp(downscale, 0.1, 1.0))
    jpeg_quality = int(_clamp(jpeg_quality, 1, 95))
    blur = float(_clamp(blur, 0.0, 10.0))
    rotate = float(_clamp(rotate, -10.0, 10.0))
    noise = float(_clamp(noise, 0.0, 0.5))

    # Render scale: 72 points per inch baseline. Thanks GPT for the help here.
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    in_doc = fitz.open(str(in_path))
    out_doc = fitz.open()

    try:
        for page_index in range(in_doc.page_count):
            page = in_doc.load_page(page_index)

            pix = page.get_pixmap(matrix=mat, alpha=False)  # RGB
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

            # Optional post-processing to further stress OCR. Feel free to tweak these parameters.
            if downscale < 1.0:
                new_w = max(1, int(img.width * downscale))
                new_h = max(1, int(img.height * downscale))
                img = img.resize((new_w, new_h), resample=Image.Resampling.BILINEAR)

            if rotate != 0.0:
                # Expand so content stays within the view frame.
                img = img.rotate(rotate, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=(255, 255, 255))

            if blur > 0.0:
                img = img.filter(ImageFilter.GaussianBlur(radius=blur))

            if grayscale:
                img = img.convert("L").convert("RGB")

            if noise > 0.0:
                # Sprinkles some pixel jitter into the output to give OCR a hard time.
                # noise is fraction of 255 per channel.
                import random

                rnd = random.Random(1337 + page_index)
                px = img.load()
                w, h = img.size
                amp = int(255 * noise)
                for y in range(h):
                    for x in range(w):
                        r, g, b = px[x, y]
                        dr = rnd.randint(-amp, amp)
                        dg = rnd.randint(-amp, amp)
                        db = rnd.randint(-amp, amp)
                        px[x, y] = (
                            int(_clamp(r + dr, 0, 255)),
                            int(_clamp(g + dg, 0, 255)),
                            int(_clamp(b + db, 0, 255)),
                        )

            # Encode page image as JPEG to keep file size reasonable and further remove clarity.
            # (PNG would be cleaner; JPEG artifacts can help test OCR robustness.)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=jpeg_quality, optimize=True)
            img_bytes = buf.getvalue()

            # Create a new page sized to the image (1 point == 1/72 inch).
            # We map pixels back to points using dpi.
            page_w_pt = (img.width / dpi) * 72.0
            page_h_pt = (img.height / dpi) * 72.0

            out_page = out_doc.new_page(width=page_w_pt, height=page_h_pt)
            rect = fitz.Rect(0, 0, page_w_pt, page_h_pt)
            out_page.insert_image(rect, stream=img_bytes)

        # Save as a fresh PDF with no incremental updates.
        out_doc.save(str(out_path), deflate=True, garbage=4, clean=True)

    finally:
        out_doc.close()
        in_doc.close()


def _default_out_path(in_path: Path) -> Path:
    stem = in_path.stem
    parent = in_path.parent
    return parent / f"{stem}-rasterized.pdf"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Rasterize a PDF into an image-only PDF."
    )
    parser.add_argument("input", help="Path to input PDF")
    parser.add_argument(
        "--out",
        help="Output PDF path (default: <input>-rasterized.pdf)",
        default=None,
    )
    parser.add_argument("--dpi", type=int, default=200, help="Render DPI (72-600). Default: 200")
    parser.add_argument(
        "--downscale",
        type=float,
        default=1.0,
        help="Downscale factor (0.1-1.0). Default: 1.0",
    )
    parser.add_argument(
        "--jpeg-quality",
        type=int,
        default=70,
        help="JPEG quality (1-95). Lower = more artifacts. Default: 70",
    )
    parser.add_argument(
        "--blur",
        type=float,
        default=0.0,
        help="Gaussian blur radius (0-10). Default: 0",
    )
    parser.add_argument(
        "--rotate",
        type=float,
        default=0.0,
        help="Rotate degrees (-10 to 10). Default: 0",
    )
    parser.add_argument(
        "--noise",
        type=float,
        default=0.0,
        help="Add noise (0-0.5). Default: 0",
    )
    parser.add_argument(
        "--grayscale",
        action="store_true",
        help="Convert pages to grayscale (still saved as RGB JPEG).",
    )

    args = parser.parse_args(argv)

    in_path = Path(args.input).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve() if args.out else _default_out_path(in_path)

    rasterize_pdf(
        in_path=in_path,
        out_path=out_path,
        dpi=args.dpi,
        downscale=args.downscale,
        jpeg_quality=args.jpeg_quality,
        blur=args.blur,
        rotate=args.rotate,
        noise=args.noise,
        grayscale=args.grayscale,
    )

    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        raise SystemExit(130)