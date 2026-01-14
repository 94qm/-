"""使用 Python 在 Windows 上以编程方式用 Microsoft Edge 打开多个网页（每个网址为一个标签）。

用法示例：直接运行此脚本会打开五个指定的网址。函数 `open_in_edge(urls)` 可被导入并复用。

注意：
- 优先在 PATH 中查找 `msedge` 可执行程序；若找不到，会尝试常见安装目录；若仍找不到，会降级到使用默认系统浏览器逐个打开标签页。
- 本脚本使用 subprocess 启动 Edge，可在不手动运行终端命令的情况下以编程形式打开浏览器。
"""

from __future__ import annotations

import os
import subprocess
import shutil
import webbrowser
from typing import List, Optional

# 要打开的 URL 列表（你可以修改或从其它模块/界面传入）
DEFAULT_URLS = [
    "https://chatgpt.com/",
    "https://gemini.google.com/app?hl=zh",
    "https://grok.com/",
    "https://www.youtube.com/",
    "https://www.zhihu.com/",
]


def find_edge_executable() -> Optional[str]:
    """尝试找到 msedge 可执行文件的路径。

    返回可执行文件绝对路径或 None（未找到）。
    """
    # 1) 直接在 PATH 查找
    edge = shutil.which("msedge")
    if edge:
        return edge

    # 2) 常见安装目录
    candidates = []
    program_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    program_files_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    local_appdata = os.environ.get("LOCALAPPDATA")

    candidates += [
        os.path.join(program_files, "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(program_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"),
    ]
    if local_appdata:
        candidates.append(os.path.join(local_appdata, "Microsoft", "Edge", "Application", "msedge.exe"))

    for p in candidates:
        if os.path.isfile(p):
            return p

    return None


def open_in_edge(urls: List[str], new_window: bool = True) -> bool:
    """在 Edge 中打开给定的 URL 列表。

    参数:
      urls: 要打开的 URL 列表
      new_window: 是否使用 --new-window（True）否则在已打开的 Edge 窗口中新标签打开（False）

    返回 True 表示成功地用 Edge 启动；False 表示降级为使用默认浏览器逐个打开。
    """
    if not urls:
        return False

    edge_exe = find_edge_executable()
    if edge_exe:
        args = [edge_exe]
        if new_window:
            # --new-window 将所有提供的 URL 放到一个新窗口中
            args.append("--new-window")
        # 添加 URL 列表
        args.extend(urls)
        try:
            # 不使用 shell，直接启动可执行文件
            subprocess.Popen(args)
            return True
        except Exception as e:
            print(f"启动 Edge 失败：{e}")
            # 降级到默认浏览器

    # 降级：使用系统默认浏览器逐个打开标签
    try:
        for url in urls:
            webbrowser.open_new_tab(url)
        return False
    except Exception as e:
        print(f"降级打开失败：{e}")
        return False


if __name__ == "__main__":
    ok = open_in_edge(DEFAULT_URLS, new_window=True)
    if ok:
        print("已使用 Edge 打开 URL（新窗口）。")
    else:
        print("未找到 Edge 或启动失败，已使用默认浏览器逐个打开 URL。")
