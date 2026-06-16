"""小偷进化 · 简化版内存修改器。"""

from __future__ import annotations

import ctypes
import os
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from .memory_scanner import MemoryAccess, ValueType
from .process_finder import find_war3_processes, pick_best_war3

FAST_MODE = os.environ.get("XTJH_FAST", "") == "1"
if FAST_MODE:
    from .memory_scanner_fast import MemoryAccessFast


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


class TrainerApp(tk.Tk):
    AUTO_ATTACH_MS = 2000

    def __init__(self) -> None:
        super().__init__()
        title = "小偷进化 · 修改器"
        if FAST_MODE:
            title += "（快速版）"
        self.title(title)
        self.geometry("680x580")
        self.minsize(600, 500)

        self.mem = MemoryAccessFast() if FAST_MODE else MemoryAccess()
        self._busy = False
        self._last_smart_label = ""

        self._build_ui()
        self._refresh_processes()
        self._try_auto_attach()
        self.after(self.AUTO_ATTACH_MS, self._auto_attach_tick)

        if not is_admin():
            self._set_status("未以管理员运行 — 扫描将始终为 0", ok=False)

    def _update_admin_banner(self) -> None:
        if is_admin():
            self.admin_label.config(text="✓ 管理员权限已就绪", fg="#008000")
        else:
            self.admin_label.config(
                text="✗ 未以管理员运行！请关闭本程序 → 右键 exe →「以管理员身份运行」（无需重启电脑）",
                fg="#cc0000",
            )

    def _diagnose(self) -> None:
        if self._busy:
            return
        if not self.mem.attached:
            self._try_auto_attach()

        def work():
            return self.mem.diagnose()

        def done(d):
            lines = [
                f"管理员权限: {'是' if d.is_admin else '否 ← 这会导致扫描失败'}",
                f"已附加进程: {'是 PID ' + str(d.pid) if d.attached else '否'}",
                f"可读内存区域: {d.readable_regions} 个（抽样读取成功 {d.readable_sample_ok} 个）",
                f"内存读取自检: {d.fuzzy_test_count} 条样本（>0 表示可读，若为 0 则无法扫描）",
            ]
            if d.attach_error:
                lines.append(f"问题: {d.attach_error}")
            msg = "\n".join(lines)
            ok = d.is_admin and d.attached and d.readable_sample_ok > 0 and d.fuzzy_test_count > 0
            if ok:
                messagebox.showinfo(
                    "诊断正常",
                    msg + "\n\n内存读取正常，可以扫描。\n攻击偷金请用「智能扫描」+ 买属性后再扫。",
                )
            else:
                messagebox.showwarning(
                    "诊断异常",
                    msg
                    + "\n\n【不需要重启电脑】\n"
                    "请确认：右键 exe → 以管理员身份运行 → UAC 点「是」→ 进入对局后再诊断",
                )

        self._run_async(work, done, status="诊断中…")

    def _build_ui(self) -> None:
        proc = ttk.LabelFrame(self, text="游戏进程")
        proc.pack(fill=tk.X, padx=10, pady=8)
        row = ttk.Frame(proc)
        row.pack(fill=tk.X, padx=8, pady=8)
        self.proc_var = tk.StringVar(value="（未检测到 War3.exe）")
        ttk.Label(row, textvariable=self.proc_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row, text="刷新", command=self._refresh_processes).pack(side=tk.RIGHT, padx=4)
        ttk.Button(row, text="附加", command=self._manual_attach).pack(side=tk.RIGHT, padx=4)
        ttk.Button(row, text="诊断", command=self._diagnose).pack(side=tk.RIGHT, padx=4)

        self.status_label = tk.Label(self, text="正在连接…", anchor="w", fg="#008000")
        self.status_label.pack(fill=tk.X, padx=12, pady=(0, 2))

        self.admin_label = tk.Label(
            self,
            text="",
            anchor="w",
            fg="#cc0000",
            font=("", 10, "bold"),
        )
        self.admin_label.pack(fill=tk.X, padx=12, pady=(0, 4))
        self._update_admin_banner()

        tip_text = (
            "攻击偷金用 float。界面显示 1810.65，内存里可能是 1810.64990234375，属正常。\n"
            "搜索时填界面上的数即可。每局新地址 → 先「新对局」→「智能扫描」→ 买属性后再扫。"
        )
        if FAST_MODE:
            tip_text += "\n快速版：多线程 + 优先堆内存，智能扫描更快（仅 float 路径）。"
        tip = tk.Label(
            self,
            text=tip_text,
            wraplength=640,
            justify=tk.LEFT,
            fg="#444",
        )
        tip.pack(fill=tk.X, padx=12, pady=(0, 6))

        scan = ttk.LabelFrame(self, text="手动扫描")
        scan.pack(fill=tk.X, padx=10, pady=4)
        sf = ttk.Frame(scan)
        sf.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(sf, text="类型").pack(side=tk.LEFT)
        self.type_var = tk.StringVar(value=ValueType.FLOAT.value)
        ttk.Combobox(
            sf,
            textvariable=self.type_var,
            values=[t.value for t in ValueType],
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=4)
        ttk.Label(sf, text="数值").pack(side=tk.LEFT, padx=(8, 0))
        self.value_var = tk.StringVar()
        ttk.Entry(sf, textvariable=self.value_var, width=14).pack(side=tk.LEFT, padx=4)
        self.fuzzy_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(sf, text="模糊±1", variable=self.fuzzy_var).pack(side=tk.LEFT, padx=4)
        ttk.Button(sf, text="首次扫描", command=self._first_scan).pack(side=tk.LEFT, padx=4)
        ttk.Button(sf, text="再次扫描", command=self._next_scan).pack(side=tk.LEFT, padx=4)
        smart_btn = "智能扫描⚡" if FAST_MODE else "智能扫描"
        ttk.Button(sf, text=smart_btn, command=self._smart_scan).pack(side=tk.LEFT, padx=4)
        ttk.Button(sf, text="新对局", command=self._new_game).pack(side=tk.LEFT, padx=4)

        sf2 = ttk.Frame(scan)
        sf2.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.count_var = tk.StringVar(value="匹配: 0")
        ttk.Label(sf2, textvariable=self.count_var).pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value="")
        ttk.Label(sf2, textvariable=self.mode_var, foreground="#0066aa").pack(side=tk.LEFT, padx=12)

        res = ttk.LabelFrame(self, text="扫描结果（双击修改）")
        res.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        cols = ("address", "type", "value")
        self.tree = ttk.Treeview(res, columns=cols, show="headings")
        self.tree.heading("address", text="地址")
        self.tree.heading("type", text="类型")
        self.tree.heading("value", text="当前值")
        self.tree.column("address", width=130)
        self.tree.column("type", width=70)
        self.tree.column("value", width=140)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.tree.bind("<Double-1>", self._on_double_click)

        wr = ttk.Frame(res)
        wr.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Label(wr, text="新数值").pack(side=tk.LEFT)
        self.write_var = tk.StringVar()
        ttk.Entry(wr, textvariable=self.write_var, width=16).pack(side=tk.LEFT, padx=4)
        ttk.Button(wr, text="写入选中", command=self._write_selected).pack(side=tk.LEFT, padx=4)

    def _set_status(self, text: str, ok: bool) -> None:
        self.status_label.config(text=text, fg="#008000" if ok else "#cc0000")

    def _refresh_processes(self) -> None:
        best = pick_best_war3()
        if best:
            self.proc_var.set(f"War3.exe  PID {best.pid}  {best.exe or ''}")
        else:
            self.proc_var.set("（未检测到 War3.exe）")

    def _try_auto_attach(self) -> None:
        best = pick_best_war3()
        if not best:
            self._set_status("未找到游戏 — 请先 KK 进入「小偷进化」", ok=False)
            return
        if self.mem.attached and self.mem.pid == best.pid:
            self._set_status(f"已附加 PID {best.pid}", ok=True)
            return
        try:
            self.mem.attach(best.pid)
            self._set_status(f"已自动附加 PID {best.pid}", ok=True)
        except Exception as exc:
            self.mem.detach()
            self._set_status(f"附加失败: {exc}", ok=False)

    def _auto_attach_tick(self) -> None:
        if not self._busy:
            if not self.mem.attached:
                self._try_auto_attach()
            elif not pick_best_war3():
                self.mem.detach()
                self._set_status("游戏已退出", ok=False)
        self.after(self.AUTO_ATTACH_MS, self._auto_attach_tick)

    def _manual_attach(self) -> None:
        self._refresh_processes()
        best = pick_best_war3()
        if not best:
            messagebox.showwarning("未找到游戏", "请先进入对局")
            return
        try:
            self.mem.attach(best.pid)
            self._set_status(f"已附加 PID {best.pid}", ok=True)
        except Exception as exc:
            messagebox.showerror("附加失败", f"{exc}\n\n请以管理员身份运行")

    def _ensure_attached(self) -> bool:
        if not is_admin():
            messagebox.showerror(
                "需要管理员权限",
                "当前未以管理员运行，无法读取游戏内存，扫描结果会始终为 0。\n\n"
                "请关闭程序 → 右键「小偷进化修改器.exe」→ 以管理员身份运行。\n\n"
                "不需要重启电脑。",
            )
            return False
        if not self.mem.attached:
            self._try_auto_attach()
        if not self.mem.attached:
            messagebox.showwarning("未附加", "未能附加 War3.exe，请先进入对局并以管理员运行。")
            return False
        return True

    def _run_async(self, work, done=None, status: str = "扫描中…") -> None:
        if self._busy:
            messagebox.showinfo("请稍候", "正在处理中…")
            return
        self._busy = True
        self._set_status(status, ok=True)

        def runner() -> None:
            err = None
            result = None
            try:
                result = work()
            except Exception as e:
                err = e

            def finish() -> None:
                self._async_done(err, done, result)

            self.after(0, finish)

        threading.Thread(target=runner, daemon=True).start()

    def _async_done(self, err, done, result=None) -> None:
        self._busy = False
        if err:
            messagebox.showerror("错误", str(err))
            self._set_status(f"错误: {err}", ok=False)
        elif done:
            try:
                done(result)
            except TypeError:
                done()
        if self.mem.attached:
            self._set_status(f"已附加 PID {self.mem.pid}", ok=True)

    def _parse_value(self, raw: str, vtype: ValueType) -> float | int:
        raw = raw.strip()
        if not raw:
            raise ValueError("请输入数值")
        if vtype == ValueType.INT32:
            return int(float(raw))
        return float(raw)

    def _new_game(self) -> None:
        self.mem.session = None
        self.tree.delete(*self.tree.get_children())
        self.count_var.set("匹配: 0")
        self.mode_var.set("")
        self.write_var.set("")

    def _first_scan(self) -> None:
        if not self._ensure_attached():
            return
        vtype = ValueType(self.type_var.get())
        val = self._parse_value(self.value_var.get(), vtype)
        fuzzy = 1.0 if (self.fuzzy_var.get() and vtype in (ValueType.FLOAT, ValueType.DOUBLE)) else 0.0

        def work():
            self.mem.first_scan(vtype, val, fuzzy=fuzzy)
            self._last_smart_label = f"{vtype.value}" + (f" ±{fuzzy}" if fuzzy else " 精确")

        def done():
            self._update_results()
            total = self.mem.session.count if self.mem.session else 0
            if total == 0:
                messagebox.showwarning("匹配 0 条", "未找到。请点「智能扫描」，或买属性后再次扫描。")

        self._run_async(work, done)

    def _smart_scan(self) -> None:
        if not self._ensure_attached():
            return
        raw = self.value_var.get().strip()
        if not raw:
            messagebox.showwarning("提示", "请先填写游戏内当前数值（如 1810.65）")
            return
        val = float(raw)

        def work():
            result = self.mem.smart_scan(val)
            if result is None:
                raise RuntimeError("所有方式均为 0 条匹配")
            self._last_smart_label = result.label

        def done():
            self._update_results()
            if self.mem.session and self.mem.session.count == 0:
                messagebox.showwarning(
                    "仍为 0",
                    "智能扫描也未找到。\n\n"
                    "可能原因：\n"
                    "1. 界面显示的是计算值，内存里没有单独的 1810.65\n"
                    "2. 请买一次「攻击偷金」相关属性让数值变化，再用「再次扫描」\n"
                    "3. 确认修改器状态栏为绿色「已附加」",
                )
            elif self.mem.session and self.mem.session.count > 500:
                messagebox.showinfo(
                    "结果较多",
                    f"找到 {self.mem.session.count} 条（{self._last_smart_label}）。\n"
                    "请回游戏让攻击偷金变化，再填新数值点「再次扫描」缩小范围。",
                )

        self._run_async(work, done)

    def _next_scan(self) -> None:
        if not self._ensure_attached() or not self.mem.session:
            messagebox.showwarning("提示", "请先首次扫描或智能扫描")
            return
        vtype = self.mem.session.value_type
        val = self._parse_value(self.value_var.get(), vtype)

        def work():
            self.mem.next_scan(val)

        self._run_async(work, self._update_results)

    def _update_results(self) -> None:
        self.tree.delete(*self.tree.get_children())
        if not self.mem.session:
            self.count_var.set("匹配: 0")
            self.mode_var.set("")
            return
        matches = self.mem.read_matches()
        for m in matches:
            self.tree.insert("", tk.END, values=(hex(m.address), m.value_type.value, m.value))
        total = self.mem.session.count
        shown = len(matches)
        extra = f"（显示 {shown} 条）" if shown < total else ""
        self.count_var.set(f"匹配: {total}{extra}")
        self.mode_var.set(self._last_smart_label)

    def _selected_row(self) -> tuple[int, str] | None:
        sel = self.tree.selection()
        if not sel:
            return None
        addr_s, _t, cur = self.tree.item(sel[0], "values")
        return int(addr_s, 16), str(cur)

    def _write_at(self, addr: int, new_raw: str, old_display: str) -> None:
        if not self.mem.session:
            return
        vtype = self.mem.session.value_type
        val = self._parse_value(new_raw, vtype)
        try:
            self.mem.write_value(addr, vtype, val)
            self._update_results()
            messagebox.showinfo("成功", f"{old_display} → {val}\n请切回游戏查看。")
        except Exception as exc:
            messagebox.showerror("失败", str(exc))

    def _write_selected(self) -> None:
        row = self._selected_row()
        if not row:
            messagebox.showwarning("提示", "请先选中一行")
            return
        addr, cur = row
        raw = self.write_var.get().strip()
        if not raw:
            messagebox.showwarning("提示", "请填写新数值")
            return
        self._write_at(addr, raw, cur)

    def _on_double_click(self, _evt) -> None:
        row = self._selected_row()
        if not row:
            return
        addr, cur = row
        new_val = simpledialog.askstring("修改", f"当前: {cur}\n新数值:", initialvalue=cur, parent=self)
        if new_val and new_val.strip():
            self.write_var.set(new_val.strip())
            self._write_at(addr, new_val.strip(), cur)


def main() -> None:
    TrainerApp().mainloop()


if __name__ == "__main__":
    main()
