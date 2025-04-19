import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from pdf2image import convert_from_path
import threading
import queue
import sys

class PDFOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF 文件整理工具")
        self.root.geometry("600x400")

        # 线程安全的队列，用于传递进度信息
        self.progress_queue = queue.Queue()

        # 动态确定 Poppler 路径
        self.poppler_path = self.get_poppler_path()

        # 按钮框架
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        self.select_button = tk.Button(button_frame, text="选择 PDF 文件", 
                                      command=self.start_processing,
                                      width=20, font=("Arial", 12))
        self.select_button.pack()

        # 输出文本框
        self.output_text = scrolledtext.ScrolledText(self.root, height=15, width=60, 
                                                    font=("Arial", 10))
        self.output_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # 窗口居中
        self.root.eval('tk::PlaceWindow . center')

        # 定期检查队列以更新界面
        self.check_queue()

    def get_poppler_path(self):
        """动态确定 Poppler 的 bin 目录路径"""
        # 如果是打包后的 exe，获取 exe 所在目录
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        # 假设 Poppler 的 bin 目录在程序目录下的 poppler 文件夹中
        poppler_bin = os.path.join(base_path, "poppler", "Library", "bin")
        if os.path.exists(poppler_bin):
            return poppler_bin
        else:
            # 如果未找到，尝试使用系统 PATH
            self.progress_queue.put("警告: 未找到 Poppler 的 bin 目录，将尝试使用系统 PATH。")
            return None

    def check_queue(self):
        """定期检查队列，更新界面"""
        try:
            while True:
                message = self.progress_queue.get_nowait()
                self.output_text.insert(tk.END, message + "\n")
                self.output_text.see(tk.END)  # 自动滚动到最新消息
        except queue.Empty:
            pass
        # 每 100 毫秒检查一次队列
        self.root.after(100, self.check_queue)

    def pdf_to_jpg(self, pdf_path, output_dir):
        """将 PDF 转换为超高清 JPG 图片，并按页码命名，转换成功后删除 PDF"""
        self.progress_queue.put(f"正在转换: {os.path.basename(pdf_path)}")
        try:
            images = convert_from_path(pdf_path, dpi=300, poppler_path=self.poppler_path)
            for i, image in enumerate(images, 1):
                image_path = os.path.join(output_dir, f"{i}.jpg")
                image.save(image_path, "JPEG", quality=95)
                self.progress_queue.put(f"已生成: {os.path.basename(image_path)}")
            
            # 如果成功生成了图片，删除原始 PDF 文件
            if images:
                os.remove(pdf_path)
                self.progress_queue.put(f"已删除原始 PDF: {os.path.basename(pdf_path)}")
            
            return len(images)
        except Exception as e:
            self.progress_queue.put(f"转换 {os.path.basename(pdf_path)} 失败: {str(e)}")
            return 0

    def organize_pdfs(self, pdf_files):
        """整理 PDF 文件到带编号的文件夹，并转换为 JPG"""
        self.output_text.delete(1.0, tk.END)  # 清空输出框
        
        if not pdf_files:
            self.progress_queue.put("警告: 未选择任何 PDF 文件！")
            return
        
        # 按文件名排序
        pdf_files = sorted(pdf_files)
        success_count = 0
        total_images = 0
        
        for index, pdf_path in enumerate(pdf_files, 1):
            # 获取文件名和所在目录
            source_dir = os.path.dirname(pdf_path)
            pdf_file = os.path.basename(pdf_path)
            file_name = os.path.splitext(pdf_file)[0]
            
            # 创建新文件夹名（带序号）
            folder_name = f"{index}.{file_name}"
            folder_path = os.path.join(source_dir, folder_name)
            
            try:
                os.makedirs(folder_path, exist_ok=True)
                dest_path = os.path.join(folder_path, pdf_file)
                shutil.move(pdf_path, dest_path)
                self.progress_queue.put(f"已处理: {pdf_file} -> {folder_name}")
                
                # 将 PDF 转换为 JPG，并删除 PDF
                num_images = self.pdf_to_jpg(dest_path, folder_path)
                total_images += num_images
                
                success_count += 1
            except Exception as e:
                self.progress_queue.put(f"处理 {pdf_file} 失败: {str(e)}")
        
        self.progress_queue.put(f"\n处理完成！成功整理 {success_count}/{len(pdf_files)} 个 PDF 文件，生成 {total_images} 张图片。")
        # 在主线程中弹出消息框
        self.root.after(0, lambda: messagebox.showinfo("完成", f"成功整理 {success_count}/{len(pdf_files)} 个 PDF 文件，生成 {total_images} 张图片！"))

    def start_processing(self):
        """选择文件并启动处理线程"""
        files = filedialog.askopenfilenames(
            title="选择 PDF 文件",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")]
        )
        if files:
            self.output_text.delete(1.0, tk.END)
            self.progress_queue.put(f"已选择 {len(files)} 个 PDF 文件：")
            for file in files:
                self.progress_queue.put(f"{os.path.basename(file)}")
            
            # 禁用按钮，防止重复点击
            self.select_button.config(state="disabled")
            
            # 启动处理线程
            thread = threading.Thread(target=self.organize_pdfs, args=(files,))
            thread.start()
            
            # 检查线程是否完成，完成后启用按钮
            self.root.after(100, lambda: self.check_thread(thread))

    def check_thread(self, thread):
        """检查处理线程是否完成"""
        if thread.is_alive():
            self.root.after(100, lambda: self.check_thread(thread))
        else:
            self.select_button.config(state="normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFOrganizerApp(root)
    root.mainloop()