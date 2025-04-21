PDF 文件整理工具
PDF 文件整理工具
这是一个用于整理 PDF 文件的工具，可以将 PDF 文件转换为 JPG 图片，并支持文件排序和重命名。
1. 程序安装的依赖与库函数
系统要求

操作系统：Windows（因依赖 Poppler）
Python 版本：Python 3.6 或以上（推荐 3.10）

依赖库
在项目根目录运行以下命令安装依赖（建议使用虚拟环境）：
pip install -r requirements.txt

如果 requirements.txt 不存在，可手动安装以下库：
pip install ttkbootstrap pdf2image pillow -i https://pypi.tuna.tsinghua.edu.cn/simple


ttkbootstrap：用于构建美观的 GUI 界面
pdf2image：用于将 PDF 文件转换为图片
pillow：用于处理图片文件

其他依赖

Poppler：pdf2image 需要 Poppler 工具支持。程序已将 Poppler 打包在 assets/poppler 目录中，无需额外安装。

2. 软件用法
运行程序

确保已安装依赖（见上节）。
在项目根目录运行：D:\manualPDF\venv\Scripts\activate
cd D:\manualPDF
python main.py

或直接运行打包后的 EXE（无需安装 Python）：cd D:\manualPDF\dist\PDFOrganizer
PDFOrganizer.exe



功能说明

选择 PDF 文件：点击“选择 PDF 文件”按钮，选择一个或多个 PDF 文件。
转换与整理：
程序会将每个 PDF 文件转换为 JPG 图片（每页一个图片）。
图片保存在与 PDF 文件同目录的子文件夹中（格式为 1.文件名、2.文件名 等）。


命名与排序设置：
点击“命名和排序设置”按钮，可以调整文件命名规则和排序方式。
支持使用原文件名（添加页码后缀）或跳过手动排序。


预览与重命名：
在排序和重命名对话框中，可以预览 PDF 文件的第一页。
双击列表中的文件名可进行重命名。



3. 打包命令
打包命令
使用 PyInstaller 将程序打包为 EXE 文件，确保在虚拟环境中运行以下命令：
D:\manualPDF\venv\Scripts\activate
cd D:\manualPDF
D:\manualPDF\venv\Scripts\pyinstaller PDFOrganizer.spec

重要说明

必须使用虚拟环境的 PyInstaller：项目的依赖（如 ttkbootstrap、pdf2image）安装在虚拟环境 D:\manualPDF\venv 中。使用系统环境的 PyInstaller 可能导致依赖未被正确打包（例如 ModuleNotFoundError）。
.spec 文件：PDFOrganizer.spec 已配置好资源文件（如 poppler 和图标），确保直接使用此文件打包。
打包后目录：打包结果在 D:\manualPDF\dist\PDFOrganizer，包含 PDFOrganizer.exe 和所有依赖。

调试
如果打包或运行 EXE 时遇到问题：

检查 pdf_organizer.log 文件，查看错误日志。
启用 PyInstaller 调试模式：D:\manualPDF\venv\Scripts\pyinstaller --log-level DEBUG PDFOrganizer.spec





假设 Poppler 已安装在 C:\poppler\Library\bin 并添加到 PATH，运行：

pdftoppm -v

输出：
pdftoppm version 24.07.0
Copyright 2005-2024 The Poppler Developers - http://poppler.freedesktop.org
Copyright 1996-2011, 2022 Glyph & Cog, LLC