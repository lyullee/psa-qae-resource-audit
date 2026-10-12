"""Build a compact visual-QA contact sheet from rendered manuscript pages."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--thumb-width", type=int, default=360)
    args = parser.parse_args()

    pages = sorted(args.input_dir.glob("page-*.png"))
    if not pages:
        raise SystemExit("No page PNGs found")
    samples: list[Image.Image] = []
    label_height = 28
    for index, path in enumerate(pages, start=1):
        with Image.open(path) as source:
            scale = args.thumb_width / source.width
            thumb = source.convert("RGB").resize(
                (args.thumb_width, round(source.height * scale)), Image.Resampling.LANCZOS
            )
        tile = Image.new("RGB", (thumb.width, thumb.height + label_height), "white")
        tile.paste(thumb, (0, label_height))
        ImageDraw.Draw(tile).text((8, 6), f"Page {index}", fill="black")
        samples.append(tile)

    rows = math.ceil(len(samples) / args.columns)
    cell_width = max(x.width for x in samples)
    cell_height = max(x.height for x in samples)
    sheet = Image.new("RGB", (cell_width * args.columns, cell_height * rows), "#d9d9d9")
    for index, tile in enumerate(samples):
        x = (index % args.columns) * cell_width
        y = (index // args.columns) * cell_height
        sheet.paste(tile, (x, y))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output, optimize=True)
    print(f"{len(pages)} pages -> {args.output}")


if __name__ == "__main__":
    main()
