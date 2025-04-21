import os
import shutil
import tkinter as tk
import tkinter.ttk as ttk
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.style import Style
from tkinter import filedialog, messagebox, scrolledtext, Toplevel, Listbox, Entry, Canvas
from pdf2image import convert_from_path
from PIL import Image, ImageTk
import threading
import queue
import sys
import json
import logging
from threading import Thread
import traceback

# 设置日志，同时输出到控制台和文件
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pdf_organizer.log"),
        logging.StreamHandler(sys.stdout)  # 输出到控制台
    ]
)

class SettingsDialog:
    def __init__(self, parent, scaled_font_size):
        try:
            self.parent = parent
            self.dialog = ttkb.Toplevel(parent.root)
            self.dialog.title("设置")
            self.dialog.geometry("400x300")
            self.dialog.minsize(400, 300)

            # 居中窗口
            self.center_window(self.dialog, self.parent.root)

            # 居中容器
            container = ttkb.Label(self.dialog, text="", width=30)
            container.pack(pady=10)

            # 使用样式设置字体
            style = Style()
            style.configure("Custom.TLabel", font=("Helvetica", scaled_font_size, "normal"))
            style.configure("Custom.TCheckbutton", font=("Helvetica", scaled_font_size, "normal"))
            style.configure("Custom.TButton", font=("Helvetica", scaled_font_size, "normal"))

            ttkb.Label(container, text="命名和排序设置", style="Custom.TLabel").pack(anchor="center", pady=10)

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
            logging.error(f"SettingsDialog 初始化失败: {str(e)}")
            traceback.print_exc()

    def center_window(self, window, parent):
        try:
            parent.update_idletasks()
            parent_x = parent.winfo_x()
            parent_y = parent.winfo_y()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()

            window.update_idletasks()
            window_width = window.winfo_width()
            window_height = window.winfo_height()

            x = parent_x + (parent_width - window_width) // 2 + 20
            y = parent_y + (parent_height - window_height) // 2 + 20

            x = max(0, x)
            y = max(0, y)

            window.geometry(f"+{x}+{y}")
        except Exception as e:
            logging.error(f"center_window 失败: {str(e)}")
            traceback.print_exc()

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
            self.dialog.destroy()
        except Exception as e:
            logging.error(f"SettingsDialog save 失败: {str(e)}")
            traceback.print_exc()

class SortRenameDialog:
    def __init__(self, parent, pdf_files, scaled_font_size):
        try:
            self.parent = parent
            self.pdf_files = [(os.path.basename(f), f) for f in pdf_files]
            self.result = None
            self.preview_thread = None
            self.scaled_font_size = scaled_font_size  # 保存 scaled_font_size

            self.dialog = ttkb.Toplevel(parent.root)
            self.dialog.title("排序和重命名 PDF 文件")
            self.dialog.geometry("2000x1000")
            self.dialog.minsize(2000, 1000)
            self.dialog.transient(parent.root)

            self.center_window(self.dialog, self.parent.root)

            self.paned_window = ttk.PanedWindow(self.dialog, orient=tk.HORIZONTAL)
            self.paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            listbox_frame = ttk.Frame(self.paned_window)
            self.paned_window.add(listbox_frame, weight=1)

            self.listbox = Listbox(listbox_frame, selectmode=tk.SINGLE, width=80, height=15,
                                   font=("Helvetica", scaled_font_size, "normal"), selectbackground="green", selectforeground="black")
            self.listbox.pack(fill=tk.BOTH, expand=True)
            for name, _ in self.pdf_files:
                self.listbox.insert(tk.END, name)

            self.listbox.bind("<B1-Motion>", self.on_drag)
            self.listbox.bind("<Button-1>", self.start_drag)
            self.listbox.bind("<ButtonRelease-1>", self.on_drag_release)
            self.listbox.bind("<Double-1>", self.rename_item)
            self.listbox.bind("<<ListboxSelect>>", self.show_preview)

            canvas_frame = ttk.Frame(self.paned_window)
            self.paned_window.add(canvas_frame, weight=1)

            self.paned_window.update_idletasks()
            self.paned_window.sashpos(0, 1000)  # 2000 / 2 = 1000

            self.preview_canvas = Canvas(canvas_frame, bg="white")
            self.preview_canvas.pack(fill=tk.BOTH, expand=True)
            # 立即更新画布尺寸
            self.preview_canvas.update_idletasks()
            self.canvas_width = self.preview_canvas.winfo_width()
            self.canvas_height = self.preview_canvas.winfo_height()
            # 确保画布尺寸至少为 1
            self.canvas_width = max(1, self.canvas_width)
            self.canvas_height = max(1, self.canvas_height)
            self.preview_canvas.create_text(50, 50, text="选择文件以预览", fill="gray", font=("Helvetica", scaled_font_size, "normal"))
            
            self.paned_window.bind("<Configure>", self.on_paned_resize)

            button_frame = ttkb.Frame(self.dialog)
            button_frame.pack(fill=tk.X, pady=10)
            ttkb.Button(button_frame, text="确定", command=self.confirm, bootstyle="success",
                        style="Custom.TButton").pack(side=tk.LEFT, padx=20)
            ttkb.Button(button_frame, text="取消", command=self.cancel, bootstyle="danger",
                        style="Custom.TButton").pack(side=tk.RIGHT, padx=20)

            self.drag_start_index = None
            self.current_image = None

            self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
        except Exception as e:
            logging.error(f"SortRenameDialog 初始化失败: {str(e)}")
            traceback.print_exc()

    def center_window(self, window, parent):
        try:
            parent.update_idletasks()
            parent_x = parent.winfo_x()
            parent_y = parent.winfo_y()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()

            window.update_idletasks()
            window_width = window.winfo_width()
            window_height = window.winfo_height()

            x = parent_x + (parent_width - window_width) // 2 + 20
            y = parent_y + (parent_height - window_height) // 2 + 20

            x = max(0, x)
            y = max(0, y)

            window.geometry(f"+{x}+{y}")
        except Exception as e:
            logging.error(f"center_window 失败: {str(e)}")
            traceback.print_exc()

    def on_paned_resize(self, event):
        try:
            new_width = self.preview_canvas.winfo_width()
            new_height = self.preview_canvas.winfo_height()
            if new_width != self.canvas_width or new_height != self.canvas_height:
                self.canvas_width = new_width
                self.canvas_height = new_height
                selection = self.listbox.curselection()
                if selection and self.current_image:
                    index = selection[0]
                    _, pdf_path = self.pdf_files[index]
                    self.load_preview(pdf_path)
        except Exception as e:
            logging.error(f"on_paned_resize 失败: {str(e)}")
            traceback.print_exc()

    def start_drag(self, event):
        try:
            self.drag_start_index = self.listbox.nearest(event.y)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.drag_start_index)
            self.listbox.activate(self.drag_start_index)
        except Exception as e:
            logging.error(f"start_drag 失败: {str(e)}")
            traceback.print_exc()

    def on_drag(self, event):
        try:
            if self.drag_start_index is None:
                return
            current_index = self.listbox.nearest(event.y)
            if current_index != self.drag_start_index and 0 <= current_index < len(self.pdf_files):
                name, path = self.pdf_files.pop(self.drag_start_index)
                self.pdf_files.insert(current_index, (name, path))
                self.listbox.delete(self.drag_start_index)
                self.listbox.insert(current_index, name)
                self.drag_start_index = current_index
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(self.drag_start_index)
                self.listbox.activate(self.drag_start_index)
        except Exception as e:
            logging.error(f"on_drag 失败: {str(e)}")
            traceback.print_exc()

    def on_drag_release(self, event):
        try:
            if self.drag_start_index is None:
                return
            current_index = self.listbox.nearest(event.y)
            if 0 <= current_index < len(self.pdf_files):
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(current_index)
                self.listbox.activate(current_index)
            self.drag_start_index = None
        except Exception as e:
            logging.error(f"on_drag_release 失败: {str(e)}")
            traceback.print_exc()

    def show_preview(self, event):
        try:
            selection = self.listbox.curselection()
            if not selection:
                return
            index = selection[0]
            _, pdf_path = self.pdf_files[index]

            if not hasattr(self, 'preview_thread'):
                self.preview_thread = None

            if self.preview_thread and self.preview_thread.is_alive():
                return

            self.preview_thread = Thread(target=self.load_preview, args=(pdf_path,))
            self.preview_thread.start()
        except Exception as e:
            logging.error(f"show_preview 失败: {str(e)}")
            traceback.print_exc()

    def load_preview(self, pdf_path):
        try:
            images = convert_from_path(pdf_path, dpi=72, poppler_path=self.parent.poppler_path)
            image = images[0]
            self.current_image = image

            # 确保 canvas 尺寸有效
            if self.canvas_width <= 20 or self.canvas_height <= 20:
                self.parent.root.after(0, lambda: self.update_preview_error("画布尺寸无效"))
                logging.error("画布尺寸无效: width=%d, height=%d" % (self.canvas_width, self.canvas_height))
                return

            max_width = self.canvas_width - 20
            max_height = self.canvas_height - 20

            # 确保 image 尺寸有效
            if image.width <= 0 or image.height <= 0:
                self.parent.root.after(0, lambda: self.update_preview_error("图像尺寸无效"))
                logging.error("图像尺寸无效: width=%d, height=%d" % (image.width, image.height))
                return

            image_ratio = image.width / image.height

            # 避免除零错误
            if max_height <= 0:
                self.parent.root.after(0, lambda: self.update_preview_error("最大高度无效"))
                logging.error("最大高度无效: max_height=%d" % max_height)
                return

            if image_ratio > max_width / max_height:
                new_width = max_width
                new_height = int(new_width / image_ratio)
            else:
                new_height = max_height
                new_width = int(new_height * image_ratio)

            # 确保宽度和高度至少为 1
            new_width = max(1, new_width)
            new_height = max(1, new_height)

            image = image.resize((new_width, new_height), Image.LANCZOS)
            self.preview_image = ImageTk.PhotoImage(image)
            self.parent.root.after(0, self.update_preview)
        except Exception as e:
            self.parent.root.after(0, lambda: self.update_preview_error(str(e)))
            logging.error(f"load_preview 失败: {str(e)}")
            traceback.print_exc()

    def update_preview(self):
        try:
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(self.canvas_width // 2, self.canvas_height // 2, image=self.preview_image)
        except Exception as e:
            logging.error(f"update_preview 失败: {str(e)}")
            traceback.print_exc()

    def update_preview_error(self, error):
        try:
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(self.canvas_width // 2, self.canvas_height // 2, text=f"预览失败: {error}", 
                                            fill="red", font=("Helvetica", self.scaled_font_size, "normal"))
        except Exception as e:
            logging.error(f"update_preview_error 失败: {str(e)}")
            traceback.print_exc()

    def rename_item(self, event):
        try:
            index = self.listbox.nearest(event.y)
            if index < 0:
                return
            current_name, path = self.pdf_files[index]

            rename_dialog = ttkb.Toplevel(self.dialog)
            rename_dialog.title("重命名")
            rename_dialog.geometry("600x200")
            rename_dialog.minsize(600, 200)
            rename_dialog.transient(self.dialog)
            rename_dialog.grab_set()

            self.center_window(rename_dialog, self.dialog)

            # 使用动态字体大小
            style = Style()
            style.configure("Custom.TLabel", font=("Helvetica", self.scaled_font_size, "normal"))
            style.configure("Custom.TEntry", font=("Helvetica", self.scaled_font_size, "normal"))
            style.configure("Custom.TButton", font=("Helvetica", self.scaled_font_size, "normal"))

            ttkb.Label(rename_dialog, text="输入新文件名（不含扩展名）：", style="Custom.TLabel").pack(pady=5)
            entry = ttkb.Entry(rename_dialog, width=80, style="Custom.TEntry")
            entry.insert(0, os.path.splitext(current_name)[0])
            entry.pack(pady=5, fill=tk.X, expand=True)

            def save_name():
                try:
                    new_name = entry.get().strip()
                    if new_name:
                        invalid_chars = '<>:"/\\|?*'
                        for char in invalid_chars:
                            new_name = new_name.replace(char, "_")
                        new_name = f"{new_name}.pdf"
                        self.pdf_files[index] = (new_name, path)
                        self.listbox.delete(index)
                        self.listbox.insert(index, new_name)
                    rename_dialog.destroy()
                except Exception as e:
                    logging.error(f"save_name 失败: {str(e)}")
                    traceback.print_exc()

            ttkb.Button(rename_dialog, text="确定", command=save_name, bootstyle="primary",
                        style="Custom.TButton").pack(pady=5)
            rename_dialog.protocol("WM_DELETE_WINDOW", rename_dialog.destroy)
        except Exception as e:
            logging.error(f"rename_item 失败: {str(e)}")
            traceback.print_exc()

    def confirm(self):
        try:
            self.result = [(name, path) for name, path in self.pdf_files]
            self.dialog.destroy()
        except Exception as e:
            logging.error(f"confirm 失败: {str(e)}")
            traceback.print_exc()

    def cancel(self):
        try:
            self.result = None
            while not self.parent.progress_queue.empty():
                self.parent.progress_queue.get()
            self.parent.output_text.delete(1.0, tk.END)
            self.dialog.destroy()
        except Exception as e:
            logging.error(f"cancel 失败: {str(e)}")
            traceback.print_exc()

class PDFOrganizerApp:
    def __init__(self, root):
        try:
            self.root = root
            self.root.title("PDF 文件整理工具")
            self.root.geometry("1000x800")
            self.root.minsize(1000, 800)
            logging.info("初始化主窗口")

            # 获取系统的 DPI 缩放比例
            dpi = self.root.winfo_fpixels('1i')  # 获取 1 英寸对应的像素数
            scale_factor = dpi / 96.0  # 假设 96 DPI 为基准（Windows 默认值）
            logging.info(f"系统 DPI: {dpi}, 缩放比例: {scale_factor}")

            # 根据缩放比例调整字体大小，使用平方根平滑缩放
            base_font_size = 10  # 降低基准字体大小
            self.scaled_font_size = int(base_font_size * (scale_factor ** 0.5))  # 保存为实例变量
            logging.info(f"计算出的字体大小: {self.scaled_font_size}")

            # 配置样式以设置字体
            style = Style()
            style.configure("Custom.TButton", font=("Helvetica", self.scaled_font_size, "normal"))
            style.configure("Custom.TLabel", font=("Helvetica", self.scaled_font_size, "normal"))
            style.configure("Custom.TCheckbutton", font=("Helvetica", self.scaled_font_size, "normal"))
            style.configure("Custom.TEntry", font=("Helvetica", self.scaled_font_size, "normal"))

            # 尝试设置窗口图标
            try:
                self.root.iconbitmap("pdf.ico")
            except tk.TclError:
                logging.warning("未能加载 pdf.ico，可能文件不存在或路径错误")

            self.progress_queue = queue.Queue()
            self.logger = logging.getLogger()
            self.poppler_path = self.get_poppler_path()
            self.load_settings()

            # 创建主框架
            main_frame = ttkb.Frame(self.root, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            logging.info("创建主框架")

            # 创建按钮框架
            button_frame = ttkb.Frame(main_frame)
            button_frame.pack(pady=5, fill=tk.X)
            logging.info("创建按钮框架")

            # 创建“选择 PDF 文件”按钮
            self.select_button = ttkb.Button(button_frame, text="选择 PDF 文件", command=self.start_processing, 
                                             bootstyle="primary", width=20, style="Custom.TButton")
            self.select_button.pack(side=tk.LEFT, padx=5)
            logging.info("创建并添加 '选择 PDF 文件' 按钮")

            # 创建“命名和排序设置”按钮
            self.settings_button = ttkb.Button(button_frame, text="命名和排序设置", command=self.open_settings, 
                                               bootstyle="secondary", width=15, style="Custom.TButton")
            self.settings_button.pack(side=tk.LEFT, padx=5)
            logging.info("创建并添加 '命名和排序设置' 按钮")

            # 创建输出文本框（ScrolledText 支持直接设置 font）
            self.output_text = scrolledtext.ScrolledText(main_frame, height=15, width=60, 
                                                         font=("Helvetica", self.scaled_font_size, "normal"))
            self.output_text.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
            logging.info("创建并添加输出文本框")

            # 创建进度标签
            self.progress = ttkb.Label(main_frame, text="进度: 0%", style="Custom.TLabel")
            self.progress.pack(pady=5)
            logging.info("创建并添加进度标签")

            # 居中窗口
            self.center_window(self.root)
            logging.info("居中主窗口")

            # 启动队列检查
            self.check_queue()
            logging.info("启动队列检查")

        except Exception as e:
            logging.error(f"PDFOrganizerApp 初始化失败: {str(e)}")
            traceback.print_exc()

    def center_window(self, window):
        try:
            window.update_idletasks()
            screen_width = window.winfo_screenwidth()
            screen_height = window.winfo_screenheight()
            window_width = window.winfo_width()
            window_height = window.winfo_height()

            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2

            x = max(0, x)
            y = max(0, y)

            window.geometry(f"+{x}+{y}")
        except Exception as e:
            logging.error(f"center_window 失败: {str(e)}")
            traceback.print_exc()

    def load_settings(self):
        try:
            with open("settings.json", "r") as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            self.settings = {
                "use_original_name": True,
                "skip_sorting": False,
                "keep_source_pdf": False
            }
        except Exception as e:
            logging.error(f"load_settings 失败: {str(e)}")
            traceback.print_exc()

    def open_settings(self):
        try:
            self.logger.info("打开设置窗口")
            # 使用保存的 scaled_font_size
            SettingsDialog(self, self.scaled_font_size)
        except Exception as e:
            logging.error(f"open_settings 失败: {str(e)}")
            traceback.print_exc()

    def get_poppler_path(self):
        try:
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            poppler_bin = os.path.join(base_path, "poppler", "Library", "bin")
            if os.path.exists(poppler_bin):
                return poppler_bin
            else:
                self.progress_queue.put("警告: 未找到 Poppler 的 bin 目录，将尝试使用系统 PATH。")
                self.logger.warning("未找到 Poppler 的 bin 目录，将尝试使用系统 PATH")
                return None
        except Exception as e:
            logging.error(f"get_poppler_path 失败: {str(e)}")
            traceback.print_exc()
            return None

    def check_queue(self):
        try:
            while True:
                message = self.progress_queue.get_nowait()
                self.output_text.insert(tk.END, message + "\n")
                self.output_text.see(tk.END)
        except queue.Empty:
            self.root.after(100, self.check_queue)
        except Exception as e:
            logging.error(f"check_queue 失败: {str(e)}")
            traceback.print_exc()

    def pdf_to_jpg(self, pdf_path, output_dir, use_original_name=False, original_name=None):
        self.progress_queue.put(f"正在转换: {os.path.basename(pdf_path)}")
        self.logger.info(f"正在转换: {os.path.basename(pdf_path)}")
        try:
            A4_SIZE = (2480, 3508)
            images = convert_from_path(pdf_path, size=A4_SIZE, dpi=300, 
                                     poppler_path=self.poppler_path)
            
            for i, image in enumerate(images, 1):
                width, height = image.size
                self.progress_queue.put(f"图片 {i} 尺寸: {width}x{height} 像素")

                if use_original_name and original_name:
                    image_name = os.path.splitext(original_name)[0]
                    image_path = os.path.join(output_dir, f"{image_name}_{i}.jpg")
                else:
                    image_path = os.path.join(output_dir, f"{i}.jpg")
                image.save(image_path, "JPEG", quality=95)
                self.progress_queue.put(f"已生成: {os.path.basename(image_path)}")
                self.logger.info(f"已生成: {os.path.basename(image_path)}")
            
            return len(images)
        except MemoryError:
            self.progress_queue.put("内存不足，请尝试处理更小的文件")
            self.logger.error("内存不足")
            self.root.after(0, lambda: messagebox.showerror("内存错误", "内存不足，请尝试处理更小的文件"))
            return 0
        except FileNotFoundError:
            self.progress_queue.put(f"文件 {os.path.basename(pdf_path)} 不存在")
            self.logger.error(f"文件 {os.path.basename(pdf_path)} 不存在")
            self.root.after(0, lambda: messagebox.showerror("文件错误", f"文件 {os.path.basename(pdf_path)} 不存在"))
            return 0
        except Exception as e:
            self.progress_queue.put(f"转换 {os.path.basename(pdf_path)} 失败: {str(e)}")
            self.logger.error(f"转换 {os.path.basename(pdf_path)} 失败: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("错误", f"转换 {os.path.basename(pdf_path)} 失败: {str(e)}"))
            return 0

    def organize_pdfs(self, pdf_files, use_original_name=False):
        try:
            self.output_text.delete(1.0, tk.END)
            
            if not pdf_files:
                self.progress_queue.put("警告: 未选择任何 PDF 文件！")
                self.logger.warning("未选择任何 PDF 文件")
                return
            
            self.progress["text"] = "进度: 0%"
            self.root.update_idletasks()
            
            keep_source = self.settings.get("keep_source_pdf", False)

            success_count = 0
            total_images = 0

            for index, pdf_info in enumerate(pdf_files, 1):
                if isinstance(pdf_info, tuple):
                    pdf_file, pdf_path = pdf_info
                else:
                    pdf_path = pdf_info
                    pdf_file = os.path.basename(pdf_path)
                
                source_dir = os.path.dirname(pdf_path)
                file_name = os.path.splitext(pdf_file)[0]
                
                # 始终创建目标文件夹
                folder_name = f"{index}.{file_name}"
                folder_path = os.path.join(source_dir, folder_name)
                os.makedirs(folder_path, exist_ok=True)
                
                dest_path = os.path.join(folder_path, pdf_file)
                if keep_source:
                    # 保留源文件，复制到目标文件夹
                    shutil.copy2(pdf_path, dest_path)
                    self.progress_queue.put(f"已复制: {pdf_file} -> {folder_name}")
                    self.logger.info(f"已复制: {pdf_file} -> {folder_name}")
                else:
                    # 不保留源文件，移动到目标文件夹
                    shutil.move(pdf_path, dest_path)
                    self.progress_queue.put(f"已移动: {pdf_file} -> {folder_name}")
                    self.logger.info(f"已移动: {pdf_file} -> {folder_name}")
                
                try:
                    num_images = self.pdf_to_jpg(dest_path, folder_path, 
                                               use_original_name=use_original_name, 
                                               original_name=pdf_file)
                    total_images += num_images
                    
                    # 如果保留源文件，删除目标文件夹中的 PDF
                    if keep_source and os.path.exists(dest_path):
                        os.remove(dest_path)
                        self.progress_queue.put(f"已删除目标文件夹中的 PDF: {os.path.basename(dest_path)}")
                        self.logger.info(f"已删除目标文件夹中的 PDF: {os.path.basename(dest_path)}")
                    # 如果不保留源文件，PDF 已在 pdf_to_jpg 中删除
                    elif not keep_source:
                        self.progress_queue.put(f"已删除目标文件夹中的 PDF: {os.path.basename(dest_path)}")
                        self.logger.info(f"已删除目标文件夹中的 PDF: {os.path.basename(dest_path)}")
                    
                    success_count += 1
                except Exception as e:
                    self.progress_queue.put(f"处理 {pdf_file} 失败: {str(e)}")
                    self.logger.error(f"处理 {pdf_file} 失败: {str(e)}")
                
                progress_percentage = int((index / len(pdf_files)) * 100)
                self.progress["text"] = f"进度: {progress_percentage}%"
                self.root.update_idletasks()
            
            self.progress["text"] = "进度: 100%"
            self.progress_queue.put(f"\n处理完成！成功整理 {success_count}/{len(pdf_files)} 个 PDF 文件，生成 {total_images} 张图片。")
            self.logger.info(f"处理完成！成功整理 {success_count}/{len(pdf_files)} 个 PDF 文件，生成 {total_images} 张图片")
            self.root.after(0, lambda: messagebox.showinfo("完成", f"成功整理 {success_count}/{len(pdf_files)} 个 PDF 文件，生成 {total_images} 张图片！"))
        except Exception as e:
            logging.error(f"organize_pdfs 失败: {str(e)}")
            traceback.print_exc()

    def start_processing(self):
        try:
            files = filedialog.askopenfilenames(
                title="选择 PDF 文件",
                filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")]
            )
            if files:
                self.output_text.delete(1.0, tk.END)
                self.progress_queue.put(f"已选择 {len(files)} 个 PDF 文件：")
                self.logger.info(f"已选择 {len(files)} 个 PDF 文件")
                for file in files:
                    self.progress_queue.put(f"{os.path.basename(file)}")
                    self.logger.info(f"选择文件: {os.path.basename(file)}")
                
                if self.settings.get("skip_sorting", False):
                    sorted_files = sorted(files)
                else:
                    # 使用保存的 scaled_font_size
                    dialog = SortRenameDialog(self, files, self.scaled_font_size)
                    self.root.wait_window(dialog.dialog)
                    if dialog.result is None:
                        self.output_text.delete(1.0, tk.END)
                        self.progress_queue.put("已取消手动排序")
                        self.logger.info("已取消手动排序")
                        return
                    sorted_files = dialog.result
                
                use_original_name = self.settings.get("use_original_name", True)
                
                self.select_button.config(state="disabled")
                
                thread = threading.Thread(target=self.organize_pdfs, args=(sorted_files, use_original_name))
                thread.start()
                
                self.root.after(100, lambda: self.check_thread(thread))
            else:
                self.output_text.delete(1.0, tk.END)
        except Exception as e:
            logging.error(f"start_processing 失败: {str(e)}")
            traceback.print_exc()

    def check_thread(self, thread):
        try:
            if thread.is_alive():
                self.root.after(100, lambda: self.check_thread(thread))
            else:
                self.select_button.config(state="normal")
        except Exception as e:
            logging.error(f"check_thread 失败: {str(e)}")
            traceback.print_exc()

if __name__ == "__main__":
    try:
        # 尝试使用 ttkbootstrap 的 litera 主题
        root = ttkb.Window(themename="litera")
        
        app = PDFOrganizerApp(root)
        root.mainloop()
    except Exception as e:
        logging.error(f"程序启动失败: {str(e)}")
        traceback.print_exc()
        input("按任意键退出...")  # 防止控制台立即关闭