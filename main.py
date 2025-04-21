import logging
import ttkbootstrap as ttkb
from gui.app import PDFOrganizerApp

# 设置日志，仅输出到文件
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pdf_organizer.log")  # 只输出到文件
    ]
)

if __name__ == "__main__":
    try:
        # 使用litera主题启动窗口
        root = ttkb.Window(themename="litera")
        app = PDFOrganizerApp(root)
        root.mainloop()
    except Exception as e:
        logging.error(f"程序启动失败: {str(e)}")
        import traceback
        traceback.print_exc()
        input("按任意键退出...")