import sys
import os
import time
import json

# --- FREEZE-PROOF SYSTEM PATH ANCHOR ---
if getattr(sys, 'frozen', False):
    exe_dir = os.path.dirname(sys.executable)
else:
    exe_dir = os.path.dirname(os.path.abspath(__file__))

os.environ["PATH"] = exe_dir + os.pathsep + os.environ["PATH"]
CONFIG_FILE = os.path.join(exe_dir, "config.json")

import mpv
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QHBoxLayout, QWidget, QFileDialog, QListWidget, QLineEdit, 
                             QSlider, QLabel, QColorDialog, QFontDialog, QMessageBox) 
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QShortcut, QKeySequence, QIcon, QPixmap, QColor, QFont
from PyQt6.QtSvg import QSvgRenderer

# --- CYBERPUNK MULTI-PANEL DECK SKIN ---
STYLESHEET = """
QMainWindow { 
    background-color: #030303; 
    border: 1px solid #00f3ff; 
}

#TitleBar { 
    background-color: #0a0a0a; 
    border-bottom: 1px solid #1a1a1a; 
}
#TitleText {
    color: #00f3ff;
    font-family: 'Consolas';
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}

#SidePanel { 
    background-color: #050505; 
    border-right: 1px solid #1a1a1a; 
}
.PanelTitle {
    color: #ff00ea;
    font-family: 'Consolas';
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
    padding-top: 5px;
}
QLineEdit { 
    background-color: #0a0a0a; 
    color: #00f3ff; 
    border: 1px solid #333; 
    border-radius: 4px;
    padding: 6px; 
    font-family: 'Consolas'; 
    font-size: 11px;
}
QLineEdit:focus { border: 1px solid #00f3ff; }

QListWidget { 
    background-color: #070707; 
    color: #888; 
    border: 1px solid #111; 
    border-radius: 4px;
    font-family: 'Consolas'; 
    font-size: 11px; 
}
QListWidget::item { padding: 4px; border-radius: 2px; }
QListWidget::item:hover { background-color: #111; color: #00f3ff; }
QListWidget::item:selected { background-color: rgba(255, 0, 234, 0.15); color: #ff00ea; font-weight: bold; }

#BottomBar { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(0, 0, 0, 0), stop:0.4 rgba(5, 5, 5, 0.85), stop:1 rgba(5, 5, 5, 0.95));
    border-top: 1px solid rgba(0, 243, 255, 0.2);
}

QPushButton {
    background-color: transparent; 
    color: #00f3ff; 
    border: 1px solid rgba(0, 243, 255, 0.4);
    border-radius: 4px;
    padding: 6px 12px; 
    font-family: 'Consolas'; 
    font-weight: bold;
    font-size: 12px;
}
QPushButton:hover { 
    background-color: rgba(0, 243, 255, 0.1);
    border: 1px solid #00f3ff;
    color: #ffffff;
}

#CloseBtn { border: none; color: #ff00ea; font-size: 18px; font-weight: bold; }
#CloseBtn:hover { background: rgba(255, 0, 234, 0.2); color: #ffffff; }

#MaximizeBtn { border: none; color: #00f3ff; font-size: 15px; font-weight: bold; }
#MaximizeBtn:hover { background: rgba(0, 243, 255, 0.15); color: #ffffff; }

#PlayBtn, #FullscreenBtn {
    border: 1px solid rgba(0, 243, 255, 0.2);
    padding: 4px;
}
#PlayBtn:hover, #FullscreenBtn:hover { border: 1px solid #00f3ff; }

QSlider::groove:horizontal { height: 4px; background: rgba(255, 255, 255, 0.2); }
QSlider::sub-page:horizontal { background: #ff00ea; } 
QSlider::handle:horizontal { background: #00f3ff; width: 10px; height: 10px; margin: -3px 0; border-radius: 5px; }

#VolumeSlider::sub-page:horizontal { background: #00f3ff; }
#VolumeSlider::handle:horizontal { background: #ff00ea; }

#TimeLabel, #SubStatusLabel, #VolumeLabel { color: #888; font-family: 'Consolas'; font-size: 12px; }
#SubStatusLabel { color: #666; margin-left: 15px; }
#VolumeLabel { color: #00f3ff; font-weight: bold; margin-left: 10px; }

QMessageBox { background-color: #0a0a0a; border: 1px solid #ff00ea; }
QMessageBox QLabel { color: #00f3ff; font-family: 'Consolas'; }
QMessageBox QPushButton { color: #00f3ff; border: 1px solid #00f3ff; padding: 4px 10px; font-family: 'Consolas'; }
"""

SVG_PLAY = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#00f3ff"><path d="M8 5v14l11-7z"/></svg>'
SVG_PAUSE = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#00f3ff"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>'

class TimelineSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.is_user_dragging = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_user_dragging = True
            val = self.minimum() + ((self.maximum() - self.minimum()) * event.position().x()) / self.width()
            val = max(self.minimum(), min(self.maximum(), int(val)))
            self.setValue(val)
            self.sliderMoved.emit(val)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_user_dragging:
            val = self.minimum() + ((self.maximum() - self.minimum()) * event.position().x()) / self.width()
            val = max(self.minimum(), min(self.maximum(), int(val)))
            self.setValue(val)
            self.sliderMoved.emit(val)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_user_dragging = False
            self.sliderReleased.emit()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

class VolumeSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.is_user_dragging = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_user_dragging = True
            val = self.minimum() + ((self.maximum() - self.minimum()) * event.position().x()) / self.width()
            val = max(self.minimum(), min(self.maximum(), int(val)))
            self.setValue(val)
            self.sliderMoved.emit(val)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_user_dragging:
            val = self.minimum() + ((self.maximum() - self.minimum()) * event.position().x()) / self.width()
            val = max(self.minimum(), min(self.maximum(), int(val)))
            self.setValue(val)
            self.sliderMoved.emit(val)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_user_dragging = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

class CyberPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CyberPlayer")
        self.resize(1280, 720)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(STYLESHEET)
        
        self.media_files = [] 
        self.subtitle_files = [] 
        self.custom_subs_map = {} 
        self.playback_positions = {} 
        
        # --- UI State Initialization Defaults ---
        self.current_sub_size = 36
        self.current_sub_color = "#00f3ff" 
        self.current_sub_font = "Consolas" 
        self.current_volume = 100  
        self.last_known_text = "" 
        self.active_media_path = None
        self.is_awaiting_resume = False 
        self.pending_resume_seconds = 0.0 
        self.is_initializing = True
        self.video_fs_window = None

        self.init_ui()
        
        # Initialize MPV Engine
        self.player = mpv.MPV(wid=str(int(self.video_frame.winId())), force_window=True, keep_open='yes', volume_max=150.0)
        
        try:
            self.player.sub_use_osd = True
        except AttributeError:
            self.player._set_property('sub-use-osd', 'yes')

        self.player._set_property('osd-font', 'Consolas')
        self.player._set_property('osd-blur', '2')
        self.player._set_property('osd-border-size', '3')
        self.player._set_property('osd-margin-y', '45')
        
        last_played_media = self.load_configuration_memory()
        self.update_sub_styles() 
        
        self.current_volume = max(0, min(100, int(self.current_volume)))
        self.volume_slider.setValue(self.current_volume)
        self.volume_label.setText(f"VOL: {self.current_volume}%")
        try:
            self.player.volume = float(self.calculate_boosted_volume(self.current_volume))
        except:
            pass
        
        # Global Hotkeys
        self.shortcut_right = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        self.shortcut_right.activated.connect(self.skip_forward)
        self.shortcut_left = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        self.shortcut_left.activated.connect(self.skip_backward)
        
        # Main UI Refresh Clock loop
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_timeline)
        self.timer.start()
        
        # If launched via "Open With" (sys.argv), skip restoring last session —
        # the argv file will be played directly from __main__ instead.
        if len(sys.argv) > 1:
            self.is_initializing = False
        elif last_played_media and os.path.exists(last_played_media):
            QTimer.singleShot(200, lambda: self.play_file(last_played_media))
        else:
            self.is_initializing = False
        
    def init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- LEFT SIDE PANEL ---
        side_panel = QWidget()
        side_panel.setObjectName("SidePanel")
        side_panel.setFixedWidth(260)
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(12, 12, 12, 12)
        side_layout.setSpacing(8)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("GLOBAL SEARCH...")
        self.search_bar.textChanged.connect(self.filter_files)
        side_layout.addWidget(self.search_bar)
        
        lbl_media = QLabel("// MEDIA VAULT")
        lbl_media.setProperty("class", "PanelTitle")
        side_layout.addWidget(lbl_media)
        
        self.file_list = QListWidget()
        self.file_list.itemDoubleClicked.connect(self.play_from_list)
        side_layout.addWidget(self.file_list)
        
        lbl_subs = QLabel("// SUBTITLE VAULT")
        lbl_subs.setProperty("class", "PanelTitle")
        side_layout.addWidget(lbl_subs)
        
        self.sub_list = QListWidget()
        self.sub_list.itemDoubleClicked.connect(self.play_sub_from_list)
        side_layout.addWidget(self.sub_list)
        
        main_layout.addWidget(side_panel)
        
        # --- RIGHT VIEWER ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        title_bar = QWidget()
        title_bar.setObjectName("TitleBar")
        title_bar.setFixedHeight(35)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 0, 0, 0)
        
        title_text = QLabel("SYS.PLAYER // DECK 01")
        title_text.setObjectName("TitleText")
        title_layout.addWidget(title_text)
        
        title_layout.addStretch()

        maximize_btn = QPushButton("❐")
        maximize_btn.setObjectName("MaximizeBtn")
        maximize_btn.setFixedSize(45, 35)
        maximize_btn.setToolTip("Maximize App")
        maximize_btn.clicked.connect(self.toggle_fullscreen)
        title_layout.addWidget(maximize_btn)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("CloseBtn")
        close_btn.setFixedSize(45, 35)
        close_btn.clicked.connect(self.safely_handle_app_exit)
        title_layout.addWidget(close_btn)
        right_layout.addWidget(title_bar)
        
        self.viewport_container = QWidget()
        viewport_layout = QVBoxLayout(self.viewport_container)
        self.viewport_container.setContentsMargins(0, 0, 0, 0)
        viewport_layout.setSpacing(0)
        
        self.video_frame = QWidget()
        self.video_frame.setStyleSheet("background-color: #000000;")
        
        video_overlay_layout = QVBoxLayout(self.video_frame)
        video_overlay_layout.addStretch() 
        
        self.pyqt_sub_label = QLabel("")
        self.pyqt_sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pyqt_sub_label.setWordWrap(True)
        self.pyqt_sub_label.hide() 
        
        video_overlay_layout.addWidget(self.pyqt_sub_label, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        viewport_layout.addWidget(self.video_frame)
        
        # --- FLOATING BOTTOM BAR DECK ---
        self.bottom_bar = QWidget(self.viewport_container)
        self.bottom_bar.setObjectName("BottomBar")
        self.bottom_bar.setFixedHeight(85)
        bottom_layout = QVBoxLayout(self.bottom_bar)
        bottom_layout.setContentsMargins(20, 5, 20, 15)
        bottom_layout.setSpacing(8)
        
        self.slider = TimelineSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0) 
        self.slider.sliderMoved.connect(self.preview_time)
        self.slider.sliderReleased.connect(self.apply_video_position)
        bottom_layout.addWidget(self.slider)
        
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        self.play_btn = QPushButton()
        self.play_btn.setObjectName("PlayBtn")
        self.play_btn.setFixedSize(32, 28)
        self.set_vector_icon(self.play_btn, SVG_PLAY)
        self.play_btn.clicked.connect(self.toggle_play)
        controls_layout.addWidget(self.play_btn)
        
        self.time_label = QLabel("00:00:00.00 / 00:00:00.00")
        self.time_label.setObjectName("TimeLabel")
        controls_layout.addWidget(self.time_label)
        
        self.volume_slider = VolumeSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setObjectName("VolumeSlider")
        self.volume_slider.setRange(0, 100) 
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.sliderMoved.connect(self.adjust_system_volume)
        controls_layout.addWidget(self.volume_slider)
        
        self.volume_label = QLabel("VOL: 100%")
        self.volume_label.setObjectName("VolumeLabel")
        controls_layout.addWidget(self.volume_label)
        
        self.sub_status_label = QLabel("SUBTITLE: NONE")
        self.sub_status_label.setObjectName("SubStatusLabel")
        controls_layout.addWidget(self.sub_status_label)
        
        controls_layout.addSpacing(20)
        
        btn_sub_dec = QPushButton("A-")
        btn_sub_dec.clicked.connect(lambda: self.adjust_sub_size(-4))
        controls_layout.addWidget(btn_sub_dec)
        
        btn_sub_inc = QPushButton("A+")
        btn_sub_inc.clicked.connect(lambda: self.adjust_sub_size(4))
        controls_layout.addWidget(btn_sub_inc)
        
        btn_sub_color = QPushButton("COLOR")
        btn_sub_color.clicked.connect(self.open_color_dialog)
        controls_layout.addWidget(btn_sub_color)
        
        btn_sub_font = QPushButton("FONT")
        btn_sub_font.clicked.connect(self.open_font_dialog)
        controls_layout.addWidget(btn_sub_font)
        
        controls_layout.addSpacing(20)
        
        load_btn = QPushButton("LOAD MEDIA")
        load_btn.clicked.connect(self.load_media)
        controls_layout.addWidget(load_btn)
        
        sub_btn = QPushButton("LOAD SUBTITLE")
        sub_btn.clicked.connect(self.load_subtitle)
        controls_layout.addWidget(sub_btn)
        
        controls_layout.addStretch()

        video_fs_btn = QPushButton("⛶")
        video_fs_btn.setObjectName("FullscreenBtn")
        video_fs_btn.setFixedSize(45, 32)
        video_fs_btn.setToolTip("Video Fullscreen")
        video_fs_btn.clicked.connect(self.toggle_video_fullscreen)
        controls_layout.addWidget(video_fs_btn)
        
        bottom_layout.addLayout(controls_layout)
        viewport_layout.addWidget(self.bottom_bar)
        
        right_layout.addWidget(self.viewport_container)
        main_layout.addWidget(right_widget)

    def set_vector_icon(self, button, svg_data):
        renderer = QSvgRenderer(svg_data)
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        from PyQt6.QtGui import QPainter
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        
        button.setIcon(QIcon(pixmap))

    def load_configuration_memory(self):
        if not os.path.exists(CONFIG_FILE): return None
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                memory = json.load(f)
                
            self.current_sub_font = memory.get("font_family", "Consolas")
            self.current_sub_size = memory.get("font_size", 36)
            self.current_sub_color = memory.get("font_color", "#00f3ff")
            self.current_volume = memory.get("system_volume_level", 100) 
            
            raw_positions = memory.get("playback_positions", {})
            self.playback_positions = {k.lower().replace('\\', '/'): v for k, v in raw_positions.items()}
            
            raw_subs_map = memory.get("custom_subs_map", {})
            self.custom_subs_map = {k.lower().replace('\\', '/'): v.lower().replace('\\', '/') for k, v in raw_subs_map.items()}
            
            for path in memory.get("media_files_playlist", []):
                norm_path = path.lower().replace('\\', '/')
                if os.path.exists(norm_path) and norm_path not in self.media_files:
                    self.media_files.append(norm_path)
                    self.file_list.addItem(os.path.basename(norm_path))
                    
            for path in memory.get("subtitle_files_playlist", []):
                norm_path = path.lower().replace('\\', '/')
                if os.path.exists(norm_path) and norm_path not in self.subtitle_files:
                    self.subtitle_files.append(norm_path)
                    self.sub_list.addItem(os.path.basename(norm_path))
            
            last_active = memory.get("last_active_media_file", None)
            return last_active.lower().replace('\\', '/') if last_active else None
        except Exception as e:
            print(f"Memory extraction read break: {e}")
            return None

    def save_configuration_memory(self):
        if self.is_initializing: return

        if self.active_media_path and hasattr(self, 'player') and self.player.time_pos is not None and not self.is_awaiting_resume:
            self.playback_positions[self.active_media_path] = self.player.time_pos
            
        on_disk_memory = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    on_disk_memory = json.load(f)
            except:
                pass

        disk_media_playlist = [p.lower().replace('\\', '/') for p in on_disk_memory.get("media_files_playlist", [])]
        disk_sub_playlist = [p.lower().replace('\\', '/') for p in on_disk_memory.get("subtitle_files_playlist", [])]
        
        merged_media_playlist = list(set(self.media_files + disk_media_playlist))
        merged_sub_playlist = list(set(self.subtitle_files + disk_sub_playlist))
        
        disk_positions = {k.lower().replace('\\', '/'): v for k, v in on_disk_memory.get("playback_positions", {}).items()}
        disk_positions.update(self.playback_positions)
        
        disk_subs_map = {k.lower().replace('\\', '/'): v.lower().replace('\\', '/') for k, v in on_disk_memory.get("custom_subs_map", {}).items()}
        disk_subs_map.update(self.custom_subs_map)

        memory_payload = {
            "font_family": self.current_sub_font,
            "font_size": self.current_sub_size,
            "font_color": self.current_sub_color,
            "system_volume_level": int(self.current_volume), 
            "last_active_media_file": self.active_media_path if self.active_media_path else on_disk_memory.get("last_active_media_file", None),
            "media_files_playlist": merged_media_playlist,
            "subtitle_files_playlist": merged_sub_playlist,
            "custom_subs_map": disk_subs_map,
            "playback_positions": disk_positions
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(memory_payload, f, indent=4)
        except Exception as e:
            print(f"Memory write breakdown loop: {e}")

    def safely_handle_app_exit(self):
        self.close()

    def calculate_boosted_volume(self, value):
        if value <= 0:
            return 0.0
        boosted_value = float(value + 40)
        return min(100.0, boosted_value)

    def adjust_system_volume(self, value):
        try:
            self.current_volume = int(value) 
            self.volume_label.setText(f"VOL: {self.current_volume}%")
            self.player.volume = float(self.calculate_boosted_volume(self.current_volume))
            self.save_configuration_memory()
        except:
            pass

    def adjust_sub_size(self, delta):
        self.current_sub_size = max(12, min(72, self.current_sub_size + delta))
        self.update_sub_styles()
        self.save_configuration_memory()

    def open_color_dialog(self):
        self.timer.stop()
        parent = self.video_fs_window if self.video_fs_window is not None else self
        dialog = QColorDialog(parent)
        dialog.setCurrentColor(QColor(self.current_sub_color))
        dialog.setWindowTitle("CHOOSE SUBTITLE COLOR")
        
        if dialog.exec():
            selected_color = dialog.selectedColor()
            if selected_color.isValid():
                self.current_sub_color = selected_color.name() 
                self.update_sub_styles() 
                self.save_configuration_memory()
            
        self.timer.start()

    def open_font_dialog(self):
        self.timer.stop()
        parent = self.video_fs_window if self.video_fs_window is not None else self
        dialog = QFontDialog(parent)
        dialog.setCurrentFont(QFont(self.current_sub_font, self.current_sub_size))
        dialog.setWindowTitle("SELECT SUBTITLE FONT")
        
        if dialog.exec():
            selected_font = dialog.selectedFont()
            self.current_sub_font = selected_font.family().strip("'\"")
            self.update_sub_styles()
            self.save_configuration_memory()
            
        self.timer.start()

    def convert_rgb_to_mpv_hex(self, hex_str):
        clean_hex = hex_str.lstrip('#')
        r, g, b = clean_hex[0:2], clean_hex[2:4], clean_hex[4:6]
        return f"00{b}{g}{r}".upper()

    def update_sub_styles(self):
        try:
            self.player._set_property('sub-font', self.current_sub_font)
            self.player._set_property('sub-font-size', str(self.current_sub_size))
            self.player._set_property('sub-color', self.current_sub_color)
            self.player._set_property('sub-border-color', '#000000')
            self.player._set_property('sub-border-size', '2')
            
            self.player._set_property('osd-font', self.current_sub_font)
            self.player._set_property('osd-font-size', str(self.current_sub_size))
            
            mpv_ready_bgr_hex = self.convert_rgb_to_mpv_hex(self.current_sub_color)
            self.player._set_property('osd-color', f"#{mpv_ready_bgr_hex}")
            self.player._set_property('osd-border-color', '#000000')
            self.player._set_property('osd-border-size', '1') 
        except:
            pass
        
        if self.last_known_text:
            self.refresh_pyqt_label_styling()

    def refresh_pyqt_label_styling(self):
        inline_css = (
            f"font-family: '{self.current_sub_font}'; "
            f"font-size: {self.current_sub_size}px; "
            f"color: {self.current_sub_color}; "
            f"font-weight: bold; "
            f"background-color: rgba(5, 5, 5, 180); "
            f"padding: 12px 24px; "
            f"border-radius: 6px;"
        )
        self.pyqt_sub_label.setStyleSheet(inline_css)

    def update_timeline(self):
        if self.is_awaiting_resume and not self.slider.is_user_dragging:
            try:
                dur = self.player.duration
                pos = self.player.time_pos
                if dur == 0 or pos is None: return
                if dur > 0:
                    target = self.pending_resume_seconds
                    self.pending_resume_seconds = 0.0
                    self.is_awaiting_resume = False 
                    self.prompt_user_playback_resume(target)
                    return
            except:
                return

        if self.is_awaiting_resume: return 
        
        if not self.slider.is_user_dragging: 
            try:
                pos = self.player.time_pos
                dur = self.player.duration
                if pos is not None and dur is not None and dur > 0:
                    scaled_max = int(dur * 100)
                    scaled_pos = int(pos * 100)
                    
                    if self.slider.maximum() != scaled_max: 
                        self.slider.setRange(0, scaled_max)
                        
                    self.slider.blockSignals(True)
                    self.slider.setValue(scaled_pos)
                    self.slider.blockSignals(False)
                    self.time_label.setText(f"{self.format_time(pos)} / {self.format_time(dur)}")
                    
                    if self.active_media_path and not self.is_initializing:
                        self.playback_positions[self.active_media_path] = pos
                        self.save_configuration_memory()
            except:
                pass

        try:
            raw_text = self.player.get_property('sub-text')
            subtitle_text = str(raw_text).strip() if raw_text else ""
        except:
            subtitle_text = ""

        if subtitle_text != self.last_known_text:
            self.last_known_text = subtitle_text
            if not subtitle_text:
                self.pyqt_sub_label.hide()
            else:
                formatted_text = subtitle_text.replace('\r\n', '<br>').replace('\n', '<br>')
                self.refresh_pyqt_label_styling()
                self.pyqt_sub_label.setText(formatted_text)
                self.pyqt_sub_label.show()

    def skip_forward(self):
        if self.player.time_pos is not None: self.player.time_pos += 5.0

    def skip_backward(self):
        if self.player.time_pos is not None: self.player.time_pos = max(0.0, self.player.time_pos - 5.0)

    def format_time(self, total_seconds):
        if total_seconds is None: return "00:00:00.00"
        total_milliseconds = int(total_seconds * 100)
        seconds, hundredths = divmod(total_milliseconds, 100)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{hundredths:02d}"

    def preview_time(self, scaled_value):
        try:
            dur = self.player.duration
            if dur: 
                live_seconds = scaled_value / 100.0
                self.time_label.setText(f"{self.format_time(live_seconds)} / {self.format_time(dur)}")
        except:
            pass

    def apply_video_position(self):
        try:
            if self.player.duration is not None: 
                target_seconds = float(self.slider.value() / 100.0)
                self.player.time_pos = target_seconds
                if self.active_media_path:
                    self.playback_positions[self.active_media_path] = target_seconds
                    self.save_configuration_memory()
        except:
            pass

    def load_media(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select Media", "", "Media (*.mp4 *.mkv *.avi *.mp3 *.flac *.wav)")
        if filepath:
            self.play_file(filepath)

    def add_to_playlist(self, filepath):
        norm_path = filepath.lower().replace('\\', '/')
        if norm_path not in self.media_files:
            self.media_files.append(norm_path)
            self.file_list.addItem(os.path.basename(norm_path))
            
            if not self.is_initializing:
                self.save_configuration_memory()

    def play_from_list(self, item):
        for path in self.media_files:
            if os.path.basename(path) == item.text():
                self.play_file(path)
                break

    def load_subtitle(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select Subtitle", "", "Subtitles (*.srt *.ass *.vtt)")
        if filepath:
            self.add_subtitle_to_playlist(filepath)
            self.load_subtitle_from_path(filepath)

    def add_subtitle_to_playlist(self, filepath):
        norm_path = filepath.lower().replace('\\', '/')
        if norm_path not in self.subtitle_files:
            self.subtitle_files.append(norm_path)
            self.sub_list.addItem(os.path.basename(norm_path))
            self.save_configuration_memory()

    def play_sub_from_list(self, item):
        for path in self.subtitle_files:
            if os.path.basename(path) == item.text():
                self.load_subtitle_from_path(path)
                break

    def load_subtitle_from_path(self, filepath):
        norm_path = filepath.lower().replace('\\', '/')
        if os.path.exists(norm_path):
            try:
                self.player.sub_add(norm_path)
                filename = os.path.basename(norm_path)
                self.sub_status_label.setText(f"SUBTITLE: {filename.upper()}")
                self.sub_status_label.setStyleSheet("color: #ff00ea; font-weight: bold;")
                if self.active_media_path:
                    self.custom_subs_map[self.active_media_path] = norm_path
                    self.save_configuration_memory()
            except:
                pass

    def play_file(self, filepath):
        self.is_initializing = True
        self.is_awaiting_resume = False
        self.pending_resume_seconds = 0.0
        
        norm_path = filepath.lower().replace('\\', '/')
        
        # Look up the bookmark value FIRST using direct dictionary lookup parameters
        target_timestamp = self.playback_positions.get(norm_path, 0.0)
        
        # Now add to the playlist layout history elements safely
        self.add_to_playlist(norm_path)
        
        if self.active_media_path and hasattr(self, 'player'):
            try:
                pos = self.player.time_pos
                if pos is not None and pos > 0.5:
                    self.playback_positions[self.active_media_path] = pos
            except:
                pass
            
        self.active_media_path = norm_path
        
        try:
            self.player.play(norm_path)
            self.player.pause = False
            self.set_vector_icon(self.play_btn, SVG_PAUSE)
        except Exception as e:
            print(f"Decoder re-allocation anomaly: {e}")

        self.update_sub_styles()

        if norm_path in self.custom_subs_map:
            saved_sub_path = self.custom_subs_map[norm_path]
            self.load_subtitle_from_path(saved_sub_path)
        else:
            self.sub_status_label.setText("SUBTITLE: NONE")
            self.sub_status_label.setStyleSheet("color: #666;")
            self.pyqt_sub_label.hide()

        # Check if the database lookup position is validly past 0.5s
        if target_timestamp > 0.5:
            self.pending_resume_seconds = target_timestamp
            self.is_awaiting_resume = True
        else:
            self.is_initializing = False 

        self.handle_visual_frame_adjustments(norm_path)
        self.save_configuration_memory()

    def handle_visual_frame_adjustments(self, filepath):
        _, ext = os.path.splitext(filepath.lower())
        if ext in ['.mp3', '.flac', '.wav']:
            self.video_frame.setStyleSheet(
                "background-color: #030303; border-bottom: 1px solid rgba(255, 0, 234, 0.2); "
                "background-image: radial-gradient(circle, #0e0e0e 15%, transparent 16%); background-size: 12px 12px;"
            )
        else:
            self.video_frame.setStyleSheet("background-color: #000000; border: none;")

    def prompt_user_playback_resume(self, target_seconds):
        try:
            self.player.pause = True 
        except:
            pass
        time_str = self.format_time(target_seconds)
        
        parent = self.video_fs_window if self.video_fs_window is not None else self
        reply = QMessageBox.question(
            parent,
            "SYS.MEMORY // DECK RESUME", 
            f"Welcome back. Playback bookmark found for last track session.\nResume from timestamp position {time_str}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        try:
            if reply == QMessageBox.StandardButton.Yes:
                self.player.time_pos = target_seconds
            else:
                self.player.time_pos = 0.0
            self.player.pause = False
        except:
            pass
            
        self.set_vector_icon(self.play_btn, SVG_PAUSE)
        self.is_awaiting_resume = False 
        self.is_initializing = False 

    def toggle_play(self):
        try:
            if not self.player.pause:
                self.player.pause = True
                self.set_vector_icon(self.play_btn, SVG_PLAY)
            else:
                self.player.pause = False
                self.set_vector_icon(self.play_btn, SVG_PAUSE)
        except:
            pass

    def toggle_fullscreen(self):
        if self.isFullScreen(): self.showNormal()
        else: self.showFullScreen()

    def toggle_video_fullscreen(self):
        if self.video_fs_window is not None:
            QTimer.singleShot(0, self._exit_video_fullscreen)
        else:
            self._enter_video_fullscreen()

    def _enter_video_fullscreen(self):
        from PyQt6.QtGui import QShortcut

        screen = QApplication.primaryScreen().geometry()

        self.video_fs_window = QWidget(None, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.video_fs_window.setStyleSheet("background-color: #000000;")
        self.video_fs_window.setGeometry(screen)

        layout = QVBoxLayout(self.video_fs_window)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Reparent video_frame and bottom_bar into the fullscreen window
        self.video_frame.setParent(self.video_fs_window)
        self.bottom_bar.setParent(self.video_fs_window)
        layout.addWidget(self.video_frame)
        layout.addWidget(self.bottom_bar)

        self.video_fs_window.show()
        self.video_frame.show()
        self.bottom_bar.show()
        QApplication.processEvents()

        try:
            self.player.wid = str(int(self.video_frame.winId()))
        except Exception:
            pass

        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self.video_fs_window)
        esc.activated.connect(self._exit_video_fullscreen)

        self.video_fs_window.showFullScreen()

    def _exit_video_fullscreen(self):
        if self.video_fs_window is None:
            return

        vl = self.viewport_container.layout()
        self.video_frame.setParent(self.viewport_container)
        self.bottom_bar.setParent(self.viewport_container)
        vl.insertWidget(0, self.video_frame)
        vl.addWidget(self.bottom_bar)
        self.video_frame.show()
        self.bottom_bar.show()
        QApplication.processEvents()

        try:
            self.player.wid = str(int(self.video_frame.winId()))
        except Exception:
            pass

        self.video_fs_window.close()
        self.video_fs_window = None

    def filter_files(self, text):
        search_query = text.lower()
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            item.setHidden(search_query not in item.text().lower())
        for i in range(self.sub_list.count()):
            item = self.sub_list.item(i)
            item.setHidden(search_query not in item.text().lower())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.isFullScreen():
            self.oldPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if hasattr(self, 'oldPos') and not self.isFullScreen():
            delta = event.globalPosition().toPoint() - self.oldPos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPosition().toPoint()

# --- WINDOWS BOOTSTRAP INTERCEPTOR ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = CyberPlayer()
    player.show()
    
    if len(sys.argv) > 1:
        target_file = os.path.normpath(sys.argv[1]).lower().replace('\\', '/')
        if os.path.exists(target_file):
            QTimer.singleShot(250, lambda: player.play_file(target_file))
            
    sys.exit(app.exec())