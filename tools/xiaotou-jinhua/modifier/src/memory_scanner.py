"""Memory read/write and Cheat-Engine-style scanning."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator

from pymem import Pymem
from pymem.memory import read_bytes, virtual_query, write_bytes
from pymem.process import module_from_name


class ValueType(str, Enum):
    INT32 = "int32"
    FLOAT = "float"
    DOUBLE = "double"


@dataclass
class ScanMatch:
    address: int
    value_type: ValueType
    value: int | float


@dataclass
class ScanSession:
    value_type: ValueType
    matches: list[int] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.matches)


class MemoryAccess:
    """Attach to war3.exe and perform region scans."""

    CHUNK = 1024 * 1024  # 1 MB per read chunk

    def __init__(self) -> None:
        self.pm: Pymem | None = None
        self.session: ScanSession | None = None

    @property
    def attached(self) -> bool:
        return self.pm is not None

    @property
    def pid(self) -> int | None:
        return self.pm.process_id if self.pm else None

    def attach(self, pid: int) -> None:
        self.detach()
        self.pm = Pymem()
        self.pm.open_process_from_id(pid)
        self.session = None

    def detach(self) -> None:
        if self.pm is not None:
            try:
                self.pm.close_process()
            except Exception:
                pass
        self.pm = None
        self.session = None

    def module_base(self, name: str = "Game.dll") -> int | None:
        if not self.pm:
            return None
        for mod_name in (name, "war3.exe", "Game.dll"):
            try:
                mod = module_from_name(self.pm.process_handle, mod_name)
                return mod.lpBaseOfDll
            except Exception:
                continue
        return None

    def _pack(self, value_type: ValueType, value: float | int) -> bytes:
        if value_type == ValueType.INT32:
            return struct.pack("<i", int(value))
        if value_type == ValueType.FLOAT:
            return struct.pack("<f", float(value))
        return struct.pack("<d", float(value))

    def _unpack(self, value_type: ValueType, data: bytes) -> int | float:
        if value_type == ValueType.INT32:
            return struct.unpack("<i", data)[0]
        if value_type == ValueType.FLOAT:
            return struct.unpack("<f", data)[0]
        return struct.unpack("<d", data)[0]

    def _size(self, value_type: ValueType) -> int:
        return {ValueType.INT32: 4, ValueType.FLOAT: 4, ValueType.DOUBLE: 8}[value_type]

    def iter_readable_regions(self) -> Iterator[tuple[int, int]]:
        if not self.pm:
            return
        handle = self.pm.process_handle
        address = 0
        # PAGE_* 可读区域
        readable_protect = {
            0x02,  # PAGE_READONLY
            0x04,  # PAGE_READWRITE
            0x08,  # PAGE_WRITECOPY
            0x20,  # PAGE_EXECUTE_READ
            0x40,  # PAGE_EXECUTE_READWRITE
            0x80,  # PAGE_EXECUTE_WRITECOPY
        }
        while address < 0x7FFFFFFF0000:
            try:
                mbi = virtual_query(handle, address)
            except Exception:
                break
            base = mbi.BaseAddress
            size = mbi.RegionSize
            if mbi.State == 0x1000 and size > 0 and mbi.Protect in readable_protect:
                yield base, size
            next_addr = base + size
            if next_addr <= address:
                break
            address = next_addr

    def first_scan(self, value_type: ValueType, value: float | int) -> ScanSession:
        if not self.pm:
            raise RuntimeError("未附加进程")
        needle = self._pack(value_type, value)
        size = self._size(value_type)
        matches: list[int] = []
        handle = self.pm.process_handle
        for base, region_size in self.iter_readable_regions():
            offset = 0
            while offset < region_size:
                read_size = min(self.CHUNK, region_size - offset)
                try:
                    chunk = read_bytes(handle, base + offset, read_size)
                except Exception:
                    offset += read_size
                    continue
                start = 0
                while True:
                    idx = chunk.find(needle, start)
                    if idx < 0:
                        break
                    matches.append(base + offset + idx)
                    start = idx + size
                offset += read_size
        self.session = ScanSession(value_type=value_type, matches=matches)
        return self.session

    def next_scan(self, value: float | int) -> ScanSession:
        if not self.pm or not self.session:
            raise RuntimeError("请先进行首次扫描")
        needle = self._pack(self.session.value_type, value)
        size = self._size(self.session.value_type)
        handle = self.pm.process_handle
        kept: list[int] = []
        for addr in self.session.matches:
            try:
                data = read_bytes(handle, addr, size)
            except Exception:
                continue
            if data == needle:
                kept.append(addr)
        self.session.matches = kept
        return self.session

    def read_value(self, address: int, value_type: ValueType) -> int | float:
        if not self.pm:
            raise RuntimeError("未附加进程")
        size = self._size(value_type)
        data = read_bytes(self.pm.process_handle, address, size)
        return self._unpack(value_type, data)

    def write_value(self, address: int, value_type: ValueType, value: float | int) -> None:
        if not self.pm:
            raise RuntimeError("未附加进程")
        write_bytes(self.pm.process_handle, address, self._pack(value_type, value), len(self._pack(value_type, value)))

    def read_matches(self, limit: int = 200) -> list[ScanMatch]:
        if not self.pm or not self.session:
            return []
        out: list[ScanMatch] = []
        for addr in self.session.matches[:limit]:
            try:
                val = self.read_value(addr, self.session.value_type)
                out.append(ScanMatch(address=addr, value_type=self.session.value_type, value=val))
            except Exception:
                continue
        return out
