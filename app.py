import sys
import os
import json
import math

# --- FREEZE-PROOF SYSTEM PATH ANCHOR ---
if getattr(sys, 'frozen', False):
    exe_dir = os.path.dirname(sys.executable)   # real .exe location (config, dlls)
    bundle_dir = sys._MEIPASS                    # temp extraction dir (bundled assets)
else:
    exe_dir = os.path.dirname(os.path.abspath(__file__))
    bundle_dir = exe_dir

os.environ["PATH"] = exe_dir + os.pathsep + os.environ["PATH"]
CONFIG_FILE = os.path.join(exe_dir, "config.json")

import mpv
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QHBoxLayout, QWidget, QFileDialog, QListWidget, QLineEdit, 
                             QSlider, QLabel, QColorDialog, QFontDialog, QMessageBox,
                             QToolTip)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from PyQt6.QtGui import QShortcut, QKeySequence, QIcon, QPixmap, QColor, QFont
from PyQt6.QtSvg import QSvgRenderer

# --- CYBERPUNK MULTI-PANEL DECK SKIN ---
STYLESHEET = """
QMainWindow { 
    background-color: #030303; 
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

#TimeLabel, #VolumeLabel { color: #888; font-family: 'Consolas'; font-size: 12px; }
#VolumeLabel { color: #00f3ff; font-weight: bold; margin-left: 10px; }

QMessageBox { background-color: #0a0a0a; border: 1px solid #ff00ea; }
QMessageBox QLabel { color: #00f3ff; font-family: 'Consolas'; }
QMessageBox QPushButton { color: #00f3ff; border: 1px solid #00f3ff; padding: 4px 10px; font-family: 'Consolas'; }
"""

SVG_PLAY = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#00f3ff"><path d="M8 5v14l11-7z"/></svg>'
SVG_PAUSE = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#00f3ff"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>'

class ClickableSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.is_user_dragging = False
        self._format_time_fn = None
        self._on_hover_fn = None  # called on any mouse move — used to reset fullscreen hide timer
        self.setMouseTracking(True)

    def _value_from_x(self, x):
        val = self.minimum() + ((self.maximum() - self.minimum()) * x) / self.width()
        return max(self.minimum(), min(self.maximum(), int(val)))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_user_dragging = True
            val = self._value_from_x(event.position().x())
            self.setValue(val)
            self.sliderMoved.emit(val)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_user_dragging:
            val = self._value_from_x(event.position().x())
            self.setValue(val)
            self.sliderMoved.emit(val)
            event.accept()
        else:
            super().mouseMoveEvent(event)

        if self._on_hover_fn:
            self._on_hover_fn()

        if self._format_time_fn and self.maximum() > 0:
            val = self._value_from_x(event.position().x())
            seconds = val / 100.0
            QToolTip.showText(
                event.globalPosition().toPoint(),
                self._format_time_fn(seconds),
                self,
                self.rect(),
                99999999
            )

    def leaveEvent(self, event):
        QToolTip.hideText()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_user_dragging = False
            self.sliderReleased.emit()
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class CyberPlayer(QMainWindow):
    _file_loaded = pyqtSignal()
    _sub_ready = pyqtSignal()  # emitted from file-loaded to apply pending sub on main thread
    def __init__(self):
        super().__init__()
        self.resize(1280, 720)
        self.setMinimumSize(900, 500)
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
        self.speed_steps = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
        self.speed_index = 3  # default 1.0x
        self.active_media_path = None
        self._pending_sub = None
        self._is_switching = False
        self._user_paused = False  # tracks whether USER intentionally paused  # sub action deferred until file-loaded
        self.is_awaiting_resume = False 
        self.pending_resume_seconds = 0.0 
        self.is_initializing = True
        self.video_fs_window = None
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geom = None
        self._controls_hide_timer = QTimer(self)
        self._controls_hide_timer.setSingleShot(True)
        self._controls_hide_timer.setInterval(5000)
        self._controls_hide_timer.timeout.connect(self._hide_controls)
        self._controls_opacity = QGraphicsOpacityEffect()
        self._controls_opacity.setOpacity(1.0)
        self._controls_anim = None

        self.init_ui()

        # Wire timeline slider tooltip to format_time
        self.slider._format_time_fn = self.format_time
        self.slider._on_hover_fn = self._reset_controls_timer

        # Lock time label width using explicit font construction — stylesheet may not be
        # applied yet when measuring, so we build the font directly to get accurate metrics.
        from PyQt6.QtGui import QFontMetrics, QFont
        fm = QFontMetrics(QFont("Consolas", 12))
        self.time_label.setFixedWidth(fm.horizontalAdvance("00:00:00 / 00:00:00") + 16)

        # App-level event filter for edge resize (child widgets swallow mouse events otherwise)
        from PyQt6.QtCore import QObject, QEvent
        class _ResizeFilter(QObject):
            def __init__(self_, win):
                super().__init__(win)
                self_._win = win
            def eventFilter(self_, obj, event):
                t = event.type()
                if t == QEvent.Type.MouseMove:
                    self_._win._handle_mouse_move(event)
                    return False
                if t == QEvent.Type.MouseButtonPress:
                    return self_._win._handle_mouse_press(event)
                if t == QEvent.Type.MouseButtonRelease:
                    self_._win._handle_mouse_release(event)
                    return False
                return False
        self._resize_filter = _ResizeFilter(self)
        QApplication.instance().installEventFilter(self._resize_filter)

        # Initialize MPV Engine
        self.player = mpv.MPV(
            wid=str(int(self.video_frame.winId())),
            force_window=True,
            keep_open='yes',
            volume_max=150.0,
            vo='gpu',
            sub_ass_override='force',
            sub_ass_force_style='ScaledBorderAndShadow=yes',
            sub_font='Consolas',
            sub_font_size=36,
            sub_color='#00f3ff',
            sub_border_color='#000000',
            sub_border_size=2,
            sub_shadow_color='#000000',
            sub_shadow_offset=1,
            osd_font='Consolas',
            osd_blur=2,
            osd_border_size=3,
            osd_margin_y=45,
        )
        
        try:
            self.player.sub_use_osd = True
        except AttributeError:
            self.player._set_property('sub-use-osd', 'yes')
        
        self._file_loaded.connect(self.update_sub_styles)
        self._sub_ready.connect(self._apply_pending_sub)
        self._sub_ready.connect(self.update_sub_styles)

        def _on_track_list_change(name, value):
            if value and any(t.get('type') == 'sub' for t in (value or [])):
                self._sub_ready.emit()

        self.player.observe_property('track-list', _on_track_list_change)
        self._on_track_list_cb = _on_track_list_change

        @self.player.event_callback('file-loaded')
        def _on_file_loaded(_event):
            self._file_loaded.emit()
        self._on_file_loaded_cb = _on_file_loaded

        last_played_media = self.load_configuration_memory()
        self.update_sub_styles()

        # Apply saved speed
        speed = self.speed_steps[self.speed_index]
        self.speed_btn.setText(f"{speed}x")
        try:
            self.player.speed = speed
        except Exception:
            pass 
        
        self.current_volume = max(0, min(100, int(self.current_volume)))
        self.volume_slider.setValue(self.current_volume)
        self.volume_label.setText(f"VOL: {self.current_volume}%")
        try:
            self.player.volume = float(self.calculate_boosted_volume(self.current_volume))
        except Exception as e:
            print(f"Volume init error: {e}")
        
        # Global Hotkeys
        self.shortcut_right = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        self.shortcut_right.activated.connect(self.skip_forward)
        self.shortcut_left = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        self.shortcut_left.activated.connect(self.skip_backward)
        self.shortcut_space = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.shortcut_space.activated.connect(self.toggle_play)
        
        # Main UI Refresh Clock loop
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_timeline)
        self.timer.start()

        # Throttled save — flushes at most every 5s during playback
        self._save_dirty = False
        self._save_throttle = QTimer(self)
        self._save_throttle.setSingleShot(True)
        self._save_throttle.setInterval(5000)
        self._save_throttle.timeout.connect(self._do_save)
        
        # If launched via "Open With" (sys.argv), skip restoring last session —
        # the argv file will be played directly from __main__ instead.
        if len(sys.argv) > 1:
            self.is_initializing = False
        elif last_played_media and os.path.exists(last_played_media):
            QTimer.singleShot(300, lambda: self.play_file(last_played_media))
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
        side_panel.setMinimumWidth(160)
        side_panel.setMaximumWidth(260)
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(12, 12, 12, 12)
        side_layout.setSpacing(8)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("GLOBAL SEARCH...")
        self.search_bar.textChanged.connect(self.filter_files)
        self.search_bar.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        side_layout.addWidget(self.search_bar)
        
        media_header = QHBoxLayout()
        lbl_media = QLabel("// MEDIA VAULT")
        lbl_media.setProperty("class", "PanelTitle")
        media_header.addWidget(lbl_media)
        media_header.addStretch()
        load_media_btn = QPushButton("+ LOAD")
        load_media_btn.setFixedHeight(22)
        load_media_btn.setStyleSheet("font-size: 10px; padding: 2px 8px;")
        load_media_btn.clicked.connect(self.load_media)
        media_header.addWidget(load_media_btn)
        side_layout.addLayout(media_header)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.file_list.itemDoubleClicked.connect(self.play_from_list)
        self.file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(
            lambda pos: self._show_vault_context_menu(pos, self.file_list, 'media')
        )
        side_layout.addWidget(self.file_list)

        subs_header = QHBoxLayout()
        lbl_subs = QLabel("// SUBTITLE VAULT")
        lbl_subs.setProperty("class", "PanelTitle")
        subs_header.addWidget(lbl_subs)
        subs_header.addStretch()
        clear_subs_btn = QPushButton("✕ OFF")
        clear_subs_btn.setFixedHeight(22)
        clear_subs_btn.setStyleSheet("font-size: 10px; padding: 2px 8px; color: #ff00ea; border-color: rgba(255, 0, 234, 0.4);")
        clear_subs_btn.setToolTip("Disable subtitles for this video")
        clear_subs_btn.clicked.connect(self.clear_subtitle)
        subs_header.addWidget(clear_subs_btn)
        load_subs_btn = QPushButton("+ LOAD")
        load_subs_btn.setFixedHeight(22)
        load_subs_btn.setStyleSheet("font-size: 10px; padding: 2px 8px;")
        load_subs_btn.clicked.connect(self.load_subtitle)
        subs_header.addWidget(load_subs_btn)
        side_layout.addLayout(subs_header)

        self.sub_list = QListWidget()
        self.sub_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.sub_list.itemDoubleClicked.connect(self.play_sub_from_list)
        self.sub_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sub_list.customContextMenuRequested.connect(
            lambda pos: self._show_vault_context_menu(pos, self.sub_list, 'subtitle')
        )
        side_layout.addWidget(self.sub_list)
        
        main_layout.addWidget(side_panel)
        
        # --- RIGHT VIEWER ---
        right_widget = QWidget()
        right_widget.setStyleSheet("background-color: #000000;")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        self.title_bar = QWidget()
        title_bar = self.title_bar
        title_bar.setObjectName("TitleBar")
        title_bar.setFixedHeight(35)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 0, 0, 0)
        
        title_text = QLabel("SYS.PLAYER // DECK 01")
        title_text.setObjectName("TitleText")
        title_layout.addWidget(title_text)
        
        title_layout.addStretch()

        about_btn = QPushButton("ℹ")
        about_btn.setObjectName("MaximizeBtn")
        about_btn.setFixedSize(45, 35)
        about_btn.setToolTip("About")
        about_btn.clicked.connect(self.show_about)
        title_layout.addWidget(about_btn)

        minimize_btn = QPushButton("─")
        minimize_btn.setObjectName("MaximizeBtn")
        minimize_btn.setFixedSize(45, 35)
        minimize_btn.setToolTip("Minimize")
        minimize_btn.clicked.connect(self._minimize)
        title_layout.addWidget(minimize_btn)

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
        self.viewport_container.setStyleSheet("background-color: #000000;")
        self.viewport_container.mousePressEvent = lambda e: self.toggle_play() if e.button() == Qt.MouseButton.LeftButton and not getattr(self, '_is_switching', False) else None
        viewport_layout = QVBoxLayout(self.viewport_container)
        self.viewport_container.setContentsMargins(0, 0, 0, 0)
        viewport_layout.setSpacing(0)
        
        self.video_frame = QWidget()
        self.video_frame.setStyleSheet("background-color: #000000;")
        self.video_frame.mousePressEvent = lambda e: self.toggle_play() if e.button() == Qt.MouseButton.LeftButton and not getattr(self, '_is_switching', False) else None
        
        video_overlay_layout = QVBoxLayout(self.video_frame)
        video_overlay_layout.addStretch()

        viewport_layout.addWidget(self.video_frame, stretch=1)
        
        # --- FLOATING BOTTOM BAR DECK ---
        self.bottom_bar = QWidget(self.viewport_container)
        self.bottom_bar.setObjectName("BottomBar")

        # Pause/play flash overlay — floats over viewport_container, above mpv's render surface
        # Pause overlay must be a separate top-level window to render transparently
        # over mpv's native render surface (airspace problem — Qt can't alpha-blend
        # over a foreign GPU surface, but the OS compositor can blend two windows).
        self.pause_overlay = QLabel(None, 
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.pause_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pause_overlay.setStyleSheet(
            "color: white; font-size: 64px; font-weight: bold; background: transparent;"
        )
        self.pause_overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.pause_overlay.setFixedSize(100, 100)
        self.pause_overlay.hide()

        self.bottom_bar.setFixedHeight(85)
        bottom_layout = QVBoxLayout(self.bottom_bar)
        bottom_layout.setContentsMargins(20, 5, 20, 15)
        bottom_layout.setSpacing(8)
        
        self.slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0) 
        self.slider.sliderMoved.connect(self.preview_time)
        self.slider.sliderReleased.connect(self.apply_video_position)
        bottom_layout.addWidget(self.slider)
        
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(6)

        self.play_btn = QPushButton()
        self.play_btn.setObjectName("PlayBtn")
        self.play_btn.setFixedSize(32, 28)
        self.set_vector_icon(self.play_btn, SVG_PLAY)
        self.play_btn.clicked.connect(self.toggle_play)
        controls_layout.addWidget(self.play_btn)

        self.time_label = QLabel("00:00:00 / 00:00:00")
        self.time_label.setObjectName("TimeLabel")
        controls_layout.addWidget(self.time_label)

        self.volume_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setObjectName("VolumeSlider")
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.sliderMoved.connect(self.adjust_system_volume)
        controls_layout.addWidget(self.volume_slider)

        self.volume_label = QLabel("VOL: 100%")
        self.volume_label.setObjectName("VolumeLabel")
        controls_layout.addWidget(self.volume_label)

        controls_layout.addStretch(1)

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

        controls_layout.addStretch(1)

        speed_label = QLabel("SPD:")
        speed_label.setObjectName("TimeLabel")
        controls_layout.addWidget(speed_label)

        self.speed_btn = QPushButton("1.0x")
        self.speed_btn.setFixedWidth(52)
        self.speed_btn.setToolTip("Playback speed")
        self.speed_btn.clicked.connect(self.show_speed_menu)
        controls_layout.addWidget(self.speed_btn)

        controls_layout.addStretch(1)

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
            saved_speed = memory.get("playback_speed", 1.0)
            if saved_speed in self.speed_steps:
                self.speed_index = self.speed_steps.index(saved_speed) 
            
            raw_positions = memory.get("playback_positions", {})
            self.playback_positions = {k.lower().replace('\\', '/'): v for k, v in raw_positions.items()}
            
            raw_subs_map = memory.get("custom_subs_map", {})
            self.custom_subs_map = {
                k.lower().replace('\\', '/'): (v if v == "none" else v.lower().replace('\\', '/'))
                for k, v in raw_subs_map.items()
            }
            
            for path in memory.get("media_files_playlist", []):
                norm_path = path.lower().replace('\\', '/')
                if os.path.exists(norm_path) and norm_path not in self.media_files:
                    self.media_files.append(norm_path)
                    self._add_playlist_item(self.file_list, norm_path)
                    
            for path in memory.get("subtitle_files_playlist", []):
                norm_path = path.lower().replace('\\', '/')
                if os.path.exists(norm_path) and norm_path not in self.subtitle_files:
                    self.subtitle_files.append(norm_path)
                    self._add_playlist_item(self.sub_list, norm_path)
            
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
            except Exception as e:
                print(f"Config disk read error: {e}")

        disk_positions = {k.lower().replace('\\', '/'): v for k, v in on_disk_memory.get("playback_positions", {}).items()}
        disk_positions.update(self.playback_positions)
        
        disk_subs_map = {
            k.lower().replace('\\', '/'): (v if v == "none" else v.lower().replace('\\', '/'))
            for k, v in on_disk_memory.get("custom_subs_map", {}).items()
        }
        disk_subs_map.update(self.custom_subs_map)

        memory_payload = {
            "font_family": self.current_sub_font,
            "font_size": self.current_sub_size,
            "font_color": self.current_sub_color,
            "system_volume_level": int(self.current_volume),
            "playback_speed": self.speed_steps[self.speed_index], 
            "last_active_media_file": self.active_media_path if self.active_media_path else on_disk_memory.get("last_active_media_file", None),
            "media_files_playlist": self.media_files,
            "subtitle_files_playlist": self.subtitle_files,
            "custom_subs_map": disk_subs_map,
            "playback_positions": disk_positions
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(memory_payload, f, indent=4)
        except Exception as e:
            print(f"Memory write breakdown loop: {e}")

    def _schedule_save(self):
        """Queue a save — fires after 5s of inactivity, avoiding rapid writes during playback."""
        self._save_dirty = True
        if not self._save_throttle.isActive():
            self._save_throttle.start()

    def _do_save(self):
        if self._save_dirty:
            self._save_dirty = False
            self.save_configuration_memory()

    def safely_handle_app_exit(self):
        self._save_throttle.stop()
        self.save_configuration_memory()  # flush immediately on exit
        self.close()

    def calculate_boosted_volume(self, value):
        if value <= 0:
            return 0.0
        return min(150.0, round(150.0 * math.log(1 + value) / math.log(101), 2))

    def adjust_system_volume(self, value):
        try:
            self.current_volume = int(value) 
            self.volume_label.setText(f"VOL: {self.current_volume}%")
            self.player.volume = float(self.calculate_boosted_volume(self.current_volume))
            self.save_configuration_memory()
        except Exception as e:
            print(f"Volume adjust error: {e}")

    def adjust_sub_size(self, delta):
        self.current_sub_size = max(12, min(72, self.current_sub_size + delta))
        self.update_sub_styles()
        self.save_configuration_memory()

    def open_color_dialog(self):
        self.timer.stop()
        parent = self
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
        parent = self
        dialog = QFontDialog(parent)
        dialog.setOption(QFontDialog.FontDialogOption.DontUseNativeDialog, True)
        dialog.setOption(QFontDialog.FontDialogOption.ScalableFonts, True)
        dialog.setCurrentFont(QFont(self.current_sub_font, self.current_sub_size))
        dialog.setWindowTitle("SELECT SUBTITLE FONT")
        # Hide style options that don't apply to mpv subtitles
        for widget in dialog.findChildren(QWidget):
            label_text = widget.property("text") or ""
            if hasattr(widget, "text") and callable(widget.text):
                label_text = widget.text()
            if label_text in ("Underline", "Strikeout"):
                widget.hide()
                widget.setEnabled(False)
        
        if dialog.exec():
            selected_font = dialog.selectedFont()
            self.current_sub_font = selected_font.family().strip("'\"")
            self.update_sub_styles()
            self.save_configuration_memory()
            
        self.timer.start()

    def update_sub_styles(self):
        color = self.current_sub_color
        for prop, val in [
            ('sub-ass-override',    'force'),
            ('sub-ass-force-style', 'ScaledBorderAndShadow=yes'),
            ('sub-font',            self.current_sub_font),
            ('sub-font-size',    int(self.current_sub_size)),
            ('sub-color',        color),
            ('sub-border-color', '#000000'),
            ('sub-border-size',  2.0),
            ('sub-shadow-color', '#000000'),
            ('sub-shadow-offset',1.0),
            ('osd-font',         self.current_sub_font),
            ('osd-font-size',    int(self.current_sub_size)),
            ('osd-color',        color),
            ('osd-border-color', '#000000'),
            ('osd-border-size',  1.0),
        ]:
            try:
                self.player[prop] = val
            except Exception as e:
                print(f"Sub style error {prop}: {e}")
        


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
                    import math
                    scaled_max = math.ceil(dur * 100)
                    # Snap to end if within 0.5s — mpv's last decoded frame
                    # is always slightly behind the container duration
                    at_end = (dur - pos) < 0.05
                    display_pos = dur if at_end else pos
                    scaled_pos = scaled_max if at_end else int(pos * 100)
                    
                    if self.slider.maximum() != scaled_max:
                        self.slider.setRange(0, scaled_max)
                        
                    self.slider.blockSignals(True)
                    self.slider.setValue(scaled_pos)
                    self.slider.blockSignals(False)
                    self.time_label.setText(f"{self.format_time(display_pos)} / {self.format_time(dur)}")
                    self.time_label.setToolTip(f"{pos:.3f}s / {dur:.3f}s")
                    
                    if self.active_media_path and not self.is_initializing:
                        self.playback_positions[self.active_media_path] = pos
                        self._schedule_save()
            except:
                pass


    def skip_forward(self):
        if self.player.time_pos is not None: self.player.time_pos += 5.0

    def skip_backward(self):
        if self.player.time_pos is not None: self.player.time_pos = max(0.0, self.player.time_pos - 5.0)

    def show_speed_menu(self):
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #0a0a0a; border: 1px solid #00f3ff; color: #00f3ff; font-family: Consolas; font-size: 12px; }
            QMenu::item { padding: 6px 24px; }
            QMenu::item:selected { background-color: rgba(0, 243, 255, 0.15); color: #ffffff; }
            QMenu::item:checked { color: #ff00ea; font-weight: bold; }
        """)
        current_speed = self.speed_steps[self.speed_index]
        for speed in self.speed_steps:
            label = f"{'▶  ' if speed == current_speed else '    '}{speed}x"
            action = QAction(label, self)
            action.setData(speed)
            action.triggered.connect(lambda checked, s=speed: self.set_playback_speed(s))
            menu.addAction(action)
        menu.exec(self.speed_btn.mapToGlobal(self.speed_btn.rect().bottomLeft()))

    def set_playback_speed(self, speed):
        self.speed_index = self.speed_steps.index(speed)
        try:
            self.player.speed = speed
        except Exception as e:
            print(f"Speed change error: {e}")
        self.speed_btn.setText(f"{speed}x")
        self.save_configuration_memory()

    def format_time(self, total_seconds):
        if total_seconds is None: return "00:00:00"
        total_seconds = int(total_seconds)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

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
        except Exception:
            pass

    def load_media(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select Media", "", 
            "Media Files (*.mp4 *.m4v *.mkv *.avi *.mov *.wmv *.asf *.flv *.f4v *.webm "
            "*.ts *.mts *.m2ts *.mpeg *.mpg *.m2v *.ogv *.ogg *.3gp *.3g2 *.divx "
            "*.rmvb *.rm *.vob *.m4b "
            "*.mp3 *.flac *.wav *.aac *.m4a *.oga *.opus *.wma *.aiff *.aif "
            "*.alac *.dts *.ac3 *.eac3 *.ape *.mka *.mp2 *.dsf *.dff);;"
            "Video (*.mp4 *.m4v *.mkv *.avi *.mov *.wmv *.asf *.flv *.f4v *.webm "
            "*.ts *.mts *.m2ts *.mpeg *.mpg *.m2v *.ogv *.ogg *.3gp *.3g2 *.divx *.rmvb *.rm *.vob *.m4b);;"
            "Audio (*.mp3 *.flac *.wav *.aac *.m4a *.oga *.opus *.wma *.aiff *.aif "
            "*.alac *.dts *.ac3 *.eac3 *.ape *.mka *.mp2 *.dsf *.dff);;"
            "All Files (*.*)"
        )
        if filepath:
            self.play_file(filepath)

    def _add_playlist_item(self, list_widget, full_path):
        """Add item to list widget with full path stored in UserRole to avoid name collisions."""
        from PyQt6.QtWidgets import QListWidgetItem
        item = QListWidgetItem(os.path.basename(full_path))
        item.setData(Qt.ItemDataRole.UserRole, full_path)
        list_widget.addItem(item)

    def add_to_playlist(self, filepath):
        norm_path = filepath.lower().replace('\\', '/')
        if norm_path not in self.media_files:
            self.media_files.append(norm_path)
            self._add_playlist_item(self.file_list, norm_path)
            
            if not self.is_initializing:
                self.save_configuration_memory()

    def play_from_list(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.play_file(path)

    def load_subtitle(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select Subtitle", "", "Subtitles (*.srt *.ass *.vtt)")
        if filepath:
            self.add_subtitle_to_playlist(filepath)
            self.load_subtitle_from_path(filepath)

    def add_subtitle_to_playlist(self, filepath):
        norm_path = filepath.lower().replace('\\', '/')
        if norm_path not in self.subtitle_files:
            self.subtitle_files.append(norm_path)
            self._add_playlist_item(self.sub_list, norm_path)
            self.save_configuration_memory()

    def play_sub_from_list(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.load_subtitle_from_path(path)

    def load_subtitle_from_path(self, filepath):
        norm_path = filepath.lower().replace('\\', '/')
        if os.path.exists(norm_path):
            try:
                self.player.sub_add(norm_path)
                self._highlight_active_sub(norm_path)
                if self.active_media_path:
                    self.custom_subs_map[self.active_media_path] = norm_path
                    self.save_configuration_memory()
            except Exception as e:
                print(f"Subtitle load error: {e}")
        else:
            print(f"Subtitle file not found: {norm_path}")

    def clear_subtitle(self):
        """Disable subtitles for the current video and persist that choice."""
        try:
            self.player._set_property('sid', 'no')
        except Exception as e:
            print(f"Subtitle clear error: {e}")
        self._highlight_active_sub(None)
        if self.active_media_path:
            self.custom_subs_map[self.active_media_path] = "none"
            self.save_configuration_memory()

    def play_file(self, filepath):
        self.is_initializing = True
        self.is_awaiting_resume = False
        self.pending_resume_seconds = 0.0
        self._is_switching = True
        self._user_paused = False
        self.pause_overlay.hide()
        
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
            except Exception as e:
                print(f"Position save error: {e}")
            
        self.active_media_path = norm_path
        self._highlight_active_media(norm_path)

        # Determine subtitle to load
        if norm_path in self.custom_subs_map:
            saved_sub_path = self.custom_subs_map[norm_path]
        else:
            saved_sub_path = "auto"

        try:
            if saved_sub_path == "none":
                self.player.loadfile(norm_path, 'replace', sid='no', sub_auto='no')
            elif saved_sub_path == "auto":
                self.player.loadfile(norm_path, 'replace', sub_auto='fuzzy')
            else:
                self.player.loadfile(norm_path, 'replace', sub_file=saved_sub_path)
            self.player.pause = False
            self.set_vector_icon(self.play_btn, SVG_PAUSE)
            self.pause_overlay.hide()
            self._is_switching = False
        except Exception as e:
            print(f"Decoder re-allocation anomaly: {e}")

        self._pending_sub = None  # no longer needed
        self._highlight_active_sub(None if saved_sub_path in ("none", "auto") else saved_sub_path)
        self.update_sub_styles()

        # Check if the database lookup position is validly past 0.5s
        if target_timestamp > 0.5:
            self.pending_resume_seconds = target_timestamp
            self.is_awaiting_resume = True
        else:
            self.is_initializing = False

        self.handle_visual_frame_adjustments(norm_path)
        self.save_configuration_memory()

    def _apply_pending_sub(self):
        """Called after file-loaded — only used for manual sub selections now.
        Initial sub loading is handled atomically via loadfile options."""
        action = self._pending_sub
        if action is None:
            return
        self._pending_sub = None
        if action == "none":
            try:
                self.player['sub-auto'] = 'no'
                self.player['sid'] = 'no'
            except Exception:
                pass
            self._highlight_active_sub(None)
        elif action == "auto":
            try:
                self.player['sub-auto'] = 'fuzzy'
            except Exception:
                pass
            self._highlight_active_sub(None)
        else:
            try:
                self.player['sub-auto'] = 'fuzzy'
            except Exception:
                pass
            self.load_subtitle_from_path(action)

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
        except Exception as e:
            print(f"Pause error: {e}")
        time_str = self.format_time(target_seconds)
        
        parent = self
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
        except Exception as e:
            print(f"Resume seek error: {e}")
            
        self.set_vector_icon(self.play_btn, SVG_PAUSE)
        self.is_awaiting_resume = False 
        self.is_initializing = False 

    def _is_at_end(self):
        """Returns True if playback has reached the end of the file."""
        try:
            pos = self.player.time_pos
            dur = self.player.duration
            if pos is None or dur is None or dur == 0:
                return False
            return (dur - pos) < 0.05
        except:
            return False

    def _reposition_pause_overlay(self):
        if not hasattr(self, 'pause_overlay'):
            return
        size = 100
        vc = self.viewport_container
        bar_height = self.bottom_bar.height() if hasattr(self, 'bottom_bar') else 0
        video_height = vc.height() - bar_height
        # Map to global coords since overlay is a top-level window
        global_pos = vc.mapToGlobal(vc.rect().topLeft())
        self.pause_overlay.move(
            global_pos.x() + (vc.width() - size) // 2,
            global_pos.y() + (video_height - size) // 2,
        )

    def moveEvent(self, event):
        super().moveEvent(event)
        self._reposition_pause_overlay()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_pause_overlay()
        if hasattr(self, 'pause_overlay') and self.pause_overlay.isVisible():
            self.pause_overlay.raise_()

    def _flash_overlay(self, is_paused):
        self._reposition_pause_overlay()
        if is_paused and self._user_paused and not self._is_switching:
            self.pause_overlay.setText("| |")
            self.pause_overlay.raise_()
            self.pause_overlay.show()
        else:
            self.pause_overlay.hide()

    def toggle_play(self):
        try:
            if self._is_at_end():
                self.player.time_pos = 0.0
                self.player.pause = False
                self.set_vector_icon(self.play_btn, SVG_PAUSE)
                self._user_paused = False
                self._flash_overlay(False)
            elif not self.player.pause:
                self.player.pause = True
                self.set_vector_icon(self.play_btn, SVG_PLAY)
                self._user_paused = True
                self._flash_overlay(True)
            else:
                self.player.pause = False
                self.set_vector_icon(self.play_btn, SVG_PAUSE)
                self._user_paused = False
                self._flash_overlay(False)
        except Exception as e:
            print(f"Toggle play error: {e}")

    def show_about(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("SYS.INFO // ABOUT")
        dialog.setText(
            "<div style='font-family: Consolas; color: #00f3ff;'>"
            "<p style='font-size: 15px; font-weight: bold; color: #ff00ea;'>CyberPlayer</p>"
            "<p style='color: #888; font-size: 11px;'>A cyberpunk-styled media player<br>"
            "built with Python, PyQt6 &amp; mpv.</p>"
            "<hr style='border-color: #1a1a1a;'/>"
            "<p style='font-size: 11px; color: #555;'>"
            "<a href='https://www.flaticon.com/free-icons/play-button' style='color: #00f3ff;'>Play button icon</a>"
            " by <a href='https://www.flaticon.com/authors/freepik' style='color: #00f3ff;'>Freepik</a>"
            " via <a href='https://www.flaticon.com' style='color: #00f3ff;'>Flaticon</a>"
            "</p>"
            "</div>"
        )
        dialog.setTextFormat(Qt.TextFormat.RichText)
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        dialog.setStyleSheet("""
            QMessageBox { background-color: #0a0a0a; border: 1px solid #ff00ea; min-width: 320px; }
            QMessageBox QLabel { color: #00f3ff; font-family: Consolas; }
            QMessageBox QPushButton { color: #00f3ff; border: 1px solid #00f3ff; padding: 4px 20px; font-family: Consolas; }
            QMessageBox QPushButton:hover { background-color: rgba(0, 243, 255, 0.1); }
        """)
        dialog.exec()

    def _hide_controls(self):
        if self.video_fs_window is None:
            return
        self._controls_anim = QPropertyAnimation(self._controls_opacity, b"opacity")
        self._controls_anim.setDuration(300)
        self._controls_anim.setStartValue(1.0)
        self._controls_anim.setEndValue(0.0)
        self._controls_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._controls_anim.start()
        self.setCursor(Qt.CursorShape.BlankCursor)

    def _show_controls(self):
        self._controls_hide_timer.stop()
        if self._controls_opacity.opacity() == 1.0 and self.cursor().shape() != Qt.CursorShape.BlankCursor:
            return
        self.setCursor(Qt.CursorShape.ArrowCursor)
        if self._controls_opacity.opacity() == 1.0:
            return
        self._controls_anim = QPropertyAnimation(self._controls_opacity, b"opacity")
        self._controls_anim.setDuration(150)
        self._controls_anim.setStartValue(self._controls_opacity.opacity())
        self._controls_anim.setEndValue(1.0)
        self._controls_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._controls_anim.start()

    def _reset_controls_timer(self):
        if self.video_fs_window is None:
            return
        self._show_controls()
        self._controls_hide_timer.start()

    def _minimize(self):
        if self.video_fs_window:
            self._exit_video_fullscreen()
        self.pause_overlay.hide()
        self.showMinimized()

    def changeEvent(self, event):
        super().changeEvent(event)
        if hasattr(self, 'pause_overlay'):
            from PyQt6.QtCore import QEvent
            if event.type() == QEvent.Type.WindowStateChange:
                if self.isMinimized():
                    self.pause_overlay.hide()
                elif self._user_paused:
                    self._reposition_pause_overlay()
                    self.pause_overlay.show()
            elif event.type() == QEvent.Type.ActivationChange:
                if not self.isActiveWindow():
                    self.pause_overlay.hide()
                elif self._user_paused:
                    self._reposition_pause_overlay()
                    self.pause_overlay.show()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def toggle_video_fullscreen(self):
        if self.video_fs_window is not None:
            QTimer.singleShot(0, self._exit_video_fullscreen)
        else:
            self._enter_video_fullscreen()

    def _enter_video_fullscreen(self):
        # Capture window state FIRST before anything changes it
        # Frameless windows don't report isMaximized() correctly.
        # Detect by comparing geometry to available screen geometry.
        screen_geom = QApplication.primaryScreen().availableGeometry()
        self._pre_fs_maximized = self.geometry() == screen_geom
        self.video_fs_window = True

        # Hide side panel and title bar, keep only the video area
        self.centralWidget().layout().itemAt(0).widget().hide()  # side panel
        self.title_bar.hide()

        # Wire auto-hide controls — install event filter on app so mouse moves
        # anywhere in the window trigger the controls, regardless of which child
        # widget is under the cursor.
        self.bottom_bar.setGraphicsEffect(self._controls_opacity)
        self._controls_opacity.setOpacity(1.0)
        self.setMouseTracking(True)
        self.centralWidget().setMouseTracking(True)
        self.viewport_container.setMouseTracking(True)
        self.video_frame.setMouseTracking(True)
        self.bottom_bar.setMouseTracking(True)

        from PyQt6.QtCore import QObject, QEvent as QEv
        class _FsMouseFilter(QObject):
            def eventFilter(self_, obj, event):
                if event.type() == QEv.Type.MouseMove:
                    self._reset_controls_timer()
                return False
        self._fs_mouse_filter = _FsMouseFilter(self)
        QApplication.instance().installEventFilter(self._fs_mouse_filter)

        # Escape to exit
        from PyQt6.QtGui import QShortcut
        self._fs_esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._fs_esc.activated.connect(self._exit_video_fullscreen)
        self._fs_space = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self._fs_space.activated.connect(self.toggle_play)
        self.shortcut_space.setEnabled(False)

        self._reset_controls_timer()
        self.showFullScreen()
        QTimer.singleShot(50, self._reposition_pause_overlay)

    def _exit_video_fullscreen(self):
        if self.video_fs_window is None:
            return

        self.video_fs_window = None

        # Restore side panel and title bar
        self.centralWidget().layout().itemAt(0).widget().show()  # side panel
        self.title_bar.show()

        # Clean up auto-hide
        self._controls_hide_timer.stop()
        if self._controls_anim is not None:
            self._controls_anim.stop()
            self._controls_anim = None
        self.bottom_bar.setGraphicsEffect(None)
        self._controls_opacity = QGraphicsOpacityEffect()
        self._controls_opacity.setOpacity(1.0)

        # Remove fullscreen mouse/keyboard overrides
        if hasattr(self, '_fs_mouse_filter'):
            QApplication.instance().removeEventFilter(self._fs_mouse_filter)
            self._fs_mouse_filter = None
        self.setMouseTracking(False)
        self.viewport_container.setMouseTracking(False)
        self.video_frame.setMouseTracking(False)
        self.bottom_bar.setMouseTracking(False)
        try:
            del self.viewport_container.mouseMoveEvent
        except AttributeError:
            pass
        if hasattr(self, '_fs_esc'):
            self._fs_esc.deleteLater()
            self._fs_space.deleteLater()
        self.shortcut_space.setEnabled(True)
        self.setCursor(Qt.CursorShape.ArrowCursor)

        if getattr(self, '_pre_fs_maximized', False):
            self.showFullScreen()
        else:
            self.showNormal()
        self._reposition_pause_overlay()

    def _show_vault_context_menu(self, pos, list_widget, vault_type):
        item = list_widget.itemAt(pos)
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)

        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #0a0a0a; border: 1px solid #00f3ff; color: #00f3ff; font-family: Consolas; font-size: 12px; }
            QMenu::item { padding: 6px 24px; }
            QMenu::item:selected { background-color: rgba(0, 243, 255, 0.15); color: #ffffff; }
        """)
        remove_action = QAction("✕  Remove from vault", self)
        remove_action.triggered.connect(lambda: self._remove_from_vault(path, item, list_widget, vault_type))
        menu.addAction(remove_action)
        menu.exec(list_widget.mapToGlobal(pos))

    def _remove_from_vault(self, path, item, list_widget, vault_type):
        list_widget.takeItem(list_widget.row(item))
        if vault_type == 'media':
            if path in self.media_files:
                self.media_files.remove(path)
            if path in self.custom_subs_map:
                del self.custom_subs_map[path]
            if path == self.active_media_path:
                self.active_media_path = None
        else:
            if path in self.subtitle_files:
                self.subtitle_files.remove(path)
            # If this sub is currently active, clear it
            if self.active_media_path and self.custom_subs_map.get(self.active_media_path) == path:
                self.clear_subtitle()
            # Remove from custom_subs_map if it was mapped to any video
            keys_to_update = [k for k, v in self.custom_subs_map.items() if v == path]
            for k in keys_to_update:
                del self.custom_subs_map[k]
        self.save_configuration_memory()

    def _highlight_active_media(self, active_path):
        """Bold and colour the active media entry in the vault; reset all others."""
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            stored = item.data(Qt.ItemDataRole.UserRole)
            if active_path and stored == active_path:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setForeground(QColor("#ff00ea"))
            else:
                font = item.font()
                font.setBold(False)
                item.setFont(font)
                item.setForeground(QColor("#888888"))

    def _highlight_active_sub(self, active_path):
        """Bold and colour the active subtitle entry in the vault; reset all others."""
        for i in range(self.sub_list.count()):
            item = self.sub_list.item(i)
            stored = item.data(Qt.ItemDataRole.UserRole)
            if active_path and stored == active_path:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setForeground(QColor("#ff00ea"))
            else:
                font = item.font()
                font.setBold(False)
                item.setFont(font)
                item.setForeground(QColor("#888888"))

    def filter_files(self, text):
        search_query = text.lower()
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            item.setHidden(search_query not in item.text().lower())
        for i in range(self.sub_list.count()):
            item = self.sub_list.item(i)
            item.setHidden(search_query not in item.text().lower())

    def _get_resize_edge(self, pos):
        m = 6
        x, y, w, h = pos.x(), pos.y(), self.width(), self.height()
        left, right, top, bottom = x < m, x > w - m, y < m, y > h - m
        if top and left:   return 'tl'
        if top and right:  return 'tr'
        if bottom and left: return 'bl'
        if bottom and right: return 'br'
        if top:    return 't'
        if bottom: return 'b'
        if left:   return 'l'
        if right:  return 'r'
        return None

    def _edge_cursor(self, edge):
        return {
            'tl': Qt.CursorShape.SizeFDiagCursor, 'br': Qt.CursorShape.SizeFDiagCursor,
            'tr': Qt.CursorShape.SizeBDiagCursor, 'bl': Qt.CursorShape.SizeBDiagCursor,
            't':  Qt.CursorShape.SizeVerCursor,   'b':  Qt.CursorShape.SizeVerCursor,
            'l':  Qt.CursorShape.SizeHorCursor,   'r':  Qt.CursorShape.SizeHorCursor,
        }.get(edge, Qt.CursorShape.ArrowCursor)

    def _handle_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.isFullScreen():
            pos = self.mapFromGlobal(event.globalPosition().toPoint())
            edge = self._get_resize_edge(pos)
            if edge:
                self._resize_edge = edge
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geom = self.geometry()
                self.oldPos = None
                return True
            else:
                self._resize_edge = None
                title_bar_rect = self.title_bar.rect().translated(
                    self.title_bar.mapTo(self, self.title_bar.rect().topLeft()))
                self.oldPos = event.globalPosition().toPoint() if title_bar_rect.contains(pos) else None
        return False

    def _handle_mouse_move(self, event):
        if self.isFullScreen():
            return
        pos = self.mapFromGlobal(event.globalPosition().toPoint())
        gpos = event.globalPosition().toPoint()
        if self._resize_edge and self._resize_start_pos and self._resize_start_geom:
            dx = gpos.x() - self._resize_start_pos.x()
            dy = gpos.y() - self._resize_start_pos.y()
            g = self._resize_start_geom
            x, y, w, h = g.x(), g.y(), g.width(), g.height()
            minw, minh = self.minimumWidth(), self.minimumHeight()
            e = self._resize_edge
            if 'r' in e: w = max(minw, w + dx)
            if 'b' in e: h = max(minh, h + dy)
            if 'l' in e:
                new_w = max(minw, w - dx)
                x = x + (w - new_w)
                w = new_w
            if 't' in e:
                new_h = max(minh, h - dy)
                y = y + (h - new_h)
                h = new_h
            self.setGeometry(x, y, w, h)
        elif getattr(self, 'oldPos', None) is not None:
            delta = gpos - self.oldPos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = gpos
        else:
            edge = self._get_resize_edge(pos)
            self.setCursor(self._edge_cursor(edge) if edge else Qt.CursorShape.ArrowCursor)

    def _handle_mouse_release(self, event):
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geom = None
        self.oldPos = None
        self.setCursor(Qt.CursorShape.ArrowCursor)


# --- WINDOWS BOOTSTRAP INTERCEPTOR ---
if __name__ == '__main__':
    # Set AUMID before QApplication so Windows assigns the taskbar button
    # to this process and reads the icon from the embedded exe resource.
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u'CyberPlayer.App.1')
    except Exception:
        pass

    app = QApplication(sys.argv)

    # bundle_dir points to sys._MEIPASS when frozen (where icon.ico is extracted),
    # and to exe_dir in dev — this is the fix for the taskbar icon not showing.
    icon_path = os.path.join(bundle_dir, 'icon.ico')
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    app.setStyleSheet("""
        QToolTip {
            background-color: #0a0a0a;
            color: #00f3ff;
            border: 1px solid rgba(0, 243, 255, 0.4);
            font-family: 'Consolas';
            font-size: 11px;
            padding: 4px 8px;
        }
    """)
    player = CyberPlayer()
    if os.path.exists(icon_path):
        player.setWindowIcon(app_icon)
    player.show()

    if len(sys.argv) > 1:
        target_file = os.path.normpath(sys.argv[1]).lower().replace('\\', '/')
        if os.path.exists(target_file):
            QTimer.singleShot(250, lambda: player.play_file(target_file))

    sys.exit(app.exec())