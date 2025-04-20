import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, Toplevel, Listbox, Entry
from pdf2image import convert_from_path
import threading
import queue
import sys

class SortRenameDialog:
    def __init__(self, parent, pdf_files):
        self.parent = parent
        self.pdf_files = [(os.path.basename(f), f) for f in pdf_files]
        self.result = None

        self.dialog = Toplevel(parent)
        self.dialog.title("排序和重命名 PDF 文件")
        self.dialog.geometry("800x800")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 设置窗口位置，靠近主窗口
        self.center_window(self.dialog, self.parent)

        self.listbox = Listbox(self.dialog, selectmode=tk.SINGLE, width=50, height=15)
        self.listbox.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        for name, _ in self.pdf_files:
            self.listbox.insert(tk.END, name)

        self.listbox.bind("<B1-Motion>", self.on_drag)
        self.listbox.bind("<Button-1>", self.start_drag)
        self.listbox.bind("<Double-1>", self.rename_item)

        button_frame = tk.Frame(self.dialog)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="确定", command=self.confirm).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="取消", command=self.cancel).pack(side=tk.LEFT, padx=5)

        self.drag_start_index = None

    def center_window(self, window, parent):
        """将窗口定位在父窗口附近"""
        parent.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        window_width = window.winfo_reqwidth()
        window_height = window.winfo_reqheight()

        x = parent_x + (parent_width - window_width) // 2 + 20
        y = parent_y + (parent_height - window_height) // 2 + 20

        x = max(0, x)
        y = max(0, y)

        window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def start_drag(self, event):
        self.drag_start_index = self.listbox.nearest(event.y)

    def on_drag(self, event):
        if self.drag_start_index is None:
            return
        current_index = self.listbox.nearest(event.y)
        if current_index != self.drag_start_index and 0 <= current_index < len(self.pdf_files):
            name, path = self.pdf_files.pop(self.drag_start_index)
            self.pdf_files.insert(current_index, (name, path))
            self.listbox.delete(self.drag_start_index)
            self.listbox.insert(current_index, name)
            self.drag_start_index = current_index

    def rename_item(self, event):
        index = self.listbox.nearest(event.y)
        if index < 0:
            return
        current_name, path = self.pdf_files[index]

        rename_dialog = Toplevel(self.dialog)
        rename_dialog.title("重命名")
        rename_dialog.geometry("600x150")
        rename_dialog.transient(self.dialog)
        rename_dialog.grab_set()

        self.center_window(rename_dialog, self.dialog)

        tk.Label(rename_dialog, text="输入新文件名（不含扩展名）：").pack(pady=5)
        entry = Entry(rename_dialog, width=40)
        entry.insert(0, os.path.splitext(current_name)[0])
        entry.pack(pady=5)

        def save_name():
            new_name = entry.get().strip()
            if new_name:
                new_name = f"{new_name}.pdf"
                self.pdf_files[index] = (new_name, path)
                self.listbox.delete(index)
                self.listbox.insert(index, new_name)
            rename_dialog.destroy()

        tk.Button(rename_dialog, text="确定", command=save_name).pack(pady=5)
        rename_dialog.protocol("WM_DELETE_WINDOW", rename_dialog.destroy)

    def confirm(self):
        self.result = [(name, path) for name, path in self.pdf_files]  # 返回 (文件名, 路径) 对
        self.dialog.destroy()

    def cancel(self):
        self.result = None
        self.dialog.destroy()

class PDFOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF 文件整理工具")
        self.root.geometry("800x800")

        self.progress_queue = queue.Queue()
        self.poppler_path = self.get_poppler_path()

        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        self.select_button = tk.Button(button_frame, text="选择 PDF 文件", 
                                      command=self.start_processing,
                                      width=20, font=("Arial", 12))
        self.select_button.pack()

        self.output_text = scrolledtext.ScrolledText(self.root, height=15, width=60, 
                                                    font=("Arial", 10))
        self.output_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.root.eval('tk::PlaceWindow . center')
        self.check_queue()

    def get_poppler_path(self):
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        poppler_bin = os.path.join(base_path, "poppler", "Library", "bin")
        if os.path.exists(poppler_bin):
            return poppler_bin
        else:
            self.progress_queue.put("警告: 未找到 Poppler 的 bin 目录，将尝试使用系统 PATH。")
            return None

    def check_queue(self):
        try:
            while True:
                message = self.progress_queue.get_nowait()
                self.output_text.insert(tk.END, message + "\n")
                self.output_text.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(100, self.check_queue)

    def pdf_to_jpg(self, pdf_path, output_dir, use_original_name=False, original_name=None):
        self.progress_queue.put(f"正在转换: {os.path.basename(pdf_path)}")
        try:
            images = convert_from_path(pdf_path, dpi=300, poppler_path=self.poppler_path)
            for i, image in enumerate(images, 1):
                if use_original_name and original_name:
                    # 使用原文件名（去掉 .pdf 扩展名）
                    image_name = os.path.splitext(original_name)[0]
                    image_path = os.path.join(output_dir, f"{image_name}.jpg")
                else:
                    # 使用页码命名
                    image_path = os.path.join(output_dir, f"{i}.jpg")
                image.save(image_path, "JPEG", quality=95)
                self.progress_queue.put(f"已生成: {os.path.basename(image_path)}")
            print("print("")")
            if images:
                os.remove(pdf_path)
                self.progress_queue.put(f"已删除原始 PDF: {os.path.basename(pdf_path)}")
            
            return len(images)
        except Exception as e:
            self.progress_queue.put(f"转换 {os.path.basename(pdf_path)} 失败: {str(e)}")
            return 0

    def organize_pdfs(self, pdf_files, use_original_name=False):
        self.output_text.delete(1.0, tk.END)
        
        if not pdf_files:
            self.progress_queue.put("警告: 未选择任何 PDF 文件！")
            return
        
        success_count = 0
        total_images = 0
        
        for index, pdf_info in enumerate(pdf_files, 1):
            # pdf_info 可能是 (文件名, 路径) 或 路径
            if isinstance(pdf_info, tuple):
                pdf_file, pdf_path = pdf_info
            else:
                pdf_path = pdf_info
                pdf_file = os.path.basename(pdf_path)
            
            source_dir = os.path.dirname(pdf_path)
            file_name = os.path.splitext(pdf_file)[0]
            
            folder_name = f"{index}.{file_name}"
            folder_path = os.path.join(source_dir, folder_name)
            
            try:
                os.makedirs(folder_path, exist_ok=True)
                dest_path = os.path.join(folder_path, pdf_file)
                shutil.move(pdf_path, dest_path)
                self.progress_queue.put(f"已处理: {pdf_file} -> {folder_name}")
                
                num_images = self.pdf_to_jpg(dest_path, folder_path, 
                                           use_original_name=use_original_name, 
                                           original_name=pdf_file)
                total_images += num_images
                
                success_count += 1
            except Exception as e:
                self.progress_queue.put(f"处理 {pdf_file} 失败: {str(e)}")
        
        self.progress_queue.put(f"\n处理完成！成功整理 {success_count}/{len(pdf_files)} 个 PDF 文件，生成 {total_images} 张图片。")
        self.root.after(0, lambda: messagebox.showinfo("完成", f"成功整理 {success_count}/{len(pdf_files)} 个 PDF 文件，生成 {total_images} 张图片！"))

    def start_processing(self):
        files = filedialog.askopenfilenames(
            title="选择 PDF 文件",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")]
        )
        if files:
            self.output_text.delete(1.0, tk.END)
            self.progress_queue.put(f"已选择 {len(files)} 个 PDF 文件：")
            for file in files:
                self.progress_queue.put(f"{os.path.basename(file)}")
            
            response = messagebox.askyesno("手动排序", "是否需要手动排序和重命名 PDF 文件？")
            if response:
                dialog = SortRenameDialog(self.root, files)
                self.root.wait_window(dialog.dialog)
                if dialog.result is None:
                    self.progress_queue.put("已取消手动排序")
                    return
                sorted_files = dialog.result  # 包含 (文件名, 路径) 对
            else:
                sorted_files = sorted(files)  # 仅包含路径
            
            # 统一询问图片命名方式
            use_original_name = messagebox.askyesno("图片命名", "是否使用原文件名作为图片名？（选择‘否’将使用页码命名）")
            
            self.select_button.config(state="disabled")
            
            thread = threading.Thread(target=self.organize_pdfs, args=(sorted_files, use_original_name))
            thread.start()
            
            self.root.after(100, lambda: self.check_thread(thread))

    def check_thread(self, thread):
        if thread.is_alive():
            self.root.after(100, lambda: self.check_thread(thread))
        else:
            self.select_button.config(state="normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFOrganizerApp(root)
    root.mainloop()