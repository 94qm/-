"""工具：只保留“打开网站”界面"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import webbrowser

from deepseek import DEFAULT_URLS, open_in_edge


class SitesApp(tk.Tk):
    def __init__(self, urls=None):
        super().__init__()
        self.title('打开网站')
        self.geometry('520x360')
        self.urls = urls or list(DEFAULT_URLS)
        self._build()

    def _build(self):
        frm = tk.Frame(self, padx=10, pady=10)
        frm.pack(fill=tk.BOTH, expand=True)

        tk.Label(frm, text='网址列表（可编辑）：').pack(anchor='w')
        self.listbox = tk.Listbox(frm, height=10, width=72, selectmode=tk.EXTENDED)
        self.listbox.pack(fill=tk.BOTH, expand=False, padx=2, pady=6)

        for u in self.urls:
            self.listbox.insert(tk.END, u)

        btn_frame = tk.Frame(frm)
        btn_frame.pack(fill=tk.X, pady=(6,0))

        tk.Button(btn_frame, text='用 Edge 打开全部', command=self.open_all_edge).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text='在默认浏览器打开全部', command=self.open_all_default).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text='打开选中（Edge）', command=self.open_selected_edge).pack(side=tk.LEFT, padx=6)

        edit_frame = tk.Frame(frm)
        edit_frame.pack(fill=tk.X, pady=(10,0))
        tk.Label(edit_frame, text='新网址:').pack(side=tk.LEFT)
        self.new_url_var = tk.StringVar()
        tk.Entry(edit_frame, textvariable=self.new_url_var, width=48).pack(side=tk.LEFT, padx=6)
        tk.Button(edit_frame, text='添加', command=self.add_url).pack(side=tk.LEFT, padx=4)
        tk.Button(edit_frame, text='删除选中', command=self.remove_selected).pack(side=tk.LEFT, padx=4)
        # 恢复默认网址按钮
        tk.Button(edit_frame, text='恢复默认', command=self.restore_defaults).pack(side=tk.LEFT, padx=6)

        self.status_var = tk.StringVar(value='就绪')
        tk.Label(self, textvariable=self.status_var, anchor='w').pack(fill=tk.X, side=tk.BOTTOM)

    def get_all_urls(self):
        return [self.listbox.get(i) for i in range(self.listbox.size())]

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
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning('未选择', '请先选择要打开的一个或多个网址')
            return
        urls = [self.listbox.get(i) for i in sel]
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
        self.listbox.insert(tk.END, u)
        self.new_url_var.set('')

    def remove_selected(self):
        sel = list(self.listbox.curselection())
        if not sel:
            return
        for i in reversed(sel):
            self.listbox.delete(i)

    def restore_defaults(self):
        """恢复为 DEFAULT_URLS 列表。"""
        if messagebox.askyesno('确认', '是否恢复为默认网址列表？'):
            self.listbox.delete(0, tk.END)
            for u in DEFAULT_URLS:
                self.listbox.insert(tk.END, u)
            self.status_var.set('已恢复默认网址')


if __name__ == '__main__':
    app = SitesApp()
    app.mainloop()
