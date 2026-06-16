"""Process discovery for KK platform / Warcraft III."""

from __future__ import annotations

from dataclasses import dataclass

import psutil

# KK 平台常见启动链：Platform.exe -> war3.exe
WAR3_PROCESS_NAMES = (
    "war3.exe",
    "War3.exe",
    "Frozen Throne.exe",
)

PLATFORM_PROCESS_NAMES = (
    "Platform.exe",
    "platform.exe",
)


@dataclass(frozen=True)
class GameProcess:
    pid: int
    name: str
    exe: str | None


def _match(names: tuple[str, ...]) -> list[GameProcess]:
    targets = {n.lower() for n in names}
    found: list[GameProcess] = []
    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            name = proc.info["name"] or ""
            if name.lower() not in targets:
                continue
            found.append(
                GameProcess(
                    pid=proc.info["pid"],
                    name=name,
                    exe=proc.info.get("exe"),
                )
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return found


def find_war3_processes() -> list[GameProcess]:
    return _match(WAR3_PROCESS_NAMES)


def find_platform_processes() -> list[GameProcess]:
    return _match(PLATFORM_PROCESS_NAMES)


def pick_best_war3() -> GameProcess | None:
    processes = find_war3_processes()
    if not processes:
        return None
    if len(processes) == 1:
        return processes[0]
    # 多开时优先选内存占用最大的 war3 实例
    best = processes[0]
    best_rss = 0
    for p in processes:
        try:
            rss = psutil.Process(p.pid).memory_info().rss
            if rss > best_rss:
                best_rss = rss
                best = p
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return best
