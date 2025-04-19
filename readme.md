PDF 文件整理工具
这是一个用于整理 PDF 文件的工具，可以将 PDF 文件整理到带编号的文件夹中，并转换为超高清 JPG 图片，同时删除原始 PDF 文件。工具使用简单，支持实时进度显示，界面不会卡顿。
功能

选择多个 PDF 文件。
为每个 PDF 创建带编号的文件夹（例如 1.test）。
将 PDF 转换为超高清 JPG 图片（例如 1.jpg, 2.jpg）。
转换成功后自动删除原始 PDF 文件。
实时显示处理进度，避免界面卡顿。

使用方法

解压 PDF_Organizer.zip 文件到任意目录。解压后目录结构如下：PDF_Organizer/
├── organize_pdfs_gui.exe
├── poppler/
│   ├── Library/
│   │   ├── bin/
│   │   │   ├── pdftoppm.exe
│   │   │   └── ...


重要：请勿删除 poppler 文件夹，且确保它与 organize_pdfs_gui.exe 在同一目录下。poppler 文件夹包含工具运行所需的依赖，删除后将无法转换 PDF 为图片。
双击 organize_pdfs_gui.exe 运行程序。
点击“选择 PDF 文件”按钮，选择要处理的 PDF 文件。
程序会自动处理：
创建带编号的文件夹。
将 PDF 转换为 JPG。
删除原始 PDF 文件。


处理过程中，进度信息会实时显示在窗口中，处理完成后会弹出总结消息。

示例

输入：选择一个名为 test.pdf 的文件（有 3 页）。
输出：
文件夹结构：1.test/
├── 1.jpg
├── 2.jpg
└── 3.jpg


界面显示：已选择 1 个 PDF 文件：
test.pdf
已处理: test.pdf -> 1.test
正在转换: test.pdf
已生成: 1.jpg
已生成: 2.jpg
已生成: 3.jpg
已删除原始 PDF: test.pdf
处理完成！成功整理 1/1 个 PDF 文件，生成 3 张图片。





注意事项

Poppler 依赖：poppler 文件夹是工具运行的必要依赖，请勿删除或移动。如果缺少 poppler 文件夹，程序将无法转换 PDF 文件，并会提示错误。
权限：确保目标文件夹有写入和删除权限，否则可能无法创建文件夹或删除 PDF 文件。
系统兼容性：本工具适用于 Windows 系统。
杀毒软件：某些杀毒软件可能误报 .exe 文件为病毒，请将其添加到白名单。

常见问题

程序启动时提示“无法找到 Poppler”？
确保 poppler 文件夹存在，且与 organize_pdfs_gui.exe 在同一目录下。
检查 poppler/Library/bin 目录下是否有 pdftoppm.exe 文件。


转换 PDF 失败？
确认 PDF 文件是否损坏。
确保有足够的磁盘空间来保存生成的 JPG 文件。
检查目标文件夹是否有写入权限。



联系方式
如果有任何问题或建议，请联系开发者：[18127833715]。
