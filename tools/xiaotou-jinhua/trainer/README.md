# 小偷进化 · 简化修改器

独立 GUI，自动附加 `War3.exe`，仅保留手动扫描/修改。

## 两个 exe 版本

| 文件 | 说明 |
|------|------|
| `小偷进化修改器.exe` | 标准版：智能扫描尝试 float/double/int/字符串 |
| `小偷进化修改器-快速版.exe` | 快速版：多线程 + 优先堆内存，智能扫描更快 |

打包：

```powershell
cd tools/xiaotou-jinhua/trainer
build.bat        # 仅标准版（会重建 dist）
build_fast.bat   # 仅快速版（不删除标准版 exe）
```

## 使用（exe）

1. 打开 **`dist/小偷进化修改器.exe`**（或 `tools/小偷进化修改器.exe`）
2. **右键 → 以管理员身份运行**（必须，否则无法附加游戏）
3. KK 平台进入「小偷进化」单人局
4. 程序会自动检测并附加；状态栏绿色 = 成功，红色 = 未找到或未附加

### 修改数值（以「攻击偷金」为例）

| 步骤 | 操作 |
|------|------|
| 1 | 类型选 **float**，数值填游戏内当前值（如 2290.65）→ **首次扫描** |
| 2 | 回游戏等数值变化 |
| 3 | 数值框改成新值 → **再次扫描** |
| 4 | 匹配剩 1 条 → **双击** 输入目标值（如 99999） |

整数资源（金币/木材）类型选 **int32**。

## 开发运行

```powershell
cd tools/xiaotou-jinhua/trainer
pip install pymem psutil
python run.py
```

## 打包 exe

```powershell
cd tools/xiaotou-jinhua/trainer
build.bat
```

输出：`trainer/dist/小偷进化修改器.exe`（已请求管理员权限 UAC）

## 与旧版 modifier 区别

| | 旧 modifier | 本 trainer |
|---|------------|------------|
| 位置 | `modifier/` | `trainer/` |
| 快捷扫描 | 有 | 无 |
| 地址锁定 | 有 | 无 |
| 自动附加 | 手动 | 自动 + 每 2 秒重试 |
| exe | 无 | 有 |
