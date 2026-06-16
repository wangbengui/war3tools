"""Independent GUI memory trainer for 小偷进化 @ KK platform."""

from __future__ import annotations

import json
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from .memory_scanner import MemoryAccess, ValueType
from .process_finder import find_platform_processes, find_war3_processes, pick_best_war3
from .scan_presets import PRESET_BY_KEY, SCAN_PRESETS, ScanPreset

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "saved_addresses.json"


class TrainerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("小偷进化 · 内存修改器")
        self.geometry("920x680")
        self.minsize(800, 600)

        self.mem = MemoryAccess()
        self._busy = False
        self._saved: dict[str, dict] = self._load_saved()

        self._build_ui()
        self._refresh_process_list()
        self._render_saved()

    def _load_saved(self) -> dict[str, dict]:
        if not CONFIG_PATH.exists():
            return {}
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_saved(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(self._saved, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _build_ui(self) -> None:
        top = ttk.LabelFrame(self, text="进程")
        top.pack(fill=tk.X, padx=8, pady=6)

        self.proc_var = tk.StringVar()
        self.proc_combo = ttk.Combobox(top, textvariable=self.proc_var, width=70, state="readonly")
        self.proc_combo.pack(side=tk.LEFT, padx=6, pady=6)
        ttk.Button(top, text="刷新", command=self._refresh_process_list).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="附加", command=self._attach).pack(side=tk.LEFT, padx=4)
        self.status_var = tk.StringVar(value="未附加")
        ttk.Label(top, textvariable=self.status_var).pack(side=tk.LEFT, padx=8)

        hint = ttk.Label(
            self,
            text="建议：KK 平台单人开局 → 记下当前数值 → 首次扫描 → 游戏内花金币/等几秒 → 再次扫描 → 缩小到 1~5 个地址后锁定",
            wraplength=880,
        )
        hint.pack(fill=tk.X, padx=10, pady=(0, 4))

        preset_frame = ttk.LabelFrame(self, text="快捷扫描（来自截图锚点，数值变了请改右侧输入框）")
        preset_frame.pack(fill=tk.X, padx=8, pady=4)

        self.preset_vars: dict[str, tk.StringVar] = {}
        grid = ttk.Frame(preset_frame)
        grid.pack(fill=tk.X, padx=6, pady=6)
        for i, preset in enumerate(SCAN_PRESETS):
            row, col = divmod(i, 2)
            cell = ttk.Frame(grid)
            cell.grid(row=row, column=col, sticky="ew", padx=4, pady=2)
            ttk.Label(cell, text=preset.label, width=12).pack(side=tk.LEFT)
            var = tk.StringVar(value=str(preset.screenshot_value))
            self.preset_vars[preset.key] = var
            ttk.Entry(cell, textvariable=var, width=12).pack(side=tk.LEFT, padx=4)
            ttk.Button(
                cell,
                text="首次扫",
                command=lambda p=preset: self._scan_preset(p, first=True),
            ).pack(side=tk.LEFT, padx=2)
            ttk.Label(cell, text=preset.hint, foreground="#666").pack(side=tk.LEFT, padx=4)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        manual = ttk.LabelFrame(self, text="手动扫描")
        manual.pack(fill=tk.X, padx=8, pady=4)
        mf = ttk.Frame(manual)
        mf.pack(fill=tk.X, padx=6, pady=6)
        ttk.Label(mf, text="类型").pack(side=tk.LEFT)
        self.type_var = tk.StringVar(value=ValueType.INT32.value)
        ttk.Combobox(
            mf,
            textvariable=self.type_var,
            values=[t.value for t in ValueType],
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=4)
        ttk.Label(mf, text="数值").pack(side=tk.LEFT, padx=(8, 0))
        self.manual_value_var = tk.StringVar()
        ttk.Entry(mf, textvariable=self.manual_value_var, width=14).pack(side=tk.LEFT, padx=4)
        ttk.Button(mf, text="首次扫描", command=self._first_scan_manual).pack(side=tk.LEFT, padx=4)
        ttk.Button(mf, text="再次扫描", command=self._next_scan_manual).pack(side=tk.LEFT, padx=4)
        self.scan_count_var = tk.StringVar(value="匹配: 0")
        ttk.Label(mf, textvariable=self.scan_count_var).pack(side=tk.LEFT, padx=12)

        mid = ttk.Panedwindow(self, orient=tk.VERTICAL)
        mid.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        result_frame = ttk.LabelFrame(
            mid,
            text="扫描结果（单击选中 → 下方填「新数值」→ 点「写入选中」；或双击直接弹窗修改）",
        )
        mid.add(result_frame, weight=2)
        cols = ("address", "type", "value")
        self.result_tree = ttk.Treeview(result_frame, columns=cols, show="headings", height=10)
        for c, w in zip(cols, (140, 80, 120)):
            self.result_tree.heading(c, text={"address": "地址", "type": "类型", "value": "当前值"}[c])
            self.result_tree.column(c, width=w)
        self.result_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.result_tree.bind("<<TreeviewSelect>>", self._on_result_select)
        self.result_tree.bind("<Double-1>", self._on_result_double_click)

        rb = ttk.Frame(result_frame)
        rb.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Label(rb, text="新数值").pack(side=tk.LEFT)
        self.write_var = tk.StringVar()
        ttk.Entry(rb, textvariable=self.write_var, width=14).pack(side=tk.LEFT, padx=4)
        ttk.Button(rb, text="写入选中", command=self._write_selected).pack(side=tk.LEFT, padx=4)
        ttk.Label(rb, text="（改攻击偷金示例：填 99999 再点写入选中）", foreground="#0066aa").pack(
            side=tk.LEFT, padx=6
        )
        ttk.Label(rb, text="锁定名称").pack(side=tk.LEFT, padx=(12, 0))
        self.lock_name_var = tk.StringVar()
        ttk.Entry(rb, textvariable=self.lock_name_var, width=16).pack(side=tk.LEFT, padx=4)
        ttk.Button(rb, text="锁定到下方", command=self._lock_selected).pack(side=tk.LEFT, padx=4)

        saved_frame = ttk.LabelFrame(mid, text="已锁定地址（下次启动自动加载；可一键读/写）")
        mid.add(saved_frame, weight=1)
        scols = ("name", "address", "type", "value")
        self.saved_tree = ttk.Treeview(saved_frame, columns=scols, show="headings", height=6)
        for c, w in zip(scols, (120, 140, 80, 120)):
            self.saved_tree.heading(
                c,
                text={"name": "名称", "address": "地址", "type": "类型", "value": "当前值"}[c],
            )
            self.saved_tree.column(c, width=w)
        self.saved_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        sb = ttk.Frame(saved_frame)
        sb.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Button(sb, text="刷新当前值", command=self._refresh_saved_values).pack(side=tk.LEFT, padx=4)
        ttk.Button(sb, text="应用写入值到全部", command=self._apply_saved_writes).pack(side=tk.LEFT, padx=4)
        ttk.Button(sb, text="删除选中", command=self._delete_saved).pack(side=tk.LEFT, padx=4)

    def _process_choices(self) -> list[tuple[int, str]]:
        choices: list[tuple[int, str]] = []
        for p in find_war3_processes():
            choices.append((p.pid, f"war3 · PID {p.pid} · {p.exe or p.name}"))
        if not choices:
            for p in find_platform_processes():
                choices.append((p.pid, f"platform · PID {p.pid} · {p.exe or p.name} (需先进入游戏)"))
        return choices

    def _refresh_process_list(self) -> None:
        self._proc_map = dict(self._process_choices())
        labels = list(self._proc_map.values())
        self.proc_combo["values"] = labels
        best = pick_best_war3()
        if best:
            label = self._proc_map.get(best.pid)
            if label:
                self.proc_var.set(label)
        elif labels:
            self.proc_var.set(labels[0])

    def _selected_pid(self) -> int | None:
        label = self.proc_var.get()
        for pid, text in self._proc_map.items():
            if text == label:
                return pid
        return None

    def _attach(self) -> None:
        pid = self._selected_pid()
        if pid is None:
            messagebox.showwarning("提示", "未找到 war3.exe。请先 KK 平台进入「小偷进化」对局后再点刷新。")
            return
        try:
            self.mem.attach(pid)
            base = self.mem.module_base()
            extra = f" · Game.dll @ {hex(base)}" if base else ""
            self.status_var.set(f"已附加 PID {pid}{extra}")
        except Exception as exc:
            messagebox.showerror("附加失败", f"{exc}\n\n请以管理员身份运行本修改器。")

    def _run_async(self, fn, on_done=None) -> None:
        if self._busy:
            messagebox.showinfo("请稍候", "正在扫描中…")
            return
        self._busy = True
        self.status_var.set("扫描中…")

        def worker() -> None:
            err = None
            try:
                fn()
            except Exception as exc:
                err = exc
            self.after(0, lambda: self._async_done(err, on_done))

        threading.Thread(target=worker, daemon=True).start()

    def _async_done(self, err: Exception | None, on_done) -> None:
        self._busy = False
        if err:
            messagebox.showerror("错误", str(err))
            self.status_var.set("扫描失败")
        else:
            if on_done:
                on_done()
            if self.mem.attached:
                self.status_var.set(f"已附加 PID {self.mem.pid}")

    def _ensure_attached(self) -> bool:
        if not self.mem.attached:
            messagebox.showwarning("提示", "请先附加 war3.exe 进程")
            return False
        return True

    def _update_results(self) -> None:
        self.result_tree.delete(*self.result_tree.get_children())
        if not self.mem.session:
            self.scan_count_var.set("匹配: 0")
            return
        matches = self.mem.read_matches(limit=500)
        for m in matches:
            self.result_tree.insert(
                "",
                tk.END,
                values=(hex(m.address), m.value_type.value, m.value),
            )
        total = self.mem.session.count
        shown = len(matches)
        suffix = f"（显示前 {shown} 条）" if shown < total else ""
        self.scan_count_var.set(f"匹配: {total}{suffix}")

    def _scan_preset(self, preset: ScanPreset, first: bool) -> None:
        if not self._ensure_attached():
            return
        raw = self.preset_vars[preset.key].get().strip()
        if not raw:
            messagebox.showwarning("提示", "请输入扫描数值")
            return
        value: float | int
        if preset.value_type == ValueType.INT32:
            value = int(float(raw))
        else:
            value = float(raw)
        self.lock_name_var.set(preset.label)

        def work() -> None:
            if first or not self.mem.session:
                self.mem.first_scan(preset.value_type, value)
            else:
                self.mem.next_scan(value)

        self._run_async(work, self._update_results)

    def _first_scan_manual(self) -> None:
        if not self._ensure_attached():
            return
        vtype = ValueType(self.type_var.get())
        raw = self.manual_value_var.get().strip()
        if not raw:
            messagebox.showwarning("提示", "请输入数值")
            return
        value: float | int = int(float(raw)) if vtype == ValueType.INT32 else float(raw)

        def work() -> None:
            self.mem.first_scan(vtype, value)

        self._run_async(work, self._update_results)

    def _next_scan_manual(self) -> None:
        if not self._ensure_attached():
            return
        if not self.mem.session:
            messagebox.showwarning("提示", "请先首次扫描")
            return
        vtype = ValueType(self.type_var.get())
        raw = self.manual_value_var.get().strip()
        if not raw:
            messagebox.showwarning("提示", "请输入变化后的数值")
            return
        value: float | int = int(float(raw)) if vtype == ValueType.INT32 else float(raw)

        def work() -> None:
            self.mem.next_scan(value)

        self._run_async(work, self._update_results)

    def _selected_result_row(self) -> tuple[int, str, str] | None:
        sel = self.result_tree.selection()
        if not sel:
            return None
        addr_str, vtype, cur = self.result_tree.item(sel[0], "values")
        return int(addr_str, 16), vtype, str(cur)

    def _on_result_select(self, _event=None) -> None:
        row = self._selected_result_row()
        if row is None:
            return
        _addr, _vtype, cur = row
        if not self.write_var.get().strip():
            self.write_var.set(cur)

    def _write_selected(self, new_value: str | None = None) -> None:
        if not self._ensure_attached() or not self.mem.session:
            return
        row = self._selected_result_row()
        if row is None:
            messagebox.showwarning("提示", "请先单击选中扫描结果里的一行")
            return
        addr, _vtype_str, cur = row
        raw = (new_value if new_value is not None else self.write_var.get()).strip()
        if not raw:
            messagebox.showwarning(
                "提示",
                "请在扫描结果下方「新数值」输入框填写要改成的数字，\n例如把攻击偷金改成 99999，再点「写入选中」。",
            )
            return
        vtype = self.mem.session.value_type
        value: float | int = int(float(raw)) if vtype == ValueType.INT32 else float(raw)
        try:
            self.mem.write_value(addr, vtype, value)
            self._update_results()
            messagebox.showinfo("写入成功", f"已将内存值从 {cur} 改为 {value}\n请切回游戏查看是否生效。")
        except Exception as exc:
            messagebox.showerror("写入失败", str(exc))

    def _on_result_double_click(self, _event) -> None:
        row = self._selected_result_row()
        if row is None:
            return
        _addr, _vtype, cur = row
        new_val = simpledialog.askstring(
            "修改数值",
            f"当前值：{cur}\n\n请输入要改成的新数值：",
            initialvalue=cur,
            parent=self,
        )
        if new_val is None or not new_val.strip():
            return
        self.write_var.set(new_val.strip())
        self._write_selected(new_val.strip())

    def _lock_selected(self) -> None:
        if not self.mem.session:
            messagebox.showwarning("提示", "无扫描会话")
            return
        row = self._selected_result_row()
        if row is None:
            messagebox.showwarning("提示", "请先选中扫描结果")
            return
        addr, _vtype, _cur = row
        name = self.lock_name_var.get().strip() or f"addr_{hex(addr)}"
        self._saved[name] = {
            "address": addr,
            "value_type": self.mem.session.value_type.value,
            "write_value": self.write_var.get().strip(),
        }
        self._save_saved()
        self._render_saved()

    def _render_saved(self) -> None:
        self.saved_tree.delete(*self.saved_tree.get_children())
        for name, item in self._saved.items():
            self.saved_tree.insert(
                "",
                tk.END,
                iid=name,
                values=(name, hex(item["address"]), item["value_type"], "-"),
            )

    def _refresh_saved_values(self) -> None:
        if not self._ensure_attached():
            return
        for name, item in self._saved.items():
            try:
                val = self.mem.read_value(item["address"], ValueType(item["value_type"]))
                self.saved_tree.set(name, "value", val)
            except Exception:
                self.saved_tree.set(name, "value", "读取失败")

    def _apply_saved_writes(self) -> None:
        if not self._ensure_attached():
            return
        for name, item in self._saved.items():
            wv = item.get("write_value", "").strip()
            if not wv:
                continue
            vtype = ValueType(item["value_type"])
            value: float | int = int(float(wv)) if vtype == ValueType.INT32 else float(wv)
            try:
                self.mem.write_value(item["address"], vtype, value)
            except Exception as exc:
                messagebox.showerror("写入失败", f"{name}: {exc}")
                return
        self._refresh_saved_values()
        messagebox.showinfo("完成", "已写入全部配置了 write_value 的锁定项")

    def _delete_saved(self) -> None:
        sel = self.saved_tree.selection()
        if not sel:
            return
        for name in sel:
            self._saved.pop(name, None)
        self._save_saved()
        self._render_saved()


def main() -> None:
    app = TrainerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
