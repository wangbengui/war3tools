"""Screenshot-derived scan anchors for 小偷进化 (2026-06-15).

Values taken from tools/image.png while in-game (wave 2).
Re-scan after values change in game (buy upgrades, gain gold, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass

from .memory_scanner import ValueType


@dataclass(frozen=True)
class ScanPreset:
    key: str
    label: str
    value_type: ValueType
    screenshot_value: float | int
    hint: str


# 截图时刻锚点 — 游戏内数值变化后需重新扫描
SCAN_PRESETS: tuple[ScanPreset, ...] = (
    ScanPreset(
        key="gold",
        label="金币",
        value_type=ValueType.INT32,
        screenshot_value=94700,
        hint="顶部资源栏 9.47万 → 94700（整数）",
    ),
    ScanPreset(
        key="lumber",
        label="木材",
        value_type=ValueType.INT32,
        screenshot_value=115,
        hint="顶部资源栏",
    ),
    ScanPreset(
        key="kills",
        label="杀敌数",
        value_type=ValueType.INT32,
        screenshot_value=16,
        hint="顶部头盔图标旁数字（若不对请手动改值再扫）",
    ),
    ScanPreset(
        key="steal_gold",
        label="攻击偷金",
        value_type=ValueType.FLOAT,
        screenshot_value=1410.65,
        hint="左侧属性面板",
    ),
    ScanPreset(
        key="gold_per_sec",
        label="每秒金币",
        value_type=ValueType.FLOAT,
        screenshot_value=248.0,
        hint="左侧属性面板",
    ),
    ScanPreset(
        key="kill_gold_per_sec",
        label="每秒杀敌金币",
        value_type=ValueType.FLOAT,
        screenshot_value=536.0,
        hint="左侧属性面板",
    ),
    ScanPreset(
        key="lumber_per_sec",
        label="每秒木材",
        value_type=ValueType.FLOAT,
        screenshot_value=5.0,
        hint="左侧属性面板",
    ),
    ScanPreset(
        key="hero_hp",
        label="英雄当前生命",
        value_type=ValueType.INT32,
        screenshot_value=1000,
        hint="左下角头像旁 1000/1000",
    ),
)

PRESET_BY_KEY = {p.key: p for p in SCAN_PRESETS}
