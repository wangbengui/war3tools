# 小偷进化 · 内存修改器

KK 平台单人局内存扫描/修改工具（独立 GUI）。

## 环境

- Windows 10+
- Python 3.10+
- **建议以管理员身份运行**（否则无法附加 war3.exe）

## 安装与启动

> **必须先进入 modifier 目录**，或在资源管理器中双击 bat 启动。  
> 不要在 `C:\Windows\system32` 下直接运行 `python run.py`。

### 方式一：双击启动（推荐）

在资源管理器中打开：

```
E:\IDE-WorkSpace\war3tools\tools\
```

双击 **`启动小偷进化修改器.bat`**（建议右键 → **以管理员身份运行**）。

### 方式二：PowerShell 命令

```powershell
cd E:\IDE-WorkSpace\war3tools\tools\xiaotou-jinhua\modifier
pip install -r requirements.txt
python run.py
```

顺序必须是：**先 cd，再 pip，再 python run.py**。

## 使用流程

1. KK 平台进入「小偷进化」并 **单人开局**
2. 打开修改器 → **刷新** → 选择 `war3.exe` → **附加**
3. 看游戏内当前数值，在「快捷扫描」区确认/修改输入框中的值
4. 点对应项的 **首次扫**
5. 回游戏让该数值变化（花金币、等几秒涨金币等）
6. 把输入框改成 **变化后的新值** → 在「手动扫描」点 **再次扫描**（或重新首次扫）
7. 重复直到匹配数 ≤ 5
8. 选中地址 → 填写入值 → **锁定到下方**（下次自动加载）
9. **应用写入值到全部** 一键修改

## 截图锚点

首次扫描默认值来自 `tools/image.png`，详见 `src/scan_presets.py`。  
**数值随游戏进行会变**，扫描前务必改成游戏内当前值。

## 锁定配置

`config/saved_addresses.json` — 锁定后的地址持久保存。

## 目录

```
modifier/
├── run.py
├── start.bat
├── requirements.txt
├── config/              # 运行时生成
└── src/
    ├── app.py           # GUI
    ├── memory_scanner.py
    ├── process_finder.py
    └── scan_presets.py
```

## 已知限制（v0.1）

- 首版为通用 CE 式扫描，**未内置固定地址表**（需你在本机扫一次并锁定）
- RPG 自定义属性可能在 Lua 表/多层指针中，有时需多轮扫描或改 float 而非 int
- 联机使用有封号风险；建议单人

## 下一步（待你反馈扫描结果）

若某字段始终扫不出唯一地址，请告诉我：
- 字段名
- 首次/再次扫描时用的两个数值
- 最终匹配数量

我可针对性加指针链或 AOB 特征扫描。
