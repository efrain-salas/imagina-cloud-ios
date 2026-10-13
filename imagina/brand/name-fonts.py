#!/usr/bin/env python3
"""Writes the Instrument Sans files that Imagina Cloud bundles (imagina/Sources/Fonts/). See IMAGINA.md.

The brand kit's static instances of Instrument Sans (instrument_sans_{regular,medium,semibold,bold}.ttf) are cut from
the variable font without renaming, so the four files say «Instrument Sans Regular» (PostScript name
InstrumentSans-Regular) and iOS, which finds a font by that name, would keep only one of them. This gives each file its
own names, as the family has them (InstrumentSans-Medium, InstrumentSans-SemiBold, InstrumentSans-Bold) and sets the bold
flags of the Bold one; the glyphs are not touched. The SIL Open Font License allows it: the family declares no Reserved
Font Name.

Usage: python3 -I imagina/brand/name-fonts.py <folder with the brand kit's fonts>
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

DESTINATION = Path(__file__).resolve().parent.parent / "Sources" / "Fonts"

FAMILY = "Instrument Sans"

# kit file -> (PostScript style, name of the family for apps that only know regular/bold, its style, typographic style)
STYLES = {
    "instrument_sans_regular.ttf": ("Regular", FAMILY, "Regular", None),
    "instrument_sans_medium.ttf": ("Medium", f"{FAMILY} Medium", "Regular", "Medium"),
    "instrument_sans_semibold.ttf": ("SemiBold", f"{FAMILY} SemiBold", "Regular", "SemiBold"),
    "instrument_sans_bold.ttf": ("Bold", FAMILY, "Bold", None),
}

NAME_IDS_REPLACED = {1, 2, 3, 4, 6, 16, 17}


def read_tables(data: bytes) -> dict[str, bytes]:
    count = struct.unpack(">H", data[4:6])[0]
    tables = {}
    for index in range(count):
        tag, _checksum, offset, length = struct.unpack(">4sIII", data[12 + 16 * index:28 + 16 * index])
        tables[tag.decode("latin1")] = data[offset:offset + length]
    return tables


def checksum(data: bytes) -> int:
    padded = data + b"\0" * (-len(data) % 4)
    return sum(struct.unpack(f">{len(padded) // 4}I", padded)) & 0xFFFFFFFF


def build_name_table(original: bytes, names: dict[int, str]) -> bytes:
    _format, count, string_offset = struct.unpack(">HHH", original[:6])
    records = []
    for index in range(count):
        platform, encoding, language, name_id, length, offset = struct.unpack(">6H", original[6 + 12 * index:18 + 12 * index])
        if name_id in NAME_IDS_REPLACED:
            continue
        records.append((platform, encoding, language, name_id, original[string_offset + offset:string_offset + offset + length]))
    for name_id, value in names.items():
        records.append((3, 1, 1033, name_id, value.encode("utf-16-be")))
    records.sort(key=lambda record: record[:4])

    storage = b""
    entries = b""
    for platform, encoding, language, name_id, value in records:
        entries += struct.pack(">6H", platform, encoding, language, name_id, len(value), len(storage))
        storage += value
    return struct.pack(">HHH", 0, len(records), 6 + 12 * len(records)) + entries + storage


def build_font(tables: dict[str, bytes]) -> bytes:
    tags = sorted(tables)
    tables = dict(tables)
    head = bytearray(tables["head"])
    head[8:12] = b"\0\0\0\0"
    tables["head"] = bytes(head)

    count = len(tags)
    entry_selector = count.bit_length() - 1
    search_range = (1 << entry_selector) * 16
    header = struct.pack(">IHHHH", 0x00010000, count, search_range, entry_selector, count * 16 - search_range)

    offset = 12 + 16 * count
    directory = b""
    body = b""
    for tag in tags:
        data = tables[tag]
        directory += struct.pack(">4sIII", tag.encode("latin1"), checksum(data), offset + len(body), len(data))
        body += data + b"\0" * (-len(data) % 4)

    font = bytearray(header + directory + body)
    adjustment = (0xB1B0AFBA - checksum(bytes(font))) & 0xFFFFFFFF
    head_offset = 12 + 16 * count + sum(len(tables[tag]) + (-len(tables[tag]) % 4) for tag in tags[:tags.index("head")])
    font[head_offset + 8:head_offset + 12] = struct.pack(">I", adjustment)
    return bytes(font)


def name_font(source: Path, style: str, family: str, subfamily: str, typographic_style: str | None) -> bytes:
    tables = read_tables(source.read_bytes())
    postscript = f"{FAMILY.replace(' ', '')}-{style}"
    names = {
        1: family,
        2: subfamily,
        3: f"1.000;NONE;{postscript}",
        4: f"{FAMILY} {style}",
        6: postscript,
    }
    if typographic_style:
        names[16] = FAMILY
        names[17] = typographic_style
    tables["name"] = build_name_table(tables["name"], names)

    if subfamily == "Bold":
        os2 = bytearray(tables["OS/2"])
        selection = struct.unpack(">H", os2[62:64])[0]
        os2[62:64] = struct.pack(">H", (selection | 0x20) & ~0x40)
        tables["OS/2"] = bytes(os2)
        head = bytearray(tables["head"])
        head[44:46] = struct.pack(">H", struct.unpack(">H", head[44:46])[0] | 1)
        tables["head"] = bytes(head)
    return build_font(tables)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    kit = Path(sys.argv[1])
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for filename, (style, family, subfamily, typographic_style) in STYLES.items():
        font = name_font(kit / filename, style, family, subfamily, typographic_style)
        (DESTINATION / f"{FAMILY.replace(' ', '')}-{style}.ttf").write_bytes(font)
    print(f"Instrument Sans written to {DESTINATION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
