#!/usr/bin/env python3
"""
Palm Crosshair Overlay - Modern cross-platform overlay for gaming
Beautiful PyQt5 interface with cross-platform support (Windows, macOS, Linux)
"""

import sys
import os
import json
import platform
from pathlib import Path

# PyQt5 imports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QComboBox, QSlider, QPushButton, QCheckBox, 
                            QGroupBox, QGridLayout, QColorDialog, QSystemTrayIcon, QMenu, QDialog)
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal, QPoint, QRect
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QIcon, QPixmap, QFont

# Hotkey libraries
IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"

if IS_WINDOWS:
    try:
        import keyboard
        HAS_HOTKEYS = True
    except ImportError:
        HAS_HOTKEYS = False
elif IS_MACOS:
    try:
        from pynput import keyboard as pynput_keyboard
        HAS_HOTKEYS = True
        listener = None
    except ImportError:
        HAS_HOTKEYS = False
else:
    HAS_HOTKEYS = False

# Config
CONFIG_PATH = Path(__file__).parent / "config.json"

# Crosshair presets
PRESETS = {
    "dot": "Dot",
    "cross": "Cross",
    "circle": "Circle",
    "cross_dot": "Cross + Dot",
    "t_shape": "T Shape",
    "cross_gap": "Cross Gap"
}

COLOR_PRESETS = [
    ("White", "#FFFFFF"),
    ("Black", "#000000"),
    ("Red", "#FF3B30"),
    ("Green", "#34D058"),
    ("Blue", "#2FD7FF"),
    ("Yellow", "#FFD60A"),
    ("Pink", "#FF5CB6"),
    ("Orange", "#FF9500")
]

DEFAULT_CONFIG = {
    "preset": "cross_gap",
    "color": "#FFFFFF",
    "size": 20,
    "thickness": 3,
    "opacity": 0.85,
    "x": None,
    "y": None,
    "visible": True,
    "hotkeys_enabled": True,
    "hotkeys": {
        "toggle_visible": "F5",
        "toggle_move": "F6",
        "show_settings": "F10",
        "quit": "F9"
    }
}

def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            merged.update(cfg)
            return merged
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


class CrosshairOverlay(QWidget):
    """Transparent overlay window with crosshair"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.move_mode = False
        self.drag_start = None
        
        # Window setup
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, not self.move_mode)
        
        # Size and position
        self.win_size = 400
        screen = QApplication.primaryScreen().geometry()
        if self.config["x"] is None:
            self.config["x"] = screen.width() // 2
        if self.config["y"] is None:
            self.config["y"] = screen.height() // 2
            
        self.update_geometry()
        
        # Hotkeys
        self.hotkey_listener = None
        if HAS_HOTKEYS and self.config["hotkeys_enabled"]:
            self.setup_hotkeys()
    
    def update_geometry(self):
        x = self.config["x"] - self.win_size // 2
        y = self.config["y"] - self.win_size // 2
        self.setGeometry(x, y, self.win_size, self.win_size)
    
    def paintEvent(self, event):
        if not self.config["visible"]:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Set opacity
        painter.setOpacity(self.config["opacity"])
        
        # Set color and thickness
        color = QColor(self.config["color"])
        painter.setPen(QPen(color, self.config["thickness"], Qt.SolidLine))
        
        center_x = self.win_size // 2
        center_y = self.win_size // 2
        size = self.config["size"]
        
        preset = self.config["preset"]
        
        if preset == "dot":
            radius = max(3, size // 4)
            painter.setBrush(color)
            painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
            
        elif preset == "cross":
            painter.drawLine(center_x - size, center_y, center_x + size, center_y)
            painter.drawLine(center_x, center_y - size, center_x, center_y + size)
            
        elif preset == "circle":
            painter.drawEllipse(center_x - size, center_y - size, size * 2, size * 2)
            
        elif preset == "cross_dot":
            painter.drawLine(center_x - size, center_y, center_x + size, center_y)
            painter.drawLine(center_x, center_y - size, center_x, center_y + size)
            radius = max(3, self.config["thickness"])
            painter.setBrush(color)
            painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
            
        elif preset == "t_shape":
            painter.drawLine(center_x - size, center_y, center_x + size, center_y)
            painter.drawLine(center_x, center_y, center_x, center_y + size)
            
        elif preset == "cross_gap":
            gap = max(5, size // 3)
            painter.drawLine(center_x - size - gap, center_y, center_x - gap, center_y)
            painter.drawLine(center_x + gap, center_y, center_x + size + gap, center_y)
            painter.drawLine(center_x, center_y - size - gap, center_x, center_y - gap)
            painter.drawLine(center_x, center_y + gap, center_x, center_y + size + gap)
    
    def mousePressEvent(self, event):
        if self.move_mode and event.button() == Qt.LeftButton:
            self.drag_start = event.globalPos() - self.pos()
    
    def mouseMoveEvent(self, event):
        if self.move_mode and self.drag_start is not None:
            self.move(event.globalPos() - self.drag_start)
            self.config["x"] = self.x() + self.win_size // 2
            self.config["y"] = self.y() + self.win_size // 2
    
    def mouseReleaseEvent(self, event):
        self.drag_start = None
    
    def toggle_visible(self):
        self.config["visible"] = not self.config["visible"]
        self.update()
    
    def toggle_move_mode(self):
        self.move_mode = not self.move_mode
        self.setAttribute(Qt.WA_TransparentForMouseEvents, not self.move_mode)
    
    def reset_position(self):
        screen = QApplication.primaryScreen().geometry()
        self.config["x"] = screen.width() // 2
        self.config["y"] = screen.height() // 2
        self.update_geometry()
    
    def setup_hotkeys(self):
        if IS_WINDOWS and HAS_HOTKEYS:
            keyboard.add_hotkey(self.config["hotkeys"]["toggle_visible"], self.toggle_visible)
            keyboard.add_hotkey(self.config["hotkeys"]["toggle_move"], self.toggle_move_mode)
            keyboard.add_hotkey(self.config["hotkeys"]["quit"], lambda: QApplication.quit())
        elif IS_MACOS and HAS_HOTKEYS:
            def on_press(key):
                try:
                    key_str = key.char if hasattr(key, 'char') else str(key)
                    if key_str == self.config["hotkeys"]["toggle_visible"]:
                        self.toggle_visible()
                    elif key_str == self.config["hotkeys"]["toggle_move"]:
                        self.toggle_move_mode()
                    elif key_str == self.config["hotkeys"]["quit"]:
                        QApplication.quit()
                except Exception:
                    pass
            
            self.hotkey_listener = pynput_keyboard.Listener(on_press=on_press)
            self.hotkey_listener.start()


class SettingsWindow(QMainWindow):
    """Modern settings window with PyQt5"""
    
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, overlay, parent=None):
        super().__init__(parent)
        self.overlay = overlay
        self.config = overlay.config
        
        self.setWindowTitle("Palm Crosshair Settings")
        self.setFixedSize(500, 600)
        
        # Set window icon if available
        icon_path = Path(__file__).parent / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # Setup UI
        self.setup_ui()
        
        # Tray icon
        self.setup_tray()
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Preset selection
        preset_group = QGroupBox("Crosshair Preset")
        preset_layout = QVBoxLayout()
        self.preset_combo = QComboBox()
        for key, name in PRESETS.items():
            self.preset_combo.addItem(name, key)
        self.preset_combo.setCurrentText(PRESETS[self.config["preset"]])
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        preset_layout.addWidget(self.preset_combo)
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)
        
        # Color selection
        color_group = QGroupBox("Color")
        color_layout = QGridLayout()
        
        # Color presets
        row, col = 0, 0
        for name, hex_color in COLOR_PRESETS:
            btn = QPushButton(name)
            btn.setStyleSheet(f"background-color: {hex_color}; color: {'white' if name == 'Black' else 'black'}")
            btn.clicked.connect(lambda _, h=hex_color: self.on_color_preset(h))
            color_layout.addWidget(btn, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1
        
        # Custom color button
        custom_btn = QPushButton("Custom Color...")
        custom_btn.clicked.connect(self.on_custom_color)
        color_layout.addWidget(custom_btn, row + 1, 0, 1, 4)
        
        color_group.setLayout(color_layout)
        layout.addWidget(color_group)
        
        # Size and thickness
        size_group = QGroupBox("Size & Thickness")
        size_layout = QVBoxLayout()
        
        # Size slider
        size_label = QLabel(f"Size: {self.config['size']}px")
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(5, 60)
        self.size_slider.setValue(self.config["size"])
        self.size_slider.valueChanged.connect(lambda v: self.on_size_changed(v, size_label))
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.size_slider)
        
        # Thickness slider
        thickness_label = QLabel(f"Thickness: {self.config['thickness']}px")
        self.thickness_slider = QSlider(Qt.Horizontal)
        self.thickness_slider.setRange(1, 10)
        self.thickness_slider.setValue(self.config["thickness"])
        self.thickness_slider.valueChanged.connect(lambda v: self.on_thickness_changed(v, thickness_label))
        size_layout.addWidget(thickness_label)
        size_layout.addWidget(self.thickness_slider)
        
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)
        
        # Opacity
        opacity_group = QGroupBox("Opacity")
        opacity_layout = QVBoxLayout()
        opacity_label = QLabel(f"Opacity: {self.config['opacity'] * 100:.0f}%")
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(int(self.config["opacity"] * 100))
        self.opacity_slider.valueChanged.connect(lambda v: self.on_opacity_changed(v, opacity_label))
        opacity_layout.addWidget(opacity_label)
        opacity_layout.addWidget(self.opacity_slider)
        opacity_group.setLayout(opacity_layout)
        layout.addWidget(opacity_group)
        
        # Visibility and movement
        control_group = QGroupBox("Controls")
        control_layout = QVBoxLayout()
        
        self.visible_check = QCheckBox("Visible (F5)")
        self.visible_check.setChecked(self.config["visible"])
        self.visible_check.stateChanged.connect(self.on_visible_changed)
        control_layout.addWidget(self.visible_check)
        
        self.move_check = QCheckBox("Move Mode (F6) - Drag to reposition")
        self.move_check.setChecked(self.overlay.move_mode)
        self.move_check.stateChanged.connect(self.on_move_changed)
        control_layout.addWidget(self.move_check)
        
        reset_btn = QPushButton("Reset Position to Center")
        reset_btn.clicked.connect(self.on_reset_position)
        control_layout.addWidget(reset_btn)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.on_save)
        button_layout.addWidget(save_btn)
        
        quit_btn = QPushButton("Save & Quit")
        quit_btn.clicked.connect(self.on_quit)
        button_layout.addWidget(quit_btn)
        
        layout.addLayout(button_layout)
    
    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # Set tray icon
        icon_path = Path(__file__).parent / "icon.ico"
        if icon_path.exists():
            self.tray_icon.setIcon(QIcon(str(icon_path)))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = tray_menu.addAction("Show Settings")
        show_action.triggered.connect(self.show)
        
        tray_menu.addSeparator()
        
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(QApplication.quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # Connect tray icon click
        self.tray_icon.activated.connect(self.on_tray_activated)
    
    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show()
            self.activateWindow()
    
    def on_preset_changed(self, index):
        preset_key = self.preset_combo.currentData()
        self.config["preset"] = preset_key
        self.settings_changed.emit(self.config)
    
    def on_color_preset(self, hex_color):
        self.config["color"] = hex_color
        self.settings_changed.emit(self.config)
    
    def on_custom_color(self):
        color = QColorDialog.getColor(QColor(self.config["color"]), self, "Select Crosshair Color")
        if color.isValid():
            self.config["color"] = color.name()
            self.settings_changed.emit(self.config)
    
    def on_size_changed(self, value, label):
        self.config["size"] = value
        label.setText(f"Size: {value}px")
        self.settings_changed.emit(self.config)
    
    def on_thickness_changed(self, value, label):
        self.config["thickness"] = value
        label.setText(f"Thickness: {value}px")
        self.settings_changed.emit(self.config)
    
    def on_opacity_changed(self, value, label):
        opacity = value / 100.0
        self.config["opacity"] = opacity
        label.setText(f"Opacity: {value}%")
        self.settings_changed.emit(self.config)
    
    def on_visible_changed(self, state):
        self.config["visible"] = state == Qt.Checked
        self.settings_changed.emit(self.config)
    
    def on_move_changed(self, state):
        self.overlay.move_mode = state == Qt.Checked
        self.overlay.setAttribute(Qt.WA_TransparentForMouseEvents, not self.overlay.move_mode)
    
    def on_reset_position(self):
        self.overlay.reset_position()
    
    def on_save(self):
        save_config(self.config)
    
    def on_quit(self):
        save_config(self.config)
        QApplication.quit()
    
    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Palm Crosshair",
            "Application minimized to tray",
            QSystemTrayIcon.Information,
            2000
        )


def main():
    # Create application
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Load config
    config = load_config()
    
    # Create overlay
    overlay = CrosshairOverlay(config)
    overlay.show()
    
    # Create settings window
    settings = SettingsWindow(overlay)
    settings.show()
    
    # Connect settings changes to overlay updates
    settings.settings_changed.connect(lambda cfg: overlay.update())
    
    # Run
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
