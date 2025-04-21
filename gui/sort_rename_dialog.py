import os
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import Listbox, Canvas, Toplevel, Entry
from collections import OrderedDict  # 新增导入
import ttkbootstrap as ttkb
from ttkbootstrap.style import Style
from pdf2image import convert_from_path
from PIL import Image, ImageTk
from threading import Thread
from gui.base_dialog import BaseDialog
from config import WINDOW_SIZES, DEFAULT_FONT, PREVIEW_TEXT, PREVIEW_TEXT_COLOR, PREVIEW_ERROR_COLOR, LISTBOX_WIDTH, LISTBOX_HEIGHT, LISTBOX_SELECT_BG, LISTBOX_SELECT_FG, PREVIEW_DPI
from utils import log_error
import logging

class SortRenameDialog(BaseDialog):
    def __init__(self, parent, pdf_files, scaled_font_size):
        super().__init__(parent, "排序和重命名 PDF 文件", WINDOW_SIZES["sort_rename"], scaled_font_size)

        try:
            self.pdf_files = [(os.path.basename(f), f) for f in pdf_files]
            self.result = None
            self.preview_thread = None
            self.max_cache_size = 20  # 设置缓存大小为20个图
            self.preview_cache = OrderedDict()  # 使用OrderedDict实现LRU缓存

            self.paned_window = ttk.PanedWindow(self.dialog, orient=tk.HORIZONTAL)
            self.paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            listbox_frame = ttk.Frame(self.paned_window)
            self.paned_window.add(listbox_frame, weight=1)

            self.listbox = Listbox(listbox_frame, selectmode=tk.SINGLE, width=LISTBOX_WIDTH, height=LISTBOX_HEIGHT,
                                   font=(DEFAULT_FONT, self.scaled_font_size, "normal"), 
                                   selectbackground=LISTBOX_SELECT_BG, selectforeground=LISTBOX_SELECT_FG)
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
            self.paned_window.sashpos(0, int(WINDOW_SIZES["sort_rename"].split("x")[0]) // 2)

            self.preview_canvas = Canvas(canvas_frame, bg="white")
            self.preview_canvas.pack(fill=tk.BOTH, expand=True)
            self.preview_canvas.update_idletasks()
            self.canvas_width = max(1, self.preview_canvas.winfo_width())
            self.canvas_height = max(1, self.preview_canvas.winfo_height())
            self.preview_canvas.create_text(50, 50, text=PREVIEW_TEXT, fill=PREVIEW_TEXT_COLOR, 
                                            font=(DEFAULT_FONT, self.scaled_font_size, "normal"))
            
            self.paned_window.bind("<Configure>", self.on_paned_resize)

            button_frame = ttkb.Frame(self.dialog)
            button_frame.pack(fill=tk.X, pady=10, side=tk.BOTTOM)
            ttkb.Button(button_frame, text="确定", command=self.confirm, bootstyle="success",
                        style="Custom.TButton").pack(side=tk.LEFT, padx=20)
            ttkb.Button(button_frame, text="取消", command=self.cancel, bootstyle="danger",
                        style="Custom.TButton").pack(side=tk.RIGHT, padx=20)

            self.drag_start_index = None
            self.current_image = None

            self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)

        except Exception as e:
            log_error(f"SortRenameDialog 初始化失败: {str(e)}")

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
            log_error(f"on_paned_resize 失败: {str(e)}")

    def start_drag(self, event):
        try:
            self.drag_start_index = self.listbox.nearest(event.y)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.drag_start_index)
            self.listbox.activate(self.drag_start_index)
        except Exception as e:
            log_error(f"start_drag 失败: {str(e)}")

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
            log_error(f"on_drag 失败: {str(e)}")

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
            log_error(f"on_drag_release 失败: {str(e)}")

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
            log_error(f"show_preview 失败: {str(e)}")

    def load_preview(self, pdf_path):
        try:
            if pdf_path in self.preview_cache:
                self.preview_image = self.preview_cache[pdf_path]
                self.preview_cache.move_to_end(pdf_path)
                self.parent.root.after(0, self.update_preview)
                return

            images = convert_from_path(pdf_path, dpi=PREVIEW_DPI, poppler_path=self.parent.poppler_path)
            image = images[0]
            self.current_image = image

            max_width = self.canvas_width - 20
            max_height = self.canvas_height - 20
            if image.width <= 0 or image.height <= 0:
                self.parent.root.after(0, lambda: self.update_preview_error("图像尺寸无效"))
                logging.error("图像尺寸无效: width=%d, height=%d" % (image.width, image.height))
                return

            image_ratio = image.width / image.height
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

            new_width = max(1, new_width)
            new_height = max(1, new_height)

            image = image.resize((new_width, new_height), Image.LANCZOS)
            self.preview_image = ImageTk.PhotoImage(image)
            self.preview_cache[pdf_path] = self.preview_image
            self.preview_cache.move_to_end(pdf_path)
            if len(self.preview_cache) > self.max_cache_size:
                self.preview_cache.popitem(last=False)
            self.parent.root.after(0, self.update_preview)
        except Exception as e:
            self.parent.root.after(0, lambda: self.update_preview_error(str(e)))
            log_error(f"load_preview 失败: {str(e)}")

    def update_preview(self):
        try:
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(self.canvas_width // 2, self.canvas_height // 2, image=self.preview_image)
        except Exception as e:
            log_error(f"update_preview 失败: {str(e)}")

    def update_preview_error(self, error):
        try:
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(self.canvas_width // 2, self.canvas_height // 2, text=f"预览失败: {error}", 
                                            fill=PREVIEW_ERROR_COLOR, font=(DEFAULT_FONT, self.scaled_font_size, "normal"))
        except Exception as e:
            log_error(f"update_preview_error 失败: {str(e)}")

    def rename_item(self, event):
        try:
            index = self.listbox.nearest(event.y)
            if index < 0:
                return
            current_name, path = self.pdf_files[index]

            rename_dialog = ttkb.Toplevel(self.dialog)
            rename_dialog.title("重命名")
            rename_dialog.geometry(WINDOW_SIZES["rename"])
            rename_dialog.minsize(*map(int, WINDOW_SIZES["rename"].split("x")))
            rename_dialog.transient(self.dialog)
            rename_dialog.grab_set()

            style = Style()
            style.configure("Custom.TLabel", font=(DEFAULT_FONT, self.scaled_font_size, "normal"))
            style.configure("Custom.TEntry", font=(DEFAULT_FONT, self.scaled_font_size, "normal"))
            style.configure("Custom.TButton", font=(DEFAULT_FONT, self.scaled_font_size, "normal"))

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
                    log_error(f"save_name 失败: {str(e)}")

            ttkb.Button(rename_dialog, text="确定", command=save_name, bootstyle="primary",
                        style="Custom.TButton").pack(pady=5)
            rename_dialog.protocol("WM_DELETE_WINDOW", rename_dialog.destroy)
        except Exception as e:
            log_error(f"rename_item 失败: {str(e)}")

    def confirm(self):
        try:
            self.result = [(name, path) for name, path in self.pdf_files]
            self.destroy()
        except Exception as e:
            log_error(f"confirm 失败: {str(e)}")

    def cancel(self):
        try:
            self.result = None
            while not self.parent.progress_queue.empty():
                self.parent.progress_queue.get()
            self.parent.output_text.delete(1.0, tk.END)
            self.destroy()
        except Exception as e:
            log_error(f"cancel 失败: {str(e)}")