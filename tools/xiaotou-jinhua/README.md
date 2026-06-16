# 小偷进化 · 辅助工具调研

KK 对战平台地图「小偷进化」的分析与辅助工具预研。

## 当前状态

**简化版 exe 已打包** — 见 [`trainer/`](trainer/)：

| 文件 | 说明 |
|------|------|
| `tools/小偷进化修改器.exe` | 标准版 |
| `tools/小偷进化修改器-快速版.exe` | 快速版（多线程智能扫描） |

旧版完整 GUI 仍保留在 [`modifier/`](modifier/)，不再维护。

## 目录结构

```
xiaotou-jinhua/
├── modifier/                 ← 【新】独立 GUI 修改器
├── docs/
│   ├── 01-地图分析报告.md
│   ├── 02-实施方案评估.md
│   ├── 03-待确认问题.md
│   └── 04-需求确认.md      ← 【新】已锁定需求
├── analysis/
├── extracted/
└── scripts/
```

## 快速结论

| 发现 | 说明 |
|------|------|
| 地图约 94 MB | 主体是模型/贴图/音频资源 |
| `war3map.j` 仅 116 字节 | 完整游戏逻辑不在地图文件内 |
| 物编数据极少 | 无物品表，单位/技能修改极少 |
| 平台云脚本地图 | 属性/进化/存档大概率在 KK 平台侧 |

## 阅读顺序

1. [03-待确认问题.md](docs/03-待确认问题.md) ← **请先回答**
2. [01-地图分析报告.md](docs/01-地图分析报告.md)
3. [02-实施方案评估.md](docs/02-实施方案评估.md)

## 重新运行分析

```powershell
python tools/xiaotou-jinhua/scripts/analyze_map.py
```

## 地图路径

默认分析路径（可在 `scripts/analyze_map.py` 中修改）：

```
D:\GAME\Warcraft III Frozen Throne\Maps\dz\rpg\小偷进化修改版\781DD85B990F8829A6E9758F58EFCA5B.w3x
```
