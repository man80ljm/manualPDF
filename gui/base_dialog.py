import ttkbootstrap as ttkb
from ttkbootstrap.style import Style
import logging
from config import DEFAULT_FONT
from utils import center_window, log_error

class BaseDialog:
    def __init__(self, parent, title, geometry, scaled_font_size):
        """
        对话框基类，处理公共的对话框逻辑
        参数:
            parent: 父对象（通常是PDFOrganizerApp实例）
            title: 对话框标题
            geometry: 对话框尺寸（格式如 "1000x400"）
            scaled_font_size: 缩放后的字体大小
        """
        try:
            self.parent = parent
            self.scaled_font_size = scaled_font_size
            self.dialog = ttkb.Toplevel(parent.root)
            self.dialog.title(title)
            self.dialog.geometry(geometry)
            self.dialog.minsize(*map(int, geometry.split("x")))
            self.dialog.transient(parent.root)  # 设置为模态对话框

            # 配置样式
            self.configure_styles()

            # 居中窗口
            center_window(self.dialog, self.parent.root)

        except Exception as e:
            log_error(f"BaseDialog 初始化失败: {str(e)}")

    def configure_styles(self):
        """
        配置对话框的样式（主要是字体）
        """
        try:
            style = Style()
            style.configure("Custom.TLabel", font=(DEFAULT_FONT, self.scaled_font_size, "normal"))
            style.configure("Custom.TCheckbutton", font=(DEFAULT_FONT, self.scaled_font_size, "normal"))
            style.configure("Custom.TButton", font=(DEFAULT_FONT, self.scaled_font_size, "normal"))
            style.configure("Custom.TEntry", font=(DEFAULT_FONT, self.scaled_font_size, "normal"))
        except Exception as e:
            log_error(f"configure_styles 失败: {str(e)}")

    def destroy(self):
        """
        销毁对话框
        """
        try:
            self.dialog.destroy()
        except Exception as e:
            log_error(f"destroy 失败: {str(e)}")