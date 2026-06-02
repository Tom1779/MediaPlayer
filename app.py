import sys
import os
import time
import json

# Tell Python where MPV is located
os.environ["PATH"] = os.path.dirname(os.path.abspath(__file__)) + os.pathsep + os.environ["PATH"]

import mpv
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QHBoxLayout, QWidget, QFileDialog, QListWidget, QLineEdit, 
                             QSlider, QLabel, QColorDialog, QFontDialog, QMessageBox) 
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QShortcut, QKeySequence, QIcon, QPixmap, QColor, QFont
from PyQt6.QtSvg import QSvgRenderer

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

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

#PlayBtn, #FullscreenBtn {
    border: 1px solid rgba(0, 243, 255, 0.2);
    padding: 4px;
}
#PlayBtn:hover, #FullscreenBtn:hover { border: 1px solid #00f3ff; }

QSlider::groove:horizontal { height: 4px; background: rgba(255, 255, 255, 0.2); }
QSlider::sub-page:horizontal { background: #ff00ea; } 
QSlider::handle:horizontal { background: #00f3ff; width: 10px; height: 10px; margin: -3px 0; border-radius: 5px; }

#TimeLabel, #SubStatusLabel { color: #888; font-family: 'Consolas'; font-size: 12px; }
#SubStatusLabel { color: #666; margin-left: 15px; }

QMessageBox { background-color: #0a0a0a; border: 1px solid #ff00ea; }
QMessageBox QLabel { color: #00f3ff; font-family: 'Consolas'; }
QMessageBox QPushButton { color: #00f3ff; border: 1px solid #00f3ff; padding: 4px 10px; font-family: 'Consolas'; }
"""

SVG_PLAY = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#00f3ff"><path d="M8 5v14l11-7z"/></svg>'
SVG_PAUSE = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#00f3ff"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>'

class TimelineSlider(QSlider):
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            val = self.minimum() + ((self.maximum() - self.minimum()) * event.position().x()) / self.width()
            val = max(self.minimum(), min(self.maximum(), val))
            self.setValue(int(val))
            self.sliderMoved.emit(int(val))
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            val = self.minimum() + ((self.maximum() - self.minimum()) * event.position().x()) / self.width()
            val = max(self.minimum(), min(self.maximum(), val))
            self.setValue(int(val))
            self.sliderMoved.emit(int(val))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.sliderReleased.emit() 
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
        
        self.init_ui()
        
        # --- UI State Initialization ---
        self.current_sub_size = 36
        self.current_sub_color = "#00f3ff" 
        self.current_sub_font = "Consolas" 
        self.last_known_text = "" 
        self.active_media_path = None
        self.is_awaiting_resume = False 
        self.pending_resume_seconds = 0.0 
        self.is_initializing = True 
        
        # Initialize MPV Engine
        self.player = mpv.MPV(wid=str(int(self.video_frame.winId())), force_window=True, keep_open='yes')
        
        try:
            self.player.sub_use_osd = True
        except AttributeError:
            self.player._set_property('sub-use-osd', 'yes')

        self.player._set_property('osd-font', 'Consolas')
        self.player._set_property('osd-blur', '2')
        self.player._set_property('osd-border-size', '3')
        self.player._set_property('osd-margin-y', '45')
        
        # Unpack stored system memory attributes
        last_played_media = self.load_configuration_memory()
        self.update_sub_styles() 
        
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
        
        # Safe initial startup boot loader deployment pass
        if last_played_media and os.path.exists(last_played_media):
            QTimer.singleShot(200, lambda: self.play_file(last_played_media))
        else:
            self.is_initializing = False
        
    def init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- LEFT SIDE PANEL (SPLIT VAULT DECK) ---
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
        
        close_btn = QPushButton("✕")
        close_btn.setObjectName("CloseBtn")
        close_btn.setFixedSize(45, 35)
        close_btn.clicked.connect(self.safely_handle_app_exit) 
        title_layout.addStretch()
        title_layout.addWidget(close_btn)
        right_layout.addWidget(title_bar)
        
        viewport_container = QWidget()
        viewport_layout = QVBoxLayout(viewport_container)
        viewport_layout.setContentsMargins(0, 0, 0, 0)
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
        bottom_bar = QWidget(viewport_container)
        bottom_bar.setObjectName("BottomBar")
        bottom_bar.setFixedHeight(85)
        bottom_layout = QVBoxLayout(bottom_bar)
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
        
        self.time_label = QLabel("00:00:00 / 00:00:00")
        self.time_label.setObjectName("TimeLabel")
        controls_layout.addWidget(self.time_label)
        
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
        
        fullscreen_btn = QPushButton("⛶")
        fullscreen_btn.setObjectName("FullscreenBtn")
        fullscreen_btn.setFixedSize(32, 28)
        fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        controls_layout.addWidget(fullscreen_btn)
        
        bottom_layout.addLayout(controls_layout)
        viewport_layout.addWidget(bottom_bar)
        
        right_layout.addWidget(viewport_container)
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

    # --- CONFIGURATION ENGINE PERSISTENCE SYSTEM ---
    def load_configuration_memory(self):
        if not os.path.exists(CONFIG_FILE): return None
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                memory = json.load(f)
                
            self.current_sub_font = memory.get("font_family", "Consolas")
            self.current_sub_size = memory.get("font_size", 36)
            self.current_sub_color = memory.get("font_color", "#00f3ff")
            self.playback_positions = memory.get("playback_positions", {})
            self.custom_subs_map = memory.get("custom_subs_map", {})
            
            for path in memory.get("media_files_playlist", []):
                if os.path.exists(path) and path not in self.media_files:
                    self.media_files.append(path)
                    self.file_list.addItem(os.path.basename(path))
                    
            for path in memory.get("subtitle_files_playlist", []):
                if os.path.exists(path) and path not in self.subtitle_files:
                    self.subtitle_files.append(path)
                    self.sub_list.addItem(os.path.basename(path))
                    
            return memory.get("last_active_media_file", None)
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

        merged_media_playlist = list(set(self.media_files + on_disk_memory.get("media_files_playlist", [])))
        merged_sub_playlist = list(set(self.subtitle_files + on_disk_memory.get("subtitle_files_playlist", [])))
        
        merged_positions = on_disk_memory.get("playback_positions", {})
        merged_positions.update(self.playback_positions)
        
        merged_subs_map = on_disk_memory.get("custom_subs_map", {})
        merged_subs_map.update(self.custom_subs_map)

        memory_payload = {
            "font_family": self.current_sub_font,
            "font_size": self.current_sub_size,
            "font_color": self.current_sub_color,
            "last_active_media_file": self.active_media_path if self.active_media_path else on_disk_memory.get("last_active_media_file", None),
            "media_files_playlist": merged_media_playlist,
            "subtitle_files_playlist": merged_sub_playlist,
            "custom_subs_map": merged_subs_map,
            "playback_positions": merged_positions
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(memory_payload, f, indent=4)
        except Exception as e:
            print(f"Memory write breakdown loop: {e}")

    def safely_handle_app_exit(self):
        self.close()

    # --- LAYOUT STYLING CODES ---
    def adjust_sub_size(self, delta):
        self.current_sub_size = max(12, min(72, self.current_sub_size + delta))
        self.update_sub_styles()
        self.save_configuration_memory()

    def open_color_dialog(self):
        self.timer.stop() 
        dialog = QColorDialog(self)
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
        dialog = QFontDialog(self)
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
        self.player.sub_font = self.current_sub_font
        self.player.sub_font_size = self.current_sub_size
        self.player.sub_color = self.current_sub_color
        
        self.player._set_property('osd-font', self.current_sub_font)
        self.player._set_property('osd-font-size', str(self.current_sub_size))
        
        mpv_ready_bgr_hex = self.convert_rgb_to_mpv_hex(self.current_sub_color)
        self.player._set_property('osd-color', f"#{mpv_ready_bgr_hex}")
        self.player._set_property('osd-border-color', '#000000')
        self.player._set_property('osd-border-size', '1') 
        
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

    # --- MAIN THREAD TIMELINE ENGINE LOOP ---
    def update_timeline(self):
        # UI handshaking checkpoint loop
        if self.is_awaiting_resume and not self.slider.isSliderDown():
            try:
                dur = self.player.duration
                pos = self.player.time_pos
                if dur is not None and pos is not None and dur > 0:
                    target = self.pending_resume_seconds
                    self.pending_resume_seconds = 0.0
                    self.is_awaiting_resume = False 
                    self.prompt_user_playback_resume(target)
                    return
            except:
                return

        if self.is_awaiting_resume: return 
        
        if not self.slider.isSliderDown(): 
            try:
                pos = self.player.time_pos
                dur = self.player.duration
                if pos is not None and dur is not None and dur > 0:
                    if self.slider.maximum() != int(dur): self.slider.setRange(0, int(dur))
                    self.slider.blockSignals(True)
                    self.slider.setValue(int(pos))
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

    # --- TIME OPERATIONS ---
    def skip_forward(self):
        if self.player.time_pos is not None: self.player.time_pos += 5.0

    def skip_backward(self):
        if self.player.time_pos is not None: self.player.time_pos = max(0.0, self.player.time_pos - 5.0)

    def format_time(self, seconds):
        if seconds is None: return "00:00:00"
        s = int(seconds)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def preview_time(self, value):
        try:
            dur = self.player.duration
            if dur: self.time_label.setText(f"{self.format_time(value)} / {self.format_time(dur)}")
        except:
            pass

    def apply_video_position(self):
        try:
            if self.player.duration is not None: self.player.time_pos = float(self.slider.value())
        except:
            pass

    # --- MULTI-VAULT SUBTITLE & MEDIA LINKERS ---
    def load_media(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select Media", "", "Media (*.mp4 *.mkv *.avi *.mp3 *.flac *.wav)")
        if filepath:
            self.add_to_playlist(filepath)
            self.play_file(filepath)

    def add_to_playlist(self, filepath):
        if filepath not in self.media_files:
            self.media_files.append(filepath)
            self.file_list.addItem(os.path.basename(filepath))
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
        if filepath not in self.subtitle_files:
            self.subtitle_files.append(filepath)
            self.sub_list.addItem(os.path.basename(filepath))
            self.save_configuration_memory()

    def play_sub_from_list(self, item):
        for path in self.subtitle_files:
            if os.path.basename(path) == item.text():
                self.load_subtitle_from_path(path)
                break

    def load_subtitle_from_path(self, filepath):
        if os.path.exists(filepath):
            try:
                self.player.sub_add(filepath)
                filename = os.path.basename(filepath)
                self.sub_status_label.setText(f"SUBTITLE: {filename.upper()}")
                self.sub_status_label.setStyleSheet("color: #ff00ea; font-weight: bold;")
                if self.active_media_path:
                    self.custom_subs_map[self.active_media_path] = filepath
                    self.save_configuration_memory()
            except:
                pass

    # --- FIXED PLAY FILE INITIALIZER (CRASH IMMUNE PIPELINE) ---
    def play_file(self, filepath):
        # 1. Force the active sync clock loop to pause and stand down before switching handles
        self.is_initializing = True
        self.is_awaiting_resume = False
        self.pending_resume_seconds = 0.0
        
        # 2. Extract current position parameters safely before dropping decoder instances
        if self.active_media_path and hasattr(self, 'player'):
            try:
                pos = self.player.time_pos
                if pos is not None and pos > 0.5:
                    self.playback_positions[self.active_media_path] = pos
            except:
                pass
            
        self.active_media_path = filepath
        
        # 3. Terminate current video pipeline thread instances completely to prevent list click collision crashes
        try:
            self.player.play(filepath)
            self.player.pause = False
            self.set_vector_icon(self.play_btn, SVG_PAUSE)
        except Exception as e:
            print(f"Decoder reallocation fault bypassed: {e}")

        # 4. Pull auto-matched subtitle data mappings
        if filepath in self.custom_subs_map:
            saved_sub_path = self.custom_subs_map[filepath]
            self.load_subtitle_from_path(saved_sub_path)
        else:
            self.sub_status_label.setText("SUBTITLE: NONE")
            self.sub_status_label.setStyleSheet("color: #666;")
            self.pyqt_sub_label.hide()

        # 5. FIXED: Safetynet check lowered down to > 0.5 seconds to track short video files seamlessly
        if filepath in self.playback_positions:
            saved_seconds = self.playback_positions[filepath]
            if saved_seconds > 0.5:
                self.pending_resume_seconds = saved_seconds
                self.is_awaiting_resume = True
            else:
                self.is_initializing = False 
        else:
            self.is_initializing = False 

        self.handle_visual_frame_adjustments(filepath)
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
        
        reply = QMessageBox.question(
            self, 
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = CyberPlayer()
    player.show()
    sys.exit(app.exec())