import logging
import traceback
import os
import sys
import shutil

def center_window(window, parent=None):
    """
    居中窗口的工具函数
    参数:
        window: 要居中的窗口对象
        parent: 父窗口对象（可选），如果提供则相对于父窗口居中，否则相对于屏幕
    """
    try:
        window.update_idletasks()
        if parent:
            parent.update_idletasks()
            parent_x, parent_y = parent.winfo_x(), parent.winfo_y()
            parent_width, parent_height = parent.winfo_width(), parent.winfo_height()
            window_width, window_height = window.winfo_width(), window.winfo_height()
            x = parent_x + (parent_width - window_width) // 2 + 20
            y = parent_y + (parent_height - window_height) // 2 + 20
        else:
            screen_width = window.winfo_screenwidth()
            screen_height = window.winfo_screenheight()
            window_width = window.winfo_width()
            window_height = window.winfo_height()
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2

        x, y = max(0, x), max(0, y)
        window.geometry(f"+{x}+{y}")
    except Exception as e:
        logging.error(f"center_window 失败: {str(e)}")
        traceback.print_exc()

def get_poppler_path():
    """
    获取Poppler的路径
    返回:
        Poppler的bin目录路径，或者None（如果未找到则使用系统PATH）
    """
    try:
        # 确定项目根目录
        if getattr(sys, 'frozen', False):
            # 打包后的路径：与可执行文件同级目录
            base_path = os.path.dirname(sys.executable)
            # 尝试不同的可能路径
            possible_paths = [
                os.path.join(base_path, "_internal", "assets", "poppler"),  # 打包后的实际路径
                os.path.join(base_path, "assets", "poppler"),
                os.path.join(base_path, "poppler"),
            ]
        else:
            # 开发时的路径：从utils.py所在目录获取项目根目录
            base_path = os.path.dirname(os.path.abspath(__file__))
            possible_paths = [os.path.join(base_path, "assets", "poppler")]

        for poppler_bin in possible_paths:
            poppler_bin = os.path.abspath(poppler_bin)  # 转换为绝对路径
            logging.info(f"尝试Poppler路径: {poppler_bin}")
            # 检查路径是否存在
            if os.path.exists(poppler_bin):
                logging.info(f"找到Poppler: {poppler_bin}")
                return poppler_bin

        # 调试：列出目录内容
        assets_dir = os.path.join(base_path, "_internal", "assets")
        if os.path.exists(assets_dir):
            logging.info(f"assets目录存在，内容: {os.listdir(assets_dir)}")
        else:
            logging.warning(f"assets目录不存在: {assets_dir}")

        poppler_dir = os.path.join(base_path, "_internal", "assets", "poppler")
        if os.path.exists(poppler_dir):
            logging.info(f"poppler目录存在，内容: {os.listdir(poppler_dir)}")
        else:
            logging.warning(f"poppler目录不存在: {poppler_dir}")

        logging.warning(f"未找到Poppler的bin目录，将尝试使用系统PATH")
        # 最后尝试系统PATH
        if shutil.which("pdftoppm"):
            logging.info("找到系统PATH中的Poppler")
            return None
        else:
            logging.warning("系统PATH中也未找到Poppler")
            return None
    except Exception as e:
        logging.error(f"get_poppler_path 失败: {str(e)}")
        traceback.print_exc()
        return None

def log_error(message):
    """
    记录错误的工具函数
    参数:
        message: 错误信息
    """
    logging.error(message)
    traceback.print_exc()