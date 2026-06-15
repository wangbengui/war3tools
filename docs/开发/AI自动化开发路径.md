# AI 自动化开发路径

> 设计文档：[地图设计总览](../地图设计总览.md)  
> 结论：**无法 100% 零参与**，可压缩到一次性环境搭建 + 偶尔验收

---

## 为什么不能完全零参与？

Y3 地图含 `header.project`、地形/物编/UI 等，须编辑器或 **Y3 开发助手 MCP** 操作；KK 上传与开发者认证须真人完成。

---

## 官方 AI 方案

**Y3 开发助手**（VSCode 插件）+ MCP：

| 工具层 | 能力 |
|--------|------|
| y3editor | 物编、UI、地形、改 JSON |
| y3-helper | 启动游戏、执行 Lua、截图 |
| y3runtime | UI 自动化测试 |

- [AI 环境配置](https://163.com/y3/docs/guides/Editor/Y3AI)
- [Y3 开发助手](https://163.com/y3/docs/guides/FunctionManual/AIGC/Y3_AI)

---

## 推荐：Cursor + Windows + Y3 助手 MCP

### 一次性（约 1 小时）

1. 安装 KK + Y3 编辑器（**Windows**）
2. 新建 Y3 项目
3. VSCode + Y3 开发助手 + Git
4. 初始化 Y3 库，配置 MCP
5. 注册 [KK 开发者](https://create.kkdzpt.com/map)

### AI 后续可做

- 物编 / UI / Lua / 云脚本
- 启动游戏、截图、修 bug
- 维护 `war3tools` 文档与脚本，同步至 Y3 工程

### 你仍需偶尔

- 验收截图反馈
- 上传地图、填宣传物料

---

## 仓库定位

```
war3tools/docs/     → 设计文档（本仓库）
war3tools/script/   → Lua 源码（同步到 Y3 maps/EntryMap/script/）
war3tools/cloud_script/ → 云脚本
```

---

## 现实预期

| 目标 | 可行性 |
|------|--------|
| 不写代码 | ✅（AI + Y3 助手） |
| 不装软件 / 不建工程 | ❌ |
| 不注册开发者 | ❌ |

务实目标：环境搭建 1 小时 + 每周约 30 分钟验收 ≈ **95% 由 AI 完成**。
