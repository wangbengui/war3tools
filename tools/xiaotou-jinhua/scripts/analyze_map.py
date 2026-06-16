#!/usr/bin/env python3
"""Analyze 小偷进化 w3x map structure and extract readable assets."""

from __future__ import annotations

import json
import os
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

from mpyq import MPQArchive, MPQ_FILE_EXISTS

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = Path(r"D:\GAME\Warcraft III Frozen Throne\Maps\dz\rpg\小偷进化修改版\781DD85B990F8829A6E9758F58EFCA5B.w3x")
ANALYSIS_DIR = ROOT / "analysis"
EXTRACTED_DIR = ROOT / "extracted"


def fourcc(val: int) -> str:
    return struct.pack("<I", val).decode("latin1")


def read_field(data: bytes, off: int) -> tuple[dict | None, int]:
    if off + 8 > len(data):
        return None, off
    fid = struct.unpack_from("<I", data, off)[0]
    off += 4
    if fid == 0:
        return None, off
    vtype = struct.unpack_from("<I", data, off)[0]
    off += 4
    if vtype == 3:
        end = data.index(b"\x00", off)
        val = data[off:end].decode("utf-8", errors="replace")
        off = end + 1
    elif vtype == 2:
        val = round(struct.unpack_from("<f", data, off)[0], 6)
        off += 4
    elif vtype == 0:
        val = struct.unpack_from("<I", data, off)[0]
        off += 4
    else:
        val = f"<type{vtype}>"
        off += 4
    return {"id": fourcc(fid), "value": val}, off


def parse_w3u(data: bytes) -> list[dict]:
    ver, orig = struct.unpack_from("<2I", data, 0)
    off = 8
    for _ in range(orig):
        off += 4
        while True:
            field, off = read_field(data, off)
            if field is None:
                break
    units = []
    while off + 4 <= len(data):
        uid = data[off : off + 4]
        if uid == b"\x00\x00\x00\x00":
            break
        off += 4
        fields: dict[str, object] = {}
        while True:
            field, off = read_field(data, off)
            if field is None:
                break
            fields[field["id"]] = field["value"]
        units.append({"id": uid.decode("latin1"), "fields": fields})
    return units


def parse_w3a(data: bytes) -> list[dict]:
    ver, orig = struct.unpack_from("<2I", data, 0)
    off = 8
    for _ in range(orig):
        off += 4
        while True:
            field, off = read_field(data, off)
            if field is None:
                break
    abilities = []
    while off + 4 <= len(data):
        aid = data[off : off + 4]
        if aid == b"\x00\x00\x00\x00":
            break
        off += 4
        fields: dict[str, object] = {}
        while True:
            field, off = read_field(data, off)
            if field is None:
                break
            fields[field["id"]] = field["value"]
        abilities.append({"id": aid.decode("latin1"), "fields": fields})
    return abilities


def extract_mpq(map_path: Path) -> tuple[Path, dict]:
    raw = map_path.read_bytes()
    mpq_offset = raw.find(b"MPQ\x1a")
    if mpq_offset < 0:
        raise ValueError("MPQ section not found")

    map_name = raw[8 : raw.index(b"\x00", 8)].decode("utf-8", errors="replace")
    mpq_path = ANALYSIS_DIR / "map.mpq"
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    mpq_path.write_bytes(raw[mpq_offset:])

    archive = MPQArchive(str(mpq_path), listfile=False)
    meta = {
        "map_path": str(map_path),
        "map_name_in_header": map_name,
        "file_size": len(raw),
        "mpq_offset": mpq_offset,
        "mpq_size": len(raw) - mpq_offset,
        "block_count": archive.header["block_table_entries"],
        "hash_count": archive.header["hash_table_entries"],
    }
    return mpq_path, meta


def probe_known_files(archive: MPQArchive) -> list[dict]:
    candidates = [
        "war3map.j",
        "war3map.lua",
        "main.lua",
        "war3map.w3i",
        "war3map.w3u",
        "war3map.w3a",
        "war3map.w3t",
        "war3map.w3b",
        "war3map.w3d",
        "war3map.w3h",
        "war3map.w3q",
        "war3map.w3e",
        "war3map.w3r",
        "war3map.w3c",
        "war3map.w3s",
        "war3map.doo",
        "war3map.wpm",
        "war3map.shd",
        "war3map.mmp",
        "war3mapExtra.txt",
        "war3mapMisc.txt",
        "war3mapSkin.txt",
        "war3mapMap.blp",
        "fonts.ttf",
        "Fonts.ttf",
        "(listfile)",
        "(attributes)",
    ]
    rows = []
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    for name in candidates:
        entry = archive.get_hash_table_entry(name)
        if entry is None:
            rows.append({"name": name, "present": False})
            continue
        block = archive.block_table[entry.block_table_index]
        row = {
            "name": name,
            "present": True,
            "size": block.size,
            "archived_size": block.archived_size,
            "flags": hex(block.flags),
        }
        rows.append(row)
        if name in {"war3map.j", "(listfile)"}:
            continue
        try:
            data = archive.read_file(name)
            if data:
                out = EXTRACTED_DIR / name.replace("\\", "_").replace("/", "_")
                out.write_bytes(data)
        except Exception as exc:  # noqa: BLE001
            row["extract_error"] = str(exc)
    return rows


def scan_block_signatures(archive: MPQArchive) -> Counter:
    sigs: Counter = Counter()
    for block in archive.block_table:
        if not (block.flags & MPQ_FILE_EXISTS) or block.size == 0:
            continue
        archive.file.seek(block.offset + archive.header["offset"])
        head = archive.file.read(4)
        sigs[head] += 1
    return sigs


def main() -> int:
    if not MAP_PATH.exists():
        print(f"Map not found: {MAP_PATH}", file=sys.stderr)
        return 1

    mpq_path, meta = extract_mpq(MAP_PATH)
    archive = MPQArchive(str(mpq_path), listfile=False)
    files = probe_known_files(archive)
    meta["known_files"] = files
    meta["block_signatures"] = {
        (k.hex() if k else "empty"): v
        for k, v in scan_block_signatures(archive).most_common(20)
    }

    w3u_path = EXTRACTED_DIR / "war3map.w3u"
    if w3u_path.exists():
        meta["units"] = parse_w3u(w3u_path.read_bytes())

    w3a_path = EXTRACTED_DIR / "war3map.w3a"
    if w3a_path.exists():
        meta["abilities"] = parse_w3a(w3a_path.read_bytes())

    misc_path = EXTRACTED_DIR / "war3mapMisc.txt"
    if misc_path.exists():
        meta["misc_text"] = misc_path.read_text(encoding="utf-8", errors="replace")

    out_json = ANALYSIS_DIR / "map-analysis.json"
    out_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
