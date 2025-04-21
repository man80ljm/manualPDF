# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# 规范化 poppler 路径
poppler_source = os.path.normpath('D:\\manualPDF\\assets\\poppler')
poppler_target = 'assets\\poppler'

# 收集 ttkbootstrap 的资源文件和子模块
ttkbootstrap_datas = collect_data_files('ttkbootstrap')
ttkbootstrap_hiddenimports = collect_submodules('ttkbootstrap')

a = Analysis(
    ['main.py'],
    pathex=['D:\\manualPDF'],
    binaries=[],
    datas=[
        ('assets\\pdf.ico', 'assets'),
        (poppler_source, poppler_target),
        ('settings.json', '.'),
    ] + ttkbootstrap_datas,
    hiddenimports=[
        'ttkbootstrap',
        'pdf2image',
        'PIL',
        'PIL._imagingtk',
        'PIL.ImageTk',
    ] + ttkbootstrap_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PDFOrganizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 确保控制台窗口不显示
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets\\pdf.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PDFOrganizer',
)