# -*- coding: utf-8 -*-
"""
Crosshair Overlay — overlay crosshair for games (Crosshair X alternative)
Cross-platform: Windows and macOS support.

Installation:
    Windows: pip install keyboard pywin32 pystray pillow
    macOS: pip install pynput pystray pillow

Run:
    python main.py

Settings window opens at startup.
Hotkeys (work even when game is focused):
    F5  — show/hide crosshair
    F6  — toggle move mode (drag crosshair with mouse)
    F10 — show/raise settings window
    F9  — save and exit
"""

import json
import os
import sys
import tkinter as tk
from tkinter import ttk, colorchooser

PLATFORM = sys.platform
IS_WINDOWS = PLATFORM == "win32"
IS_MACOS = PLATFORM == "darwin"

if IS_WINDOWS:
    import ctypes
    try:
        import keyboard
    except ImportError:
        print("Required 'keyboard' library. Install: pip install keyboard")
        sys.exit(1)
elif IS_MACOS:
    try:
        from pynput import keyboard as pynput_keyboard
    except ImportError:
        print("macOS requires 'pynput' library. Install: pip install pynput")
        sys.exit(1)

try:
    import pystray
    from PIL import Image
except ImportError:
    print("Required 'pystray' and 'Pillow' libraries. Install: pip install pystray pillow")
    sys.exit(1)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# ---------- Platform-specific helpers ----------
if IS_WINDOWS:
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_TOOLWINDOW = 0x00000080
    user32 = ctypes.windll.user32

    def make_click_through(hwnd, enable=True):
        styles = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if enable:
            styles |= WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW
        else:
            styles &= ~WS_EX_TRANSPARENT
            styles |= WS_EX_LAYERED | WS_EX_TOOLWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, styles)

elif IS_MACOS:
    def make_click_through(window, enable=True):
        pass

# ---------- Presets and colors ----------
PRESETS = ["dot", "cross", "circle", "cross_dot", "t_shape", "cross_gap"]
PRESET_NAMES_RU = {
    "dot": "Точка",
    "cross": "Крест",
    "circle": "Круг",
    "cross_dot": "Крест + точка",
    "t_shape": "T-образный",
    "cross_gap": "Крест с разрывом",
}

SWATCHES = [
    ("Белый", "#ffffff"),
    ("Чёрный", "#000000"),
    ("Красный", "#ff3b30"),
    ("Зелёный", "#34d058"),
    ("Голубой", "#2fd7ff"),
    ("Жёлтый", "#ffd60a"),
    ("Розовый", "#ff5cb6"),
    ("Оранжевый", "#ff9500"),
]

DEFAULT_CONFIG = {
    "preset": "cross_gap",
    "color": "#ffffff",
    "size": 8,
    "thickness": 2,
    "opacity": 1.0,
    "x": None,
    "y": None,
    "visible": True,
}


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            merged.update(cfg)
            return merged
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")


class CrosshairOverlay:
    def __init__(self):
        self.cfg = load_config()
        self.move_mode = False
        self._drag_data = (0, 0)
        self.hotkey_listener = None
        self.tray_icon = None

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.iconbitmap(ICON_PATH) if IS_WINDOWS and os.path.exists(ICON_PATH) else None

        self.overlay_win = tk.Toplevel(self.root)
        self.overlay_win.overrideredirect(True)
        self.overlay_win.attributes("-topmost", True)

        self.transparent_key = "magenta"
        self.overlay_win.configure(bg=self.transparent_key)
        
        if IS_WINDOWS:
            self.overlay_win.wm_attributes("-transparentcolor", self.transparent_key)
        elif IS_MACOS:
            self.overlay_win.wm_attributes("-transparent", True)

        sw = self.overlay_win.winfo_screenwidth()
        sh = self.overlay_win.winfo_screenheight()
        self.win_size = 300

        if self.cfg["x"] is None:
            self.cfg["x"] = sw // 2
        if self.cfg["y"] is None:
            self.cfg["y"] = sh // 2

        self.update_geometry()

        self.canvas = tk.Canvas(
            self.overlay_win, width=self.win_size, height=self.win_size,
            bg=self.transparent_key, highlightthickness=0
        )
        self.canvas.pack()

        if IS_WINDOWS:
            self.overlay_win.update_idletasks()
            self.hwnd = user32.GetParent(self.overlay_win.winfo_id())
            self.apply_click_through()
        elif IS_MACOS:
            self.hwnd = None

        self.draw()
        self.setup_hotkeys()
        self.setup_move_bindings()

        self.settings_win = SettingsWindow(self)
        self.setup_tray()

    def setup_tray(self):
        def create_tray():
            try:
                if os.path.exists(ICON_PATH):
                    icon_image = Image.open(ICON_PATH)
                else:
                    icon_image = Image.new('RGB', (64, 64), color='white')
                
                menu = pystray.Menu(
                    pystray.MenuItem("Настройки", self.show_settings, default=True),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Закрыть", self.quit_app)
                )
                
                self.tray_icon = pystray.Icon("crosshair", icon_image, "Crosshair Overlay", menu)
                self.tray_icon.run()
            except Exception as e:
                print(f"Tray error: {e}")
        
        import threading
        tray_thread = threading.Thread(target=create_tray, daemon=True)
        tray_thread.start()

    def show_settings(self, icon=None, item=None):
        if self.settings_win:
            self.settings_win.win.deiconify()
            self.settings_win.win.lift()

    def quit_app(self, icon=None, item=None):
        save_config(self.cfg)
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()

    def update_geometry(self):
        x = self.cfg["x"] - self.win_size // 2
        y = self.cfg["y"] - self.win_size // 2
        self.overlay_win.geometry(f"{self.win_size}x{self.win_size}+{x}+{y}")

    def apply_click_through(self):
        if IS_WINDOWS:
            make_click_through(self.hwnd, enable=not self.move_mode)

    def draw(self):
        self.canvas.delete("all")
        if not self.cfg["visible"]:
            return

        c = self.win_size // 2
        size = self.cfg["size"]
        th = self.cfg["thickness"]
        color = self.cfg["color"]
        preset = self.cfg["preset"]

        if preset == "dot":
            r = max(2, size // 3)
            self.canvas.create_oval(c - r, c - r, c + r, c + r, fill=color, outline=color)

        elif preset == "cross":
            self.canvas.create_line(c - size, c, c + size, c, fill=color, width=th)
            self.canvas.create_line(c, c - size, c, c + size, fill=color, width=th)

        elif preset == "circle":
            self.canvas.create_oval(c - size, c - size, c + size, c + size, outline=color, width=th)

        elif preset == "cross_dot":
            self.canvas.create_line(c - size, c, c + size, c, fill=color, width=th)
            self.canvas.create_line(c, c - size, c, c + size, fill=color, width=th)
            r = max(2, th)
            self.canvas.create_oval(c - r, c - r, c + r, c + r, fill=color, outline=color)

        elif preset == "t_shape":
            self.canvas.create_line(c - size, c, c + size, c, fill=color, width=th)
            self.canvas.create_line(c, c, c, c + size, fill=color, width=th)

        elif preset == "cross_gap":
            gap = max(3, size // 2)
            self.canvas.create_line(c - size - gap, c, c - gap, c, fill=color, width=th)
            self.canvas.create_line(c + gap, c, c + size + gap, c, fill=color, width=th)
            self.canvas.create_line(c, c - size - gap, c, c - gap, fill=color, width=th)
            self.canvas.create_line(c, c + gap, c, c + size + gap, fill=color, width=th)

        self.overlay_win.attributes("-alpha", self.cfg["opacity"])

    def setup_move_bindings(self):
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.do_drag)

    def start_drag(self, event):
        self._drag_data = (event.x_root, event.y_root)

    def do_drag(self, event):
        if not self.move_mode:
            return
        dx = event.x_root - self._drag_data[0]
        dy = event.y_root - self._drag_data[1]
        self.cfg["x"] += dx
        self.cfg["y"] += dy
        self._drag_data = (event.x_root, event.y_root)
        self.update_geometry()

    def setup_hotkeys(self):
        if IS_WINDOWS:
            keyboard.add_hotkey("f5", self.toggle_visible)
            keyboard.add_hotkey("f6", self.toggle_move_mode)
            keyboard.add_hotkey("f9", self.save_and_exit)
            keyboard.add_hotkey("f10", self.raise_settings)
        elif IS_MACOS:
            def on_press(key):
                try:
                    if key == pynput_keyboard.Key.f5:
                        self.toggle_visible()
                    elif key == pynput_keyboard.Key.f6:
                        self.toggle_move_mode()
                    elif key == pynput_keyboard.Key.f9:
                        self.save_and_exit()
                    elif key == pynput_keyboard.Key.f10:
                        self.raise_settings()
                except Exception:
                    pass
            
            self.hotkey_listener = pynput_keyboard.Listener(on_press=on_press)
            self.hotkey_listener.start()

    def toggle_visible(self):
        self.cfg["visible"] = not self.cfg["visible"]
        self.draw()
        if hasattr(self, "settings_win"):
            self.settings_win.sync_visible_checkbox()

    def toggle_move_mode(self):
        self.move_mode = not self.move_mode
        self.apply_click_through()
        if hasattr(self, "settings_win"):
            self.settings_win.sync_move_checkbox()

    def raise_settings(self):
        self.settings_win.win.deiconify()
        self.settings_win.win.lift()

    def reset_position(self):
        sw = self.overlay_win.winfo_screenwidth()
        sh = self.overlay_win.winfo_screenheight()
        self.cfg["x"] = sw // 2
        self.cfg["y"] = sh // 2
        self.update_geometry()

    def save_and_exit(self):
        self.quit_app()

    def run(self):
        self.root.mainloop()
        if self.tray_icon:
            self.tray_icon.stop()
        save_config(self.cfg)
        if self.hotkey_listener:
            self.hotkey_listener.stop()


class SettingsWindow:
    def __init__(self, overlay: CrosshairOverlay):
        self.overlay = overlay
        cfg = overlay.cfg

        self.win = tk.Toplevel(overlay.root)
        self.win.title("Настройки прицела")
        self.win.geometry("300x500")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)
        self.win.protocol("WM_DELETE_WINDOW", self.on_close)

        pad = {"padx": 10, "pady": 6}

        platform_label = f"Платформа: {'Windows' if IS_WINDOWS else 'macOS' if IS_MACOS else 'Unknown'}"
        tk.Label(self.win, text=platform_label, font=("Segoe UI", 8), fg="#888888").pack(anchor="w", **pad)

        tk.Label(self.win, text="Форма прицела", font=("Segoe UI", 9, "bold")).pack(anchor="w", **pad)
        self.preset_var = tk.StringVar(value=PRESET_NAMES_RU[cfg["preset"]])
        preset_combo = ttk.Combobox(
            self.win, textvariable=self.preset_var, state="readonly",
            values=[PRESET_NAMES_RU[p] for p in PRESETS]
        )
        preset_combo.pack(fill="x", padx=10)
        preset_combo.bind("<<ComboboxSelected>>", self.on_preset_change)

        tk.Label(self.win, text="Цвет", font=("Segoe UI", 9, "bold")).pack(anchor="w", **pad)
        swatch_frame = tk.Frame(self.win)
        swatch_frame.pack(fill="x", padx=10)
        for i, (name, hexcol) in enumerate(SWATCHES):
            b = tk.Button(
                swatch_frame, bg=hexcol, width=3, height=1,
                relief="ridge", command=lambda h=hexcol: self.on_swatch_pick(h)
            )
            b.grid(row=i // 4, column=i % 4, padx=3, pady=3)

        custom_btn = tk.Button(self.win, text="Другой цвет...", command=self.on_custom_color)
        custom_btn.pack(fill="x", padx=10, pady=(4, 0))

        tk.Label(self.win, text="Размер", font=("Segoe UI", 9, "bold")).pack(anchor="w", **pad)
        self.size_var = tk.IntVar(value=cfg["size"])
        tk.Scale(
            self.win, from_=2, to=60, orient="horizontal", variable=self.size_var,
            command=self.on_size_change
        ).pack(fill="x", padx=10)

        tk.Label(self.win, text="Толщина линий", font=("Segoe UI", 9, "bold")).pack(anchor="w", **pad)
        self.thickness_var = tk.IntVar(value=cfg["thickness"])
        tk.Scale(
            self.win, from_=1, to=8, orient="horizontal", variable=self.thickness_var,
            command=self.on_thickness_change
        ).pack(fill="x", padx=10)

        tk.Label(self.win, text="Прозрачность", font=("Segoe UI", 9, "bold")).pack(anchor="w", **pad)
        self.opacity_var = tk.DoubleVar(value=cfg["opacity"])
        tk.Scale(
            self.win, from_=0.1, to=1.0, resolution=0.05, orient="horizontal",
            variable=self.opacity_var, command=self.on_opacity_change
        ).pack(fill="x", padx=10)

        self.visible_var = tk.BooleanVar(value=cfg["visible"])
        tk.Checkbutton(
            self.win, text="Показывать прицел (F5)", variable=self.visible_var,
            command=self.on_visible_toggle
        ).pack(anchor="w", padx=10, pady=(10, 0))

        self.move_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            self.win, text="Режим перемещения — тащить мышью (F6)", variable=self.move_var,
            command=self.on_move_toggle
        ).pack(anchor="w", padx=10)

        tk.Label(
            self.win,
            text="Включите режим перемещения, перетащите\nприцел в нужное место, затем выключите.",
            fg="#666666", justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 6))

        tk.Button(self.win, text="Сбросить позицию в центр", command=self.overlay.reset_position)\
            .pack(fill="x", padx=10, pady=(0, 10))

        btn_frame = tk.Frame(self.win)
        btn_frame.pack(fill="x", padx=10, pady=10, side="bottom")
        tk.Button(btn_frame, text="Сохранить", command=lambda: save_config(self.overlay.cfg))\
            .pack(side="left", expand=True, fill="x", padx=(0, 5))
        tk.Button(btn_frame, text="Сохранить и выйти", command=self.overlay.save_and_exit)\
            .pack(side="left", expand=True, fill="x", padx=(5, 0))

    def on_preset_change(self, event=None):
        name = self.preset_var.get()
        for key, ru in PRESET_NAMES_RU.items():
            if ru == name:
                self.overlay.cfg["preset"] = key
                break
        self.overlay.draw()

    def on_swatch_pick(self, hexcol):
        self.overlay.cfg["color"] = hexcol
        self.overlay.draw()

    def on_custom_color(self):
        rgb, hexcol = colorchooser.askcolor(color=self.overlay.cfg["color"], title="Выберите цвет прицела")
        if hexcol:
            self.overlay.cfg["color"] = hexcol
            self.overlay.draw()

    def on_size_change(self, value):
        self.overlay.cfg["size"] = int(float(value))
        self.overlay.draw()

    def on_thickness_change(self, value):
        self.overlay.cfg["thickness"] = int(float(value))
        self.overlay.draw()

    def on_opacity_change(self, value):
        self.overlay.cfg["opacity"] = round(float(value), 2)
        self.overlay.draw()

    def on_visible_toggle(self):
        self.overlay.cfg["visible"] = self.visible_var.get()
        self.overlay.draw()

    def on_move_toggle(self):
        self.overlay.move_mode = self.move_var.get()
        self.overlay.apply_click_through()

    def sync_visible_checkbox(self):
        self.visible_var.set(self.overlay.cfg["visible"])

    def sync_move_checkbox(self):
        self.move_var.set(self.overlay.move_mode)

    def on_close(self):
        self.win.withdraw()


if __name__ == "__main__":
    if not IS_WINDOWS and not IS_MACOS:
        print(f"Неподдерживаемая платформа: {PLATFORM}")
        print("Поддерживаются: Windows, macOS")
        sys.exit(1)
    
    app = CrosshairOverlay()
    app.run()
