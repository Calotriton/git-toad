"""Zero-dependency GIF and PNG encoders for indexed pixel art."""

from __future__ import annotations

import struct
import zlib


def _lzw(indices: list[int], min_size: int) -> bytes:
    clear = 1 << min_size
    eoi = clear + 1
    code_size = min_size + 1
    next_code = eoi + 1
    table: dict[int, int] = {}
    out = bytearray()
    acc = clear
    nbits = code_size

    it = iter(indices)
    prefix = next(it)
    for k in it:
        key = (prefix << 8) | k
        code = table.get(key)
        if code is not None:
            prefix = code
            continue
        acc |= prefix << nbits
        nbits += code_size
        while nbits >= 8:
            out.append(acc & 255)
            acc >>= 8
            nbits -= 8
        if next_code == 4096:
            acc |= clear << nbits
            nbits += code_size
            while nbits >= 8:
                out.append(acc & 255)
                acc >>= 8
                nbits -= 8
            table.clear()
            next_code = eoi + 1
            code_size = min_size + 1
        else:
            if next_code >= (1 << code_size):
                code_size += 1
            table[key] = next_code
            next_code += 1
        prefix = k

    for code in (prefix, eoi):
        acc |= code << nbits
        nbits += code_size
        while nbits >= 8:
            out.append(acc & 255)
            acc >>= 8
            nbits -= 8
    if nbits:
        out.append(acc & 255)
    return bytes(out)


def _blocks(data: bytes) -> bytes:
    out = bytearray()
    for i in range(0, len(data), 255):
        chunk = data[i : i + 255]
        out.append(len(chunk))
        out += chunk
    out.append(0)
    return bytes(out)


def _upscale(frame: list[int], width: int, rect: tuple[int, int, int, int], scale: int) -> list[int]:
    x0, y0, x1, y1 = rect
    out: list[int] = []
    for y in range(y0, y1):
        row: list[int] = []
        base = y * width
        for x in range(x0, x1):
            row.extend([frame[base + x]] * scale)
        for _ in range(scale):
            out.extend(row)
    return out


def encode_gif(frames: list[list[int]], width: int, height: int, scale: int, delay_cs: int) -> bytes:
    """Encode frames of 0xRRGGBB pixels (logical size) into a looping, upscaled GIF."""
    colors: dict[int, int] = {}
    indexed: list[list[int]] = []
    for frame in frames:
        idx = []
        for c in frame:
            i = colors.get(c)
            if i is None:
                i = colors[c] = len(colors)
            idx.append(i)
        indexed.append(idx)
    if len(colors) > 256:
        raise ValueError(f"too many colors for GIF: {len(colors)}")

    bits = max(2, (len(colors) - 1).bit_length())
    table = bytearray(3 << bits)
    for c, i in colors.items():
        table[i * 3 : i * 3 + 3] = bytes(((c >> 16) & 255, (c >> 8) & 255, c & 255))

    out = bytearray(b"GIF89a")
    out += struct.pack("<HHBBB", width * scale, height * scale, 0x80 | ((bits - 1) << 4) | (bits - 1), 0, 0)
    out += table
    out += b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"

    # Only re-encode the rectangle that changed since the previous frame.
    plan: list[list] = []
    prev = None
    for idx in indexed:
        if prev is None:
            plan.append([(0, 0, width, height), idx, delay_cs])
        else:
            xs, ys = [], []
            for p in range(width * height):
                if idx[p] != prev[p]:
                    xs.append(p % width)
                    ys.append(p // width)
            if not xs:
                plan[-1][2] += delay_cs
            else:
                plan.append([(min(xs), min(ys), max(xs) + 1, max(ys) + 1), idx, delay_cs])
        prev = idx

    for rect, idx, delay in plan:
        x0, y0, x1, y1 = rect
        out += struct.pack("<BBBBHBB", 0x21, 0xF9, 4, 1 << 2, delay, 0, 0)
        out += struct.pack("<BHHHHB", 0x2C, x0 * scale, y0 * scale, (x1 - x0) * scale, (y1 - y0) * scale, 0)
        out.append(bits)
        out += _blocks(_lzw(_upscale(idx, width, rect, scale), bits))
    out.append(0x3B)
    return bytes(out)


def encode_png(frame: list[int], width: int, height: int, scale: int) -> bytes:
    raw = bytearray()
    for y in range(height):
        row = bytearray()
        for x in range(width):
            c = frame[y * width + x]
            row += bytes(((c >> 16) & 255, (c >> 8) & 255, c & 255)) * scale
        for _ in range(scale):
            raw.append(0)
            raw += row

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width * scale, height * scale, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
