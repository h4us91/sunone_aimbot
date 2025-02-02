import tkinter as tk
from tkinter import Canvas
import threading, queue
from logic.config_watcher import cfg

class Overlay(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.name = "Overlay"
        self.width = cfg.detection_window_width
        self.height = cfg.detection_window_height
        self.queue = queue.Queue()
        self._running = True
        self.square_id = None
        self.frame_skip_counter = 0
        self.root = None

    def run(self):
        if cfg.show_overlay:
            self.root = tk.Tk()
            self.root.overrideredirect(True)
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width - self.width) // 2
            y = (screen_height - self.height) // 2
            self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
            self.root.attributes('-topmost', True)
            self.root.attributes('-transparentcolor', 'black')
            self.canvas = Canvas(self.root, bg='black', highlightthickness=0, cursor="none")
            self.canvas.pack(fill=tk.BOTH, expand=True)

            # Blockiere alle Events:
            for widget in (self.root, self.canvas):
                widget.bind("<Button-1>", lambda e: "break")
                widget.bind("<Button-2>", lambda e: "break")
                widget.bind("<Button-3>", lambda e: "break")
                widget.bind("<Motion>", lambda e: "break")
                widget.bind("<Key>", lambda e: "break")
                widget.bind("<Enter>", lambda e: "break")
                widget.bind("<Leave>", lambda e: "break")
                widget.bind("<FocusIn>", lambda e: "break")
                widget.bind("<FocusOut>", lambda e: "break")

            if cfg.overlay_show_borders:
                if cfg.circle_capture:
                    self.square_id = self.canvas.create_oval(0, 0, self.width, self.height, outline='red', width=2)
                else:
                    self.square_id = self.canvas.create_rectangle(0, 0, self.width, self.height, outline='red', width=2)
            self.process_queue()
            self.root.mainloop()

    def process_queue(self):
        if not self._running:
            return
        self.frame_skip_counter += 1
        if self.frame_skip_counter % 3 == 0:
            if not self.queue.empty():
                for item in self.canvas.find_all():
                    if item != self.square_id:
                        self.canvas.delete(item)
                while not self.queue.empty():
                    command, args = self.queue.get()
                    command(*args)
            else:
                for item in self.canvas.find_all():
                    if item != self.square_id:
                        self.canvas.delete(item)
        if self.root:
            self.root.after(2, self.process_queue)

    def draw_square(self, x1, y1, x2, y2, color='white', size=1):
        self.queue.put((self._draw_square, (x1, y1, x2, y2, color, size)))
    def _draw_square(self, x1, y1, x2, y2, color, size):
        self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=size)

    def draw_oval(self, x1, y1, x2, y2, color='white', size=1):
        self.queue.put((self._draw_oval, (x1, y1, x2, y2, color, size)))
    def _draw_oval(self, x1, y1, x2, y2, color, size):
        self.canvas.create_oval(x1, y1, x2, y2, outline=color, width=size)

    def draw_line(self, x1, y1, x2, y2, color='white', size=1):
        self.queue.put((self._draw_line, (x1, y1, x2, y2, color, size)))
    def _draw_line(self, x1, y1, x2, y2, color, size):
        self.canvas.create_line(x1, y1, x2, y2, fill=color, width=size)

    def draw_point(self, x, y, color='white', size=1):
        self.queue.put((self._draw_point, (x, y, color, size)))
    def _draw_point(self, x, y, color, size):
        self.canvas.create_oval(x-size, y-size, x+size, y+size, fill=color, outline=color)

    def draw_text(self, x, y, text, size=12, color='white'):
        self.queue.put((self._draw_text, (x, y, text, size, color)))
    def _draw_text(self, x, y, text, size, color):
        self.canvas.create_text(x, y, text=text, font=('Arial', size), fill=color)

    def stop(self):
        self._running = False
        if self.root:
            self.root.quit()
            #self.root.destroy()
            self.root = None


# Globale Instanz, ähnlich wie bei Visuals:
overlay = Overlay()
