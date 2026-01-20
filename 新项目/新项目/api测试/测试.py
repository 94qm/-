"""工具：只保留“打开网站”界面"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog
from tkinter import ttk
import webbrowser
import os
import json
import re
from pathlib import Path

from deepseek import DEFAULT_URLS, open_in_edge


class SitesApp(tk.Tk):
    def __init__(self, urls=None):
        super().__init__()
        self.title('打开网页工具')
        self._apply_geometry('800x600')
        self.minsize(520, 360)
        # 配置目录（使用 APPDATA），用于保存 urls.json
        appdata = os.environ.get('APPDATA') or str(Path.home())
        self._config_dir = Path(appdata) / '打开网页工具'
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._urls_file = self._config_dir / 'urls.json'
        # 默认元信息（存储默认分组名），可被用户修改并持久化
        self.meta = {'default_group_names': ['分组1', '分组2']}
        # 加载已保存的分组（优先），兼容旧版保存为列表的情况；返回 (groups, meta)
        if urls is not None:
            if isinstance(urls, dict):
                self.groups = dict(urls)
            else:
                names = self.meta.get('default_group_names', ['分组1', '分组2'])
                self.groups = {names[0]: list(urls)}
                for name in names[1:]:
                    self.groups.setdefault(name, [])
        else:
            loaded = self._load_groups()
            if loaded:
                self.groups, meta = loaded
                if isinstance(meta, dict):
                    # 使用保存的 meta 覆盖默认 meta
                    self.meta.update(meta)
            else:
                names = self.meta.get('default_group_names', ['分组1', '分组2'])
                # 第一个分组填充 DEFAULT_URLS，其余为空
                self.groups = {names[0]: list(DEFAULT_URLS)}
                for name in names[1:]:
                    self.groups[name] = []
        # 当前分组名字（选中的分组）
        self.current_group = next(iter(self.groups)) if self.groups else self.meta.get('default_group_names', ['分组1'])[0]
        self._build()
        # 在关闭时保存
        self.protocol('WM_DELETE_WINDOW', self.on_close)

    def _apply_geometry(self, geom: str):
        """安全设置窗口大小：自动把 '*' 替换为 'x'，并在格式不正确时回退到默认尺寸。"""
        if not geom:
            return
        g = str(geom).replace('*', 'x').strip()
        # 简单校验：形如 800x600 或 800x600+10+10 等
        if not re.match(r'^\d+x\d+(?:[+-]\d+[+-]\d+)?$', g):
            m = re.search(r'(\d+)[^\d]+(\d+)', g)
            if m:
                g = f"{m.group(1)}x{m.group(2)}"
            else:
                g = '640x420'
        try:
            # 如果没有包含偏移（+x+y），则尝试居中显示
            if re.match(r'^\d+x\d+$', g):
                try:
                    w, h = (int(x) for x in g.split('x'))
                    sw = self.winfo_screenwidth()
                    sh = self.winfo_screenheight()
                    # 限制窗口尺寸不超过屏幕
                    w = min(w, sw)
                    h = min(h, sh)
                    x = max(0, (sw - w) // 2)
                    y = max(0, (sh - h) // 2)
                    g = f"{w}x{h}+{x}+{y}"
                except Exception:
                    pass
            self.geometry(g)
        except Exception:
            try:
                self.geometry('640x420')
            except Exception:
                pass

    def _build(self):
        frm = tk.Frame(self, padx=12, pady=12)
        frm.pack(fill=tk.BOTH, expand=True)
        # 统一样式：Treeview 行高、字体、按钮样式
        try:
            style = ttk.Style(self)
            style.configure('Treeview', rowheight=24, font=('Segoe UI', 10))
            style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))
            style.configure('TButton', font=('Segoe UI', 10))
        except Exception:
            pass

        # 分组选择与管理（使用 grid 对齐）
        grp_frame = tk.Frame(frm)
        grp_frame.pack(fill=tk.X, pady=(0,8))
        tk.Label(grp_frame, text='分组:').grid(row=0, column=0, padx=(0,8), pady=4, sticky='w')
        self.group_var = tk.StringVar(value=self.current_group)
        self.group_cb = ttk.Combobox(grp_frame, textvariable=self.group_var, values=list(self.groups.keys()), state='readonly', width=28)
        self.group_cb.grid(row=0, column=1, padx=(0,8), sticky='w')
        self.group_cb.bind('<<ComboboxSelected>>', lambda e: self.switch_group(self.group_var.get()))
        tk.Button(grp_frame, text='添加分组', command=self.add_group, width=10).grid(row=0, column=2, padx=4)
        tk.Button(grp_frame, text='删除分组', command=self.remove_group, width=10).grid(row=0, column=3, padx=4)
        tk.Button(grp_frame, text='重命名分组', command=self.rename_group, width=12).grid(row=0, column=4, padx=4)
        tk.Button(grp_frame, text='设置默认分组名', command=self.set_default_group_names, width=14).grid(row=0, column=5, padx=6)

        # 网址列表（使用 Treeview，带滚动条，支持右键菜单与双击打开）
        tk.Label(frm, text='网址列表（可编辑）：').pack(anchor='w')
        list_frame = tk.Frame(frm)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(6,10))
        self.tree = ttk.Treeview(list_frame, columns=('url',), show='headings', selectmode='extended', height=14)
        self.tree.heading('url', text='网址')
        self.tree.column('url', anchor='w')
        vsb = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        # 交替行颜色
        try:
            self.tree.tag_configure('odd', background='#fbfbfb')
            self.tree.tag_configure('even', background='#ffffff')
        except Exception:
            pass
        # 双击打开
        self.tree.bind('<Double-1>', lambda e: self.open_selected_edge())
        # 右键菜单
        self._create_tree_context_menu()
        # 拖拽支持：目标高亮和事件绑定
        try:
            self.tree.tag_configure('target', background='#cce6ff')
        except Exception:
            pass
        self._dragging_iid = None
        self._last_target = None
        self.tree.bind('<ButtonPress-1>', self._on_tree_button_press)
        self.tree.bind('<B1-Motion>', self._on_tree_motion)
        self.tree.bind('<ButtonRelease-1>', self._on_tree_button_release)
        # 填充当前分组的网址
        self._refresh_listbox()

        # 打开相关按钮（放在一行）
        btn_frame = tk.Frame(frm)
        btn_frame.pack(fill=tk.X, pady=(6,6))
        tk.Button(btn_frame, text='用 Edge 打开全部', command=self.open_all_edge, width=18).pack(side=tk.LEFT, padx=6, pady=2)
        tk.Button(btn_frame, text='在默认浏览器打开全部', command=self.open_all_default, width=24).pack(side=tk.LEFT, padx=6, pady=2)
        tk.Button(btn_frame, text='打开选中（Edge）', command=self.open_selected_edge, width=18).pack(side=tk.LEFT, padx=6, pady=2)
        ttk.Button(btn_frame, text='编辑默认网址', command=self.edit_default_urls, width=14).pack(side=tk.LEFT, padx=6, pady=2)

        # 编辑行（URL 输入 + 操作）——让输入框可拉伸，并添加编辑/移动按钮
        edit_frame = tk.Frame(frm)
        edit_frame.pack(fill=tk.X, pady=(8,0))
        tk.Label(edit_frame, text='新网址:').pack(side=tk.LEFT)
        self.new_url_var = tk.StringVar()
        tk.Entry(edit_frame, textvariable=self.new_url_var).pack(side=tk.LEFT, padx=8, fill=tk.X, expand=True)
        tk.Button(edit_frame, text='添加', command=self.add_url, width=8).pack(side=tk.LEFT, padx=6)
        tk.Button(edit_frame, text='编辑选中', command=self.edit_selected, width=10).pack(side=tk.LEFT, padx=6)
        tk.Button(edit_frame, text='上移', command=self.move_up, width=8).pack(side=tk.LEFT, padx=6)
        tk.Button(edit_frame, text='下移', command=self.move_down, width=8).pack(side=tk.LEFT, padx=6)
        tk.Button(edit_frame, text='删除选中', command=self.remove_selected, width=12).pack(side=tk.LEFT, padx=6)
        # 将恢复默认右对齐并使用 ttk 风格，使界面更协调
        ttk.Button(edit_frame, text='恢复默认', command=self.restore_defaults, width=12).pack(side=tk.RIGHT, padx=8)

        # 状态栏
        self.status_var = tk.StringVar(value='就绪')
        status_lbl = tk.Label(self, textvariable=self.status_var, anchor='w', relief=tk.SUNKEN)
        status_lbl.pack(fill=tk.X, side=tk.BOTTOM, ipady=2)

    def get_all_urls(self):
        """返回当前 Treeview 中按顺序的 URL 列表"""
        return [self.tree.item(i, 'values')[0] for i in self.tree.get_children()]

    def _load_groups(self):
        """返回 (groups_dict, meta_dict) 或 None。兼容老格式(list) 和新格式(dict with optional '_meta')."""
        try:
            if self._urls_file.exists():
                with open(self._urls_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 如果是老格式：列表 -> 放入第一个默认分组，其他为空
                if isinstance(data, list):
                    names = self.meta.get('default_group_names', ['分组1', '分组2'])
                    groups = {names[0]: data}
                    for name in names[1:]:
                        groups[name] = []
                    return groups, self.meta
                if isinstance(data, dict):
                    meta = data.get('_meta', {}) if isinstance(data.get('_meta', {}), dict) else {}
                    groups = {k: list(v) for k, v in data.items() if k != '_meta'}
                    return groups, meta
        except Exception:
            pass
        return None

    def _save_groups(self):
        try:
            # 确保将当前 listbox 内容同步到当前分组
            self.groups[self.current_group] = self.get_all_urls()
            out = dict(self.groups)
            # 将 meta 单独存储到 '_meta' 键
            out['_meta'] = self.meta
            with open(self._urls_file, 'w', encoding='utf-8') as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
            self.status_var.set(f'已保存分组 ({self.current_group})')
            # 更新组合框列表（如果分组名变更）
            if hasattr(self, 'group_cb'):
                self.group_cb['values'] = list(self.groups.keys())
                self.group_var.set(self.current_group)
        except Exception as e:
            self.status_var.set('保存失败')

    def _save_meta(self):
        """只保存 meta 到 urls.json 的 _meta 键，保持 groups 不变（保障编辑默认网址只改 meta 时也能持久化）。"""
        try:
            data = {}
            if self._urls_file.exists():
                try:
                    with open(self._urls_file, 'r', encoding='utf-8') as f:
                        data = json.load(f) or {}
                except Exception:
                    data = {}
            # 保留现有分组数据（如果存在），更新 _meta
            if not isinstance(data, dict):
                data = {}
            data['_meta'] = self.meta
            with open(self._urls_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.status_var.set('已保存默认网址 (meta)')
        except Exception:
            self.status_var.set('保存 meta 失败')

    def on_close(self):
        # 保存并退出
        try:
            self._save_groups()
        finally:
            self.destroy()

    def open_all_edge(self):
        urls = self.get_all_urls()
        if not urls:
            messagebox.showwarning('空列表', '没有网址可打开')
            return
        self.status_var.set('正在用 Edge 打开...')
        ok = open_in_edge(urls, new_window=True)
        if ok:
            self.status_var.set('已使用 Edge 打开')
        else:
            self.status_var.set('未找到 Edge，已使用默认浏览器打开')

    def open_all_default(self):
        urls = self.get_all_urls()
        if not urls:
            messagebox.showwarning('空列表', '没有网址可打开')
            return
        self.status_var.set('正在使用默认浏览器打开...')
        for u in urls:
            webbrowser.open_new_tab(u)
        self.status_var.set('已在默认浏览器中打开全部网址')

    def open_selected_edge(self):
        sel = list(self.tree.selection())
        if not sel:
            messagebox.showwarning('未选择', '请先选择要打开的一个或多个网址')
            return
        urls = [self.tree.item(i, 'values')[0] for i in sel]
        self.status_var.set('正在打开选中网址...')
        ok = open_in_edge(urls, new_window=False)
        if ok:
            self.status_var.set('已在 Edge 中打开选中网址')
        else:
            self.status_var.set('未找到 Edge，已使用默认浏览器打开选中网址')

    def add_url(self):
        u = self.new_url_var.get().strip()
        if not u:
            return
        # 插入到 Treeview
        idx = len(self.tree.get_children())
        tag = 'even' if idx % 2 == 0 else 'odd'
        self.tree.insert('', 'end', values=(u,), tags=(tag,))
        self.new_url_var.set('')
        # 自动保存
        self._save_groups()

    def remove_selected(self):
        sel = list(self.tree.selection())
        if not sel:
            return
        for iid in sel:
            self.tree.delete(iid)
        # 重新应用行色并保存
        self._apply_row_tags()
        self._save_groups()

    def restore_defaults(self):
        """恢复为 DEFAULT_URLS 列表（恢复为 meta 中记录的默认分组）。"""
        if messagebox.askyesno('确认', '是否恢复为默认网址列表？'):
            self._apply_defaults_no_confirm()

    def _apply_defaults_no_confirm(self):
        """不弹窗地将 meta['default_urls'] 应用为第一个分组并切换到该组。"""
        names = self.meta.get('default_group_names', ['分组1', '分组2'])
        defaults = self.meta.get('default_urls', DEFAULT_URLS)
        self.groups = {names[0]: list(defaults)}
        for name in names[1:]:
            self.groups[name] = []
        self.current_group = names[0]
        # 更新组合框
        if hasattr(self, 'group_cb'):
            self.group_cb['values'] = list(self.groups.keys())
            self.group_var.set(self.current_group)
        self._refresh_listbox()
        self.status_var.set('已应用默认网址')
        # 自动保存
        self._save_groups()

    def add_group(self):
        name = simpledialog.askstring('添加分组', '输入分组名称：', parent=self)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        if name in self.groups:
            messagebox.showwarning('重复', '该分组已存在')
            return
        self.groups[name] = []
        self.current_group = name
        self.group_cb['values'] = list(self.groups.keys())
        self.group_var.set(name)
        self._refresh_listbox()
        self._save_groups()

    def remove_group(self):
        if len(self.groups) <= 1:
            messagebox.showwarning('提示', '至少保持一个分组')
            return
        if messagebox.askyesno('确认', f'是否删除分组 "{self.current_group}"？'):
            del self.groups[self.current_group]
            self.current_group = next(iter(self.groups))
            self.group_cb['values'] = list(self.groups.keys())
            self.group_var.set(self.current_group)
            self._refresh_listbox()
            self._save_groups()

    def rename_group(self):
        name = simpledialog.askstring('重命名分组', '输入新分组名称：', initialvalue=self.current_group, parent=self)
        if not name:
            return
        name = name.strip()
        if not name or name == self.current_group:
            return
        if name in self.groups:
            messagebox.showwarning('重复', '该分组已存在')
            return
        self.groups[name] = self.groups.pop(self.current_group)
        self.current_group = name
        self.group_cb['values'] = list(self.groups.keys())
        self.group_var.set(name)
        self._save_groups()

    def switch_group(self, name):
        # 在切换前保存当前 listbox 到 groups
        self.groups[self.current_group] = self.get_all_urls()
        self.current_group = name
        self._refresh_listbox()
        self.status_var.set(f'切换到分组：{name}')

    def set_default_group_names(self):
        """通过逗号分隔的输入修改并保存默认分组名称（会持久化到 urls.json 的 _meta）。"""
        current = self.meta.get('default_group_names', ['分组1', '分组2'])
        initial = ','.join(current)
        s = simpledialog.askstring('设置默认分组名', '以逗号分隔输入默认分组名（例如：工作,个人）', initialvalue=initial, parent=self)
        if s is None:
            return
        names = [n.strip() for n in s.split(',') if n.strip()]
        if not names:
            messagebox.showwarning('输入错误', '请输入至少一个分组名称')
            return
        self.meta['default_group_names'] = names
        # 持久化 meta（保持现有 groups 不变）
        self._save_groups()
        self.status_var.set('已更新默认分组名')

    def edit_default_urls(self):
        """弹出对话以编辑默认网址列表，每行一个网址，保存到 meta['default_urls']。"""
        current = self.meta.get('default_urls', DEFAULT_URLS)
        dlg = tk.Toplevel(self)
        dlg.title('编辑默认网址')
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(False, False)
        # 设定大小并居中（相对于父窗口，向内偏移 20px），避免出现在屏幕左上角
        w, h = 640, 360
        self.update_idletasks()
        pw = self.winfo_width()
        ph = self.winfo_height()
        px = self.winfo_rootx()
        py = self.winfo_rooty()
        if pw <= 1 or ph <= 1:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = max(20, (sw - w) // 2)
            y = max(20, (sh - h) // 2)
        else:
            x = px + max(20, (pw - w) // 2)
            y = py + max(20, (ph - h) // 2)
        dlg.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(dlg, text='每行一个网址:').pack(anchor='w', padx=8, pady=(8,0))

        # 按钮回调放在上方以便顶部按钮可直接引用
        def on_ok(event=None):
            vals = [line.strip() for line in txt.get('1.0', 'end').splitlines() if line.strip()]
            if not vals and not messagebox.askyesno('确认', '是否将默认网址列表设置为空？'):
                return
            self.meta['default_urls'] = vals
            # 持久化 meta，并同时保存分组数据以确保一致性
            self._save_meta()
            self._save_groups()
            self.status_var.set('已更新默认网址')
            messagebox.showinfo('已保存', '默认网址已保存')
            # 是否立即应用到第一个分组
            if messagebox.askyesno('立即应用', '是否立即将默认网址应用为第一个分组并切换到该组？'):
                self._apply_defaults_no_confirm()
            dlg.destroy()

        def on_cancel(event=None):
            dlg.destroy()

        # 顶部明显的保存按钮，并绑定快捷键
        top_btn_fr = tk.Frame(dlg)
        top_btn_fr.pack(fill=tk.X, padx=8, pady=(6,0))
        tk.Button(top_btn_fr, text='保存 (Ctrl+Enter)', command=on_ok, width=14).pack(side=tk.RIGHT)

        txt = tk.Text(dlg, wrap='none')
        txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        txt.insert('1.0', '\n'.join(current))

        # 保证对话框不会太小导致按钮不可见
        dlg.minsize(420, 240)
        # 快捷键：Ctrl+Enter 确认，Esc 取消
        dlg.bind('<Control-Return>', on_ok)
        dlg.bind('<Escape>', on_cancel)

        btn_fr = tk.Frame(dlg)
        btn_fr.pack(fill=tk.X, pady=(0,8))
        ttk.Button(btn_fr, text='确定', command=on_ok, width=10).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btn_fr, text='取消', command=on_cancel, width=10).pack(side=tk.RIGHT, padx=6)

    def _apply_row_tags(self):
        # 重新计算并应用行的 odd/even 标签
        for idx, iid in enumerate(self.tree.get_children()):
            tag = 'even' if idx % 2 == 0 else 'odd'
            try:
                self.tree.item(iid, tags=(tag,))
            except Exception:
                pass

    def _create_drag_ghost(self, text, x, y):
        """创建一个半透明的浮动窗口作为拖拽虚影，文字为 text，位置基于 x,y（屏幕坐标）。"""
        try:
            g = tk.Toplevel(self)
            g.overrideredirect(True)
            # 保持在顶层并尽量半透明（若平台支持）
            try:
                g.attributes('-topmost', True)
                g.attributes('-alpha', 0.92)
            except Exception:
                pass
            lbl = tk.Label(g, text=text, bg='#ffffe0', bd=1, relief='solid', padx=6, pady=3, font=('Segoe UI', 9))
            lbl.pack()
            # 轻微偏移以避免覆盖鼠标指针
            g.geometry(f'+{x+12}+{y+12}')
            return g
        except Exception:
            return None

    # --------- 拖拽相关处理 ---------
    def _on_tree_button_press(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            self._dragging_iid = None
            return
        # 如果用户点中某项，准备开始拖动（并确保选中）
        self._dragging_iid = iid
        if iid not in self.tree.selection():
            self.tree.selection_set(iid)
        # 记录初始位置并初始化虚影相关状态（真正创建在足够移动后）
        self._drag_start = (event.x_root, event.y_root)
        self._drag_ghost = None
        # 清除上次高亮
        if self._last_target:
            try:
                tags = tuple(t for t in self.tree.item(self._last_target, 'tags') if t != 'target')
                self.tree.item(self._last_target, tags=tags)
            except Exception:
                pass
            self._last_target = None

    def _on_tree_motion(self, event):
        if not getattr(self, '_dragging_iid', None):
            return
        # 如果还没有创建虚影，只有在鼠标移动超过阈值时才创建（避免单击时出现）
        try:
            sx, sy = getattr(self, '_drag_start', (event.x_root, event.y_root))
            if getattr(self, '_drag_ghost', None) is None:
                if abs(event.x_root - sx) > 5 or abs(event.y_root - sy) > 5:
                    # 决定显示内容：多选时显示计数，单选显示网址文本
                    sel = list(self.tree.selection())
                    if len(sel) > 1:
                        text = f'拖拽 {len(sel)} 项'
                    else:
                        text = self.tree.item(self._dragging_iid, 'values')[0]
                    self._drag_ghost = self._create_drag_ghost(text, event.x_root, event.y_root)
            else:
                # 更新虚影位置
                try:
                    self._drag_ghost.geometry(f'+{event.x_root+12}+{event.y_root+12}')
                except Exception:
                    pass
        except Exception:
            pass
        # 查找当前鼠标所在的行并高亮（视觉提示）
        tgt = self.tree.identify_row(event.y)
        if tgt and tgt != self._last_target and tgt != self._dragging_iid:
            # 清除上次
            if self._last_target:
                try:
                    tags = tuple(t for t in self.tree.item(self._last_target, 'tags') if t != 'target')
                    self.tree.item(self._last_target, tags=tags)
                except Exception:
                    pass
            # 添加高亮
            try:
                cur_tags = tuple(t for t in self.tree.item(tgt, 'tags') if t != 'target')
                self.tree.item(tgt, tags=cur_tags + ('target',))
            except Exception:
                pass
            self._last_target = tgt

    def _on_tree_button_release(self, event):
        if not getattr(self, '_dragging_iid', None):
            return
        # 销毁可能存在的虚影
        if getattr(self, '_drag_ghost', None):
            try:
                self._drag_ghost.destroy()
            except Exception:
                pass
            self._drag_ghost = None
            self._drag_start = None
        tgt = self.tree.identify_row(event.y)
        src = self._dragging_iid
        # 清除高亮
        if self._last_target:
            try:
                tags = tuple(t for t in self.tree.item(self._last_target, 'tags') if t != 'target')
                self.tree.item(self._last_target, tags=tags)
            except Exception:
                pass
            self._last_target = None
        self._dragging_iid = None
        if not tgt or tgt == src:
            return
        # 计算目标索引并移动
        try:
            src_index = self.tree.index(src)
            tgt_index = self.tree.index(tgt)
            # 如果目标在源之后，插入到目标之后的位置
            if tgt_index > src_index:
                self.tree.move(src, '', tgt_index + 1)
            else:
                self.tree.move(src, '', tgt_index)
            # 重新应用行色并保存顺序
            self._apply_row_tags()
            self._reorder_save()
        except Exception:
            pass

    def _create_tree_context_menu(self):
        self._ctx_menu = tk.Menu(self, tearoff=0)
        # 增加“添加网址”到右键菜单（支持在空白处添加）
        self._ctx_menu.add_command(label='添加网址', command=self.add_url_context)
        self._ctx_menu.add_command(label='打开', command=self.open_selected_edge)
        self._ctx_menu.add_command(label='编辑', command=self.edit_selected)
        self._ctx_menu.add_command(label='删除', command=self.remove_selected)
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label='上移', command=self.move_up)
        self._ctx_menu.add_command(label='下移', command=self.move_down)
        self.tree.bind('<Button-3>', self._show_context_menu)

    def _show_context_menu(self, event):
        try:
            iid = self.tree.identify_row(event.y)
            # 记录右键上下文（被点击的行，可能为 None 表示空白处）
            self._ctx_invoked_iid = iid
            if iid:
                if iid not in self.tree.selection():
                    self.tree.selection_set(iid)
            # 无论是否点击到行，都显示菜单（方便在空白处添加）
            self._ctx_menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                self._ctx_menu.grab_release()
            except Exception:
                pass

    def add_url_context(self):
        """通过右键菜单添加网址；如果是在某行上右键则插入到该行之后，否则追加到末尾。"""
        s = simpledialog.askstring('添加网址', '输入网址：', parent=self)
        if s is None:
            return
        s = s.strip()
        if not s:
            return
        try:
            invoked = getattr(self, '_ctx_invoked_iid', None)
            if invoked:
                idx = self.tree.index(invoked)
                pos = idx + 1
                tag = 'even' if pos % 2 == 0 else 'odd'
                new_iid = self.tree.insert('', pos, values=(s,), tags=(tag,))
            else:
                idx = len(self.tree.get_children())
                tag = 'even' if idx % 2 == 0 else 'odd'
                new_iid = self.tree.insert('', 'end', values=(s,), tags=(tag,))
            try:
                self.tree.selection_set(new_iid)
                self.tree.see(new_iid)
            except Exception:
                pass
            self._apply_row_tags()
            self._save_groups()
        finally:
            # 清理上下文标记
            self._ctx_invoked_iid = None

    def edit_selected(self):
        sel = list(self.tree.selection())
        if not sel:
            return
        iid = sel[0]
        cur = self.tree.item(iid, 'values')[0]
        s = simpledialog.askstring('编辑网址', '修改网址：', initialvalue=cur, parent=self)
        if s is None:
            return
        s = s.strip()
        if not s:
            return
        self.tree.item(iid, values=(s,))
        self._save_groups()

    def move_up(self):
        sel = list(self.tree.selection())
        if not sel:
            return
        for iid in sel:
            index = self.tree.index(iid)
            if index > 0:
                self.tree.move(iid, '', index - 1)
        self._reorder_save()

    def move_down(self):
        sel = list(self.tree.selection())
        if not sel:
            return
        for iid in reversed(sel):
            index = self.tree.index(iid)
            length = len(self.tree.get_children())
            if index < length - 1:
                self.tree.move(iid, '', index + 1)
        self._reorder_save()

    def _reorder_save(self):
        # 将 Treeview 当前顺序保存回分组并持久化
        self.groups[self.current_group] = self.get_all_urls()
        self._save_groups()

    def _refresh_listbox(self):
        # 清空并填充 Treeview
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for idx, u in enumerate(self.groups.get(self.current_group, [])):
            tag = 'even' if idx % 2 == 0 else 'odd'
            self.tree.insert('', 'end', values=(u,), tags=(tag,))
        # 确保行颜色正确
        self._apply_row_tags()


if __name__ == '__main__':
    app = SitesApp()
    app.mainloop()
