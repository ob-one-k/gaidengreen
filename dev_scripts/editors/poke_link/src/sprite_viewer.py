import logging
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import os

# Configure logging
tk_logger = logging.getLogger(__name__)
tk_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
tk_logger.addHandler(handler)

class PixelArtViewer(tk.Tk):
    SUPPORTED_EXT = ('.png', '.gif', '.bmp', '.jpg', '.jpeg', '.tga')
    # GraphicsGale-style canvas background
    GGP_BG = "#78C1A3"

    def __init__(self):
        super().__init__()
        self.title("Pixel Art Viewer")
        self.geometry("800x600")

        self.original_image = None
        self.image_paths = []
        self.current_index = 0

        # Zoom bounds
        self.zoom_level = 1
        self.min_zoom = 1
        self.max_zoom = 12

        self._create_widgets()
        self._bind_events()

    def _create_widgets(self):
        self.canvas = tk.Canvas(self, bg=self.GGP_BG, highlightthickness=0)
        self.h_scroll = tk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.v_scroll = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.h_scroll.grid(row=1, column=0, sticky="ew")
        self.v_scroll.grid(row=0, column=1, sticky="ns")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        ctrl = tk.Frame(self)
        ctrl.grid(row=2, column=0, columnspan=2, pady=5)
        tk.Button(ctrl, text="◀ Prev", command=self.prev_image).pack(side=tk.LEFT, padx=10)
        tk.Button(ctrl, text="Next ▶", command=self.next_image).pack(side=tk.RIGHT, padx=10)

        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Image…", command=self.open_image)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menubar)

    def _bind_events(self):
        self.canvas.bind('<MouseWheel>', self._on_mouse_wheel)
        self.bind('+', lambda e: self.zoom(1))
        self.bind('-', lambda e: self.zoom(-1))
        self.bind('<Left>', lambda e: self.prev_image())
        self.bind('<Right>', lambda e: self.next_image())

    def open_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*%s" % " *".join(self.SUPPORTED_EXT))]
        )
        if not path:
            return

        norm_path = os.path.normpath(path)
        folder = os.path.dirname(norm_path)
        files = sorted(f for f in os.listdir(folder) if f.lower().endswith(self.SUPPORTED_EXT))
        self.image_paths = [os.path.normpath(os.path.join(folder, f)) for f in files]

        try:
            self.current_index = self.image_paths.index(norm_path)
        except ValueError:
            messagebox.showerror("Error", f"File not found in directory:\n{norm_path}")
            return

        self.zoom_level = 1
        self._load_image()

    def _load_image(self):
        if not self.image_paths:
            return
        img_path = self.image_paths[self.current_index]
        try:
            self.original_image = Image.open(img_path)
            tk_logger.info(f"Loaded: {img_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Cannot open image:\n{e}")
            return

        # Update title bar with basename
        self.title(f"Pixel Art Viewer – {os.path.basename(img_path)}")
        self._update_viewer()

    def _update_viewer(self):
        if self.original_image is None:
            return

        w, h = self.original_image.size
        scaled = self.original_image.resize((w * self.zoom_level, h * self.zoom_level), Image.NEAREST)
        self.photo = ImageTk.PhotoImage(scaled)

        self.canvas.delete("IMG")
        scaled_w, scaled_h = scaled.size
        self.canvas.config(scrollregion=(0, 0, scaled_w, scaled_h))

        # Center image in visible canvas
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        x = max((cw - scaled_w) // 2, 0)
        y = max((ch - scaled_h) // 2, 0)
        self.canvas.create_image(x, y, anchor=tk.NW, image=self.photo, tags="IMG")

        # Reset scroll to top-left
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

    def zoom(self, delta):
        new_zoom = self.zoom_level + delta
        if new_zoom < self.min_zoom:
            messagebox.showinfo("Zoom Limit", "Already at minimum zoom (1×).")
            return
        if new_zoom > self.max_zoom:
            messagebox.showinfo("Zoom Limit", f"Already at maximum zoom ({self.max_zoom}×).")
            return
        self.zoom_level = new_zoom
        self._update_viewer()

    def _on_mouse_wheel(self, event):
        self.zoom(1 if event.delta > 0 else -1)

    def prev_image(self):
        if not self.image_paths:
            return
        self.current_index = (self.current_index - 1) % len(self.image_paths)
        self._load_image()

    def next_image(self):
        if not self.image_paths:
            return
        self.current_index = (self.current_index + 1) % len(self.image_paths)
        self._load_image()

if __name__ == "__main__":
    app = PixelArtViewer()
    app.mainloop()
