"""Accelerated memory scanner: parallel + heap-first + early exit."""

from __future__ import annotations

import struct
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from pymem.memory import read_bytes

from .memory_scanner import (
    MemoryAccess,
    ScanSession,
    SmartScanResult,
    ValueType,
)

# 优先扫堆内存（RPG 动态数值多在 READWRITE 区）
_HEAP_PROT = 0x04
_MAX_WORKERS = 8
_CHUNKSIZE = 2 * 1024 * 1024


class MemoryAccessFast(MemoryAccess):
    """Fast smart scan; standard first_scan/next_scan also use cached parallel paths."""

    def __init__(self) -> None:
        super().__init__()
        self._regions_all: list[tuple[int, int, int]] | None = None
        self._regions_heap: list[tuple[int, int]] | None = None

    def attach(self, pid: int) -> None:
        super().attach(pid)
        self._regions_all = None
        self._regions_heap = None

    def detach(self) -> None:
        super().detach()
        self._regions_all = None
        self._regions_heap = None

    def _build_region_cache(self) -> None:
        if self._regions_all is not None or not self.pm:
            return
        from pymem.memory import virtual_query

        handle = self.pm.process_handle
        all_r: list[tuple[int, int, int]] = []
        heap: list[tuple[int, int]] = []
        addr = 0
        while addr < 0x7FFFFFFF0000:
            try:
                mbi = virtual_query(handle, addr)
            except Exception:
                break
            base, size = mbi.BaseAddress, mbi.RegionSize
            prot = mbi.Protect & 0xFF
            if (
                mbi.State == 0x1000
                and size > 0
                and prot in self.READABLE_BASE
                and prot != self.PAGE_NOACCESS
            ):
                all_r.append((base, size, prot))
                if prot == _HEAP_PROT:
                    heap.append((base, size))
            nxt = base + size
            if nxt <= addr:
                break
            addr = nxt
        self._regions_all = all_r
        self._regions_heap = heap if heap else [(b, s) for b, s, _ in all_r]

    def _regions_for_scan(self, heap_only: bool) -> list[tuple[int, int]]:
        self._build_region_cache()
        if heap_only and self._regions_heap:
            return self._regions_heap
        if self._regions_all:
            return [(b, s) for b, s, _ in self._regions_all]
        return list(self.iter_readable_regions())

    def _parallel_regions(
        self,
        regions: list[tuple[int, int]],
        scan_chunk: Callable[[int, int, bytes, int], list[int]],
    ) -> list[int]:
        if not self.pm:
            return []
        handle = self.pm.process_handle
        matches: list[int] = []

        def work_region(base: int, region_size: int) -> list[int]:
            local: list[int] = []
            offset = 0
            while offset < region_size:
                read_size = min(_CHUNKSIZE, region_size - offset)
                try:
                    chunk = read_bytes(handle, base + offset, read_size)
                except Exception:
                    offset += read_size
                    continue
                local.extend(scan_chunk(base, offset, chunk, read_size))
                offset += read_size
            return local

        if len(regions) <= 2:
            for base, size in regions:
                matches.extend(work_region(base, size))
            return matches

        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            futures = [pool.submit(work_region, base, size) for base, size in regions]
            for fut in as_completed(futures):
                try:
                    matches.extend(fut.result())
                except Exception:
                    pass
        return matches

    def _scan_exact_parallel(
        self,
        value_type: ValueType,
        value: float | int,
        heap_only: bool,
    ) -> list[int]:
        needle = self._pack(value_type, value)
        step = self._size(value_type)
        regions = self._regions_for_scan(heap_only)

        def scan_chunk(base: int, offset: int, chunk: bytes, _read_size: int) -> list[int]:
            out: list[int] = []
            start = 0
            while True:
                idx = chunk.find(needle, start)
                if idx < 0:
                    break
                out.append(base + offset + idx)
                start = idx + step
            return out

        return self._parallel_regions(regions, scan_chunk)

    def _scan_fuzzy_float_parallel(
        self,
        value: float,
        epsilon: float,
        heap_only: bool,
    ) -> list[int]:
        lo, hi = float(value) - epsilon, float(value) + epsilon
        regions = self._regions_for_scan(heap_only)

        def scan_chunk(base: int, offset: int, chunk: bytes, _read_size: int) -> list[int]:
            out: list[int] = []
            end = len(chunk) - 3
            pos = 0
            while pos < end:
                v = struct.unpack_from("<f", chunk, pos)[0]
                if lo <= v <= hi:
                    out.append(base + offset + pos)
                pos += 4
            return out

        return self._parallel_regions(regions, scan_chunk)

    def first_scan(
        self,
        value_type: ValueType,
        value: float | int,
        fuzzy: float = 0.0,
    ) -> ScanSession:
        if not self.pm:
            raise RuntimeError("未附加进程")
        heap_first = True
        if fuzzy > 0 and value_type == ValueType.FLOAT:
            matches = self._scan_fuzzy_float_parallel(float(value), fuzzy, heap_first)
            if not matches:
                matches = self._scan_fuzzy_float_parallel(float(value), fuzzy, False)
        elif fuzzy > 0 and value_type == ValueType.DOUBLE:
            matches = super().first_scan(value_type, value, fuzzy).matches
        else:
            matches = self._scan_exact_parallel(value_type, value, heap_first)
            if not matches:
                matches = self._scan_exact_parallel(value_type, value, False)
        self.session = ScanSession(value_type=value_type, matches=matches, fuzzy=fuzzy)
        return self.session

    def smart_scan(self, value: float) -> SmartScanResult | None:
        """Heap-first float, parallel; stop at first hit. Fallback to full memory."""
        if not self.pm:
            raise RuntimeError("未附加进程")

        trials: list[tuple[ScanSession, str]] = []

        def try_add(matches: list[int], vtype: ValueType, label: str, fuzzy: float = 0.0) -> bool:
            if not matches:
                return False
            trials.append((ScanSession(vtype, matches, fuzzy=fuzzy), label))
            return True

        # 1) heap float 精确 — 攻击偷金已验证为 float
        m = self._scan_exact_parallel(ValueType.FLOAT, value, heap_only=True)
        if try_add(m, ValueType.FLOAT, "float 精确 [快速·堆]"):
            if len(m) <= 8000:
                best, label = min(trials, key=lambda x: x[0].count)
                self.session = best
                return SmartScanResult(session=best, label=label, count=best.count)

        # 2) heap float ±1
        m = self._scan_fuzzy_float_parallel(value, 1.0, heap_only=True)
        try_add(m, ValueType.FLOAT, "float ±1 [快速·堆]", fuzzy=1.0)

        # 3) 全内存 float 精确（仍并行，比标准版少试 double/int/string）
        if not trials or trials[0][0].count == 0:
            m = self._scan_exact_parallel(ValueType.FLOAT, value, heap_only=False)
            try_add(m, ValueType.FLOAT, "float 精确 [快速·全内存]")

        if not trials:
            return None

        trials.sort(key=lambda x: x[0].count)
        best, label = trials[0]
        self.session = best
        return SmartScanResult(session=best, label=label, count=best.count)
