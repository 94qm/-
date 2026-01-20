# 打开网页工具（打包说明）

此项目包含一个简单的 GUI 工具：**打开网页工具**（网站分组与批量打开功能）。已通过 PyInstaller 打包为单文件可执行程序 `打开网页工具.exe`，并放置在 `D:\Desktop`。

## 运行
- 直接双击 `D:\Desktop\打开网页工具.exe` 即可运行图形界面。

## 重新打包（开发者）
1. 确保在你的 Python 环境中安装了依赖：
   ```bash
   python -m pip install -r requirements.txt
   python -m pip install pyinstaller
   ```
2. 使用 PyInstaller 打包（在项目根目录运行）：
   ```bash
   python -m PyInstaller --onefile --noconsole --name "打开网页工具" 测试.py
   ```
3. 生成的 exe 在 `dist/打开网页工具.exe`，可以复制到桌面或其它位置。

## 清理构建产物
- 删除 `build/`、`dist/` 文件夹和 `打开网页工具.spec` 文件可清理临时构建产物。

## 依赖
- requests
- pillow（用于图片处理）

如果你想要我：
- 自动清理 `build/` 和 `.spec` 文件，或
- 把 exe 压缩为 zip 并生成校验（例如 SHA256），
告诉我你更希望我继续的下一步。