import tkinter as tk
import ttkbootstrap as ttkb
import json
from gui.base_dialog import BaseDialog
from config import WINDOW_SIZES
from utils import log_error

class SettingsDialog(BaseDialog):
    def __init__(self, parent, scaled_font_size):
        # 调用基类构造函数，设置标题、大小和字体
        super().__init__(parent, "设置", WINDOW_SIZES["settings"], scaled_font_size)

        try:
            # 居中容器
            container = ttkb.Label(self.dialog, text="", width=30)
            container.pack(pady=10)

            ttkb.Label(container, text="命名和排序设置", style="Custom.TLabel").pack(anchor="center", pady=10)

            # 设置选项
            self.use_original_name_var = tk.BooleanVar(value=self.parent.settings.get("use_original_name", True))
            self.skip_sorting_var = tk.BooleanVar(value=self.parent.settings.get("skip_sorting", False))
            self.keep_source_pdf_var = tk.BooleanVar(value=self.parent.settings.get("keep_source_pdf", False))

            ttkb.Checkbutton(container, text="默认使用原文件名（多页 PDF 将添加页码后缀）", 
                             variable=self.use_original_name_var, bootstyle="info",
                             style="Custom.TCheckbutton").pack(anchor="w", pady=10)
            ttkb.Checkbutton(container, text="跳过手动排序", 
                             variable=self.skip_sorting_var, bootstyle="info",
                             style="Custom.TCheckbutton").pack(anchor="w", pady=10)
            ttkb.Checkbutton(container, text="转换后保留 PDF 源文件（原位置不变）", 
                             variable=self.keep_source_pdf_var, bootstyle="info",
                             style="Custom.TCheckbutton").pack(anchor="w", pady=10)
            ttkb.Button(container, text="保存", command=self.save, bootstyle="primary",
                        style="Custom.TButton").pack(anchor="center", pady=10)

        except Exception as e:
            log_error(f"SettingsDialog 初始化失败: {str(e)}")

    def save(self):
        try:
            settings = {
                "use_original_name": self.use_original_name_var.get(),
                "skip_sorting": self.skip_sorting_var.get(),
                "keep_source_pdf": self.keep_source_pdf_var.get()
            }
            with open("settings.json", "w") as f:
                json.dump(settings, f)
            self.parent.settings = settings
            self.destroy()
        except Exception as e:
            log_error(f"SettingsDialog save 失败: {str(e)}")