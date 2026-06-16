"""Memory scan and write for war3.exe."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator

from pymem import Pymem
from pymem.memory import read_bytes, virtual_query, write_bytes


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
    fuzzy: float = 0.0  # >0 时按 ±fuzzy 比较

    @property
    def count(self) -> int:
        return len(self.matches)


@dataclass
class SmartScanResult:
    session: ScanSession
    label: str
    count: int


@dataclass
class DiagReport:
    is_admin: bool
    attached: bool
    pid: int | None
    attach_error: str
    readable_regions: int
    readable_sample_ok: int
    fuzzy_test_count: int  # 对 1.0 做 float 模糊扫描，正常应 >0


class MemoryAccess:
    CHUNK = 1024 * 1024
    PAGE_NOACCESS = 0x01
    READABLE_BASE = {0x02, 0x04, 0x08, 0x20, 0x40, 0x80}

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

    def _size(self, value_type: ValueType) -> int:
        return 8 if value_type == ValueType.DOUBLE else 4

    def _pack(self, value_type: ValueType, value: float | int) -> bytes:
        if value_type == ValueType.INT32:
            return struct.pack("<i", int(value))
        if value_type == ValueType.DOUBLE:
            return struct.pack("<d", float(value))
        return struct.pack("<f", float(value))

    def _unpack_at(self, data: bytes, offset: int, value_type: ValueType) -> int | float:
        if value_type == ValueType.INT32:
            return struct.unpack_from("<i", data, offset)[0]
        if value_type == ValueType.DOUBLE:
            return struct.unpack_from("<d", data, offset)[0]
        return struct.unpack_from("<f", data, offset)[0]

    def _read_value(self, address: int, value_type: ValueType) -> int | float:
        size = self._size(value_type)
        data = read_bytes(self.pm.process_handle, address, size)
        return self._unpack_at(data, 0, value_type)

    def _value_matches(self, actual: int | float, target: float | int, session: ScanSession) -> bool:
        if session.fuzzy > 0 and session.value_type != ValueType.INT32:
            return abs(float(actual) - float(target)) <= session.fuzzy
        if session.value_type == ValueType.INT32:
            return int(actual) == int(target)
        if session.value_type == ValueType.DOUBLE:
            return struct.pack("<d", float(actual)) == struct.pack("<d", float(target))
        return struct.pack("<f", float(actual)) == struct.pack("<f", float(target))

    def iter_readable_regions(self) -> Iterator[tuple[int, int]]:
        if not self.pm:
            return
        handle = self.pm.process_handle
        address = 0
        while address < 0x7FFFFFFF0000:
            try:
                mbi = virtual_query(handle, address)
            except Exception:
                break
            base, size = mbi.BaseAddress, mbi.RegionSize
            prot = mbi.Protect & 0xFF
            if mbi.State == 0x1000 and size > 0 and prot in self.READABLE_BASE and prot != self.PAGE_NOACCESS:
                yield base, size
            nxt = base + size
            if nxt <= address:
                break
            address = nxt

    def _scan_exact(self, value_type: ValueType, value: float | int) -> list[int]:
        needle = self._pack(value_type, value)
        step = self._size(value_type)
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
                    start = idx + step
                offset += read_size
        return matches

    def _scan_fuzzy_float(self, value: float, epsilon: float) -> list[int]:
        lo, hi = float(value) - epsilon, float(value) + epsilon
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
                end = len(chunk) - 3
                pos = 0
                while pos < end:
                    v = struct.unpack_from("<f", chunk, pos)[0]
                    if lo <= v <= hi:
                        matches.append(base + offset + pos)
                    pos += 4
                offset += read_size
        return matches

    def _scan_fuzzy_double(self, value: float, epsilon: float) -> list[int]:
        lo, hi = float(value) - epsilon, float(value) + epsilon
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
                end = len(chunk) - 7
                pos = 0
                while pos < end:
                    v = struct.unpack_from("<d", chunk, pos)[0]
                    if lo <= v <= hi and abs(v) < 1e12:
                        matches.append(base + offset + pos)
                    pos += 8
                offset += read_size
        return matches

    def _scan_string(self, text: str) -> list[int]:
        needle = text.encode("ascii")
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
                    start = idx + 1
                offset += read_size
        return matches

    def diagnose(self) -> DiagReport:
        import ctypes

        is_admin = False
        try:
            is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            pass

        attach_error = ""
        regions = 0
        sample_ok = 0
        fuzzy_count = 0

        if not self.pm:
            attach_error = "未附加进程"
        else:
            try:
                handle = self.pm.process_handle
                addr = 0
                sample_budget = 20
                fuzzy_budget = 8 * 1024 * 1024  # 最多扫 8MB 做自检
                fuzzy_scanned = 0
                while addr < 0x7FFFFFFF0000:
                    try:
                        mbi = virtual_query(handle, addr)
                    except Exception:
                        break
                    prot = mbi.Protect & 0xFF
                    if (
                        mbi.State == 0x1000
                        and mbi.RegionSize > 0
                        and prot in self.READABLE_BASE
                        and prot != self.PAGE_NOACCESS
                    ):
                        regions += 1
                        if sample_ok < sample_budget:
                            try:
                                read_bytes(handle, mbi.BaseAddress, min(4096, mbi.RegionSize))
                                sample_ok += 1
                            except Exception:
                                pass
                        if fuzzy_scanned < fuzzy_budget:
                            take = min(mbi.RegionSize, fuzzy_budget - fuzzy_scanned)
                            try:
                                chunk = read_bytes(handle, mbi.BaseAddress, take)
                                lo, hi = 0.0, 2.0  # 快速探测：0~2 之间 float
                                end = len(chunk) - 3
                                pos = 0
                                while pos < end and fuzzy_count < 5000:
                                    v = struct.unpack_from("<f", chunk, pos)[0]
                                    if lo <= v <= hi:
                                        fuzzy_count += 1
                                    pos += 4
                                fuzzy_scanned += take
                            except Exception:
                                pass
                    nxt = mbi.BaseAddress + mbi.RegionSize
                    if nxt <= addr:
                        break
                    addr = nxt
                if regions == 0:
                    attach_error = "已打开进程但读不到任何内存区域（可能被平台保护）"
                elif sample_ok == 0:
                    attach_error = "无法读取游戏内存（需要管理员权限）"
            except Exception as exc:
                attach_error = str(exc)

        return DiagReport(
            is_admin=is_admin,
            attached=self.attached,
            pid=self.pid,
            attach_error=attach_error,
            readable_regions=regions,
            readable_sample_ok=sample_ok,
            fuzzy_test_count=fuzzy_count,
        )

    def first_scan(
        self,
        value_type: ValueType,
        value: float | int,
        fuzzy: float = 0.0,
    ) -> ScanSession:
        if not self.pm:
            raise RuntimeError("未附加进程")
        if fuzzy > 0 and value_type == ValueType.FLOAT:
            matches = self._scan_fuzzy_float(float(value), fuzzy)
        elif fuzzy > 0 and value_type == ValueType.DOUBLE:
            matches = self._scan_fuzzy_double(float(value), fuzzy)
        else:
            matches = self._scan_exact(value_type, value)
        self.session = ScanSession(value_type=value_type, matches=matches, fuzzy=fuzzy)
        return self.session

    def smart_scan(self, value: float) -> SmartScanResult | None:
        """Try multiple encodings; pick the smallest non-zero match set."""
        if not self.pm:
            raise RuntimeError("未附加进程")

        text = f"{value:.2f}".rstrip("0").rstrip(".")
        trials: list[tuple[ScanSession, str]] = []

        def add(session: ScanSession, label: str) -> None:
            if session.count > 0:
                trials.append((session, label))

        add(ScanSession(ValueType.FLOAT, self._scan_exact(ValueType.FLOAT, value)), "float 精确")
        add(ScanSession(ValueType.DOUBLE, self._scan_exact(ValueType.DOUBLE, value)), "double 精确")
        for eps in (0.05, 0.5, 2.0, 10.0):
            add(
                ScanSession(ValueType.FLOAT, self._scan_fuzzy_float(value, eps), fuzzy=eps),
                f"float ±{eps}",
            )
        for eps in (0.05, 0.5, 2.0):
            add(
                ScanSession(ValueType.DOUBLE, self._scan_fuzzy_double(value, eps), fuzzy=eps),
                f"double ±{eps}",
            )
        for iv in (int(value), int(round(value)), int(value * 100), int(round(value * 100))):
            add(ScanSession(ValueType.INT32, self._scan_exact(ValueType.INT32, iv)), f"int32 {iv}")

        str_addrs = self._scan_string(text)
        if str_addrs:
            add(ScanSession(ValueType.INT32, str_addrs[:5000]), f'字符串 "{text}"（只读，改数字可能无效）')

        if not trials:
            return None

        # 优先：结果少且非字符串
        trials.sort(key=lambda x: (x[0].count, "字符串" in x[1]))
        best, label = trials[0]
        self.session = best
        return SmartScanResult(session=best, label=label, count=best.count)

    def next_scan(self, value: float | int) -> ScanSession:
        if not self.pm or not self.session:
            raise RuntimeError("请先进行首次扫描")
        session = self.session
        kept: list[int] = []
        for addr in session.matches:
            try:
                actual = self._read_value(addr, session.value_type)
                if self._value_matches(actual, value, session):
                    kept.append(addr)
            except Exception:
                continue
        session.matches = kept
        return session

    def write_value(self, address: int, value_type: ValueType, value: float | int) -> None:
        if not self.pm:
            raise RuntimeError("未附加进程")
        data = self._pack(value_type, value)
        write_bytes(self.pm.process_handle, address, data, len(data))

    def read_matches(self, limit: int = 300) -> list[ScanMatch]:
        if not self.pm or not self.session:
            return []
        out: list[ScanMatch] = []
        for addr in self.session.matches[:limit]:
            try:
                val = self._read_value(addr, self.session.value_type)
                out.append(ScanMatch(address=addr, value_type=self.session.value_type, value=val))
            except Exception:
                continue
        return out
