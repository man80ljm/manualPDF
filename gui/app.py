import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import ttkbootstrap as ttkb
from ttkbootstrap.style import Style
from pdf2image import convert_from_path
import threading
import queue
import json
import logging
from config import WINDOW_SIZES, DEFAULT_FONT, BASE_FONT_SIZE, DPI_BASE, A4_SIZE, PDF_DPI, JPEG_QUALITY
from utils import center_window, get_poppler_path, log_error
from gui.settings_dialog import SettingsDialog
from gui.sort_rename_dialog import SortRenameDialog

class PDFOrganizerApp:
    def __init__(self, root):
        try:
            self.root = root
            self.root.title("PDF 文件整理工具")
            self.root.geometry(WINDOW_SIZES["main"])
            self.root.minsize(*map(int, WINDOW_SIZES["main"].split("x")))
            logging.info("初始化主窗口")

            # 获取系统的DPI缩放比例
            dpi = self.root.winfo_fpixels('1i')
            scale_factor = dpi / DPI_BASE
            logging.info(f"系统 DPI: {dpi}, 缩放比例: {scale_factor}")

            # 根据缩放比例调整字体大小，使用平方根平滑缩放
            self.scaled_font_size = int(BASE_FONT_SIZE * (scale_factor ** 0.5))
            logging.info(f"计算出的字体大小: {self.scaled_font_size}")

            # 配置样式以设置字体
            style = Style()
            style.configure("Custom.TButton", font=(DEFAULT_FONT, self.scaled_font_size, "normal"))
            style.configure("Custom.TLabel", font=(DEFAULT_FONT, self.scaled_font_size, "normal"))
            style.configure("Custom.TCheckbutton", font=(DEFAULT_FONT, self.scaled_font_size, "normal"))
            style.configure("Custom.TEntry", font=(DEFAULT_FONT, self.scaled_font_size, "normal"))

            # 尝试设置窗口图标
            try:
                self.root.iconbitmap(os.path.join("assets", "pdf.ico"))
            except tk.TclError:
                logging.warning("未能加载 pdf.ico，可能文件不存在或路径错误")

            self.progress_queue = queue.Queue()
            self.logger = logging.getLogger()
            self.poppler_path = get_poppler_path()
            if self.poppler_path is None:
                self.progress_queue.put("警告: 未找到 Poppler 的 bin 目录，将尝试使用系统 PATH。")
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

            # 创建输出文本框
            self.output_text = scrolledtext.ScrolledText(main_frame, height=15, width=60, 
                                                         font=(DEFAULT_FONT, self.scaled_font_size, "normal"))
            self.output_text.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
            logging.info("创建并添加输出文本框")

            # 创建进度标签
            self.progress = ttkb.Label(main_frame, text="进度: 0%", style="Custom.TLabel")
            self.progress.pack(pady=5)
            logging.info("创建并添加进度标签")

            # 居中窗口
            center_window(self.root)
            logging.info("居中主窗口")

            # 启动队列检查
            self.check_queue()
            logging.info("启动队列检查")

        except Exception as e:
            log_error(f"PDFOrganizerApp 初始化失败: {str(e)}")

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
            log_error(f"load_settings 失败: {str(e)}")

    def open_settings(self):
        try:
            self.logger.info("打开设置窗口")
            SettingsDialog(self, self.scaled_font_size)
        except Exception as e:
            log_error(f"open_settings 失败: {str(e)}")

    def check_queue(self):
        try:
            while True:
                message = self.progress_queue.get_nowait()
                self.output_text.insert(tk.END, message + "\n")
                self.output_text.see(tk.END)
        except queue.Empty:
            self.root.after(100, self.check_queue)
        except Exception as e:
            log_error(f"check_queue 失败: {str(e)}")

    def pdf_to_jpg(self, pdf_path, output_dir, use_original_name=False, original_name=None):
        self.progress_queue.put(f"正在转换: {os.path.basename(pdf_path)}")
        self.logger.info(f"正在转换: {os.path.basename(pdf_path)}")
        try:
            images = convert_from_path(pdf_path, size=A4_SIZE, dpi=PDF_DPI, poppler_path=self.poppler_path)
            
            for i, image in enumerate(images, 1):
                width, height = image.size
                self.progress_queue.put(f"图片 {i} 尺寸: {width}x{height} 像素")

                if use_original_name and original_name:
                    image_name = os.path.splitext(original_name)[0]
                    image_path = os.path.join(output_dir, f"{image_name}_{i}.jpg")
                else:
                    image_path = os.path.join(output_dir, f"{i}.jpg")
                image.save(image_path, "JPEG", quality=JPEG_QUALITY)
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
                    shutil.copy2(pdf_path, dest_path)
                    self.progress_queue.put(f"已复制: {pdf_file} -> {folder_name}")
                    self.logger.info(f"已复制: {pdf_file} -> {folder_name}")
                else:
                    shutil.move(pdf_path, dest_path)
                    self.progress_queue.put(f"已移动: {pdf_file} -> {folder_name}")
                    self.logger.info(f"已移动: {pdf_file} -> {folder_name}")
                
                try:
                    num_images = self.pdf_to_jpg(dest_path, folder_path, 
                                               use_original_name=use_original_name, 
                                               original_name=pdf_file)
                    total_images += num_images
                    
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                        self.progress_queue.put(f"已删除目标文件夹中的 PDF: {os.path.basename(dest_path)}")
                        self.logger.info(f"已删除目标文件夹中的 PDF: {os.path.basename(dest_path)}")
                    else:
                        self.logger.warning(f"目标文件夹中的 PDF 文件不存在: {dest_path}")
                    
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
            log_error(f"organize_pdfs 失败: {str(e)}")

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
            log_error(f"start_processing 失败: {str(e)}")

    def check_thread(self, thread):
        try:
            if thread.is_alive():
                self.root.after(100, lambda: self.check_thread(thread))
            else:
                self.select_button.config(state="normal")
        except Exception as e:
            log_error(f"check_thread 失败: {str(e)}")