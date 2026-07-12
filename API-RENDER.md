# CyberPlayer — Technical README (Render API Branch)

A cyberpunk-styled desktop media player built with Python, PyQt6, and libmpv. This document explains every system in the codebase, why each decision was made, and the problems each solution solves.

> **Branch note:** This is the render API branch. It uses `MpvRenderContext` instead of `wid=` embedding, enabling libplacebo quality upgrades. See section 7 and section 8 for the full explanation of what changed and why.
>
> **Stability recommendation:** For the most stable version of CyberPlayer, use the **[main branch](../../tree/main)**. The main branch uses `wid=` embedding with `vo='gpu'` — a simpler, proven architecture with no render loop complexity, no threading edge cases, and no audio subtitle workarounds. The quality difference is imperceptible for typical use (audiobooks, general video). This render API branch is recommended only if you specifically want libplacebo quality features (debanding, high-quality upscaling) and are comfortable with a less battle-tested codebase.

---

## Table of Contents

- [CyberPlayer — Technical README (Render API Branch)](#cyberplayer--technical-readme-render-api-branch)
  - [Table of Contents](#table-of-contents)
  - [1. Architecture Overview](#1-architecture-overview)
  - [2. Bootstrap and Path Anchoring](#2-bootstrap-and-path-anchoring)
  - [3. Stylesheet System](#3-stylesheet-system)
  - [4. ClickableSlider](#4-clickableslider)
  - [5. CyberPlayer Class — State Initialization](#5-cyberplayer-class--state-initialization)
  - [6. UI Layout](#6-ui-layout)
  - [7. Render API Architecture — MpvRenderContext](#7-render-api-architecture--mpvrendercontext)
    - [Why We Migrated](#why-we-migrated)
    - [MpvGLWidget](#mpvglwidget)
    - [What Broke Along the Way](#what-broke-along-the-way)
    - [Quality Upgrades Now Available](#quality-upgrades-now-available)
  - [7b. The Pause Overlay — Airspace Problem (Resolved)](#7b-the-pause-overlay--airspace-problem-resolved)
  - [8. MPV Engine Initialization](#8-mpv-engine-initialization)
  - [9. Subtitle Reliability — The Full Investigation](#9-subtitle-reliability--the-full-investigation)
    - [The Symptoms](#the-symptoms)
    - [What We Tried That Didn't Work](#what-we-tried-that-didnt-work)
    - [The `loadfile` Change](#the-loadfile-change)
  - [10. Thread Safety — Signals and the MPV Callback Problem](#10-thread-safety--signals-and-the-mpv-callback-problem)
  - [11. Configuration System](#11-configuration-system)
    - [Config File Structure](#config-file-structure)
    - [Path Normalization](#path-normalization)
    - [The `"none"` Sentinel](#the-none-sentinel)
    - [Throttled Saving](#throttled-saving)
    - [`is_initializing` Guard](#is_initializing-guard)
    - [Playlist as Source of Truth](#playlist-as-source-of-truth)
  - [12. Playback Engine](#12-playback-engine)
    - [`play_file(filepath)`](#play_filefilepath)
    - [Resume Dialog](#resume-dialog)
    - [`_is_at_end()`](#_is_at_end)
    - [Speed Control](#speed-control)
  - [13. Timeline and Seeking](#13-timeline-and-seeking)
    - [Slider Scale](#slider-scale)
    - [`blockSignals(True/False)`](#blocksignalstruefalse)
    - [End-of-file Snap](#end-of-file-snap)
    - [Dragging](#dragging)
  - [14. Volume System](#14-volume-system)
    - [Logarithmic Curve](#logarithmic-curve)
  - [15. Subtitle Controls](#15-subtitle-controls)
    - [Font and Color Dialogs](#font-and-color-dialogs)
    - [`update_sub_styles()`](#update_sub_styles)
    - [Size Bounds](#size-bounds)
    - [Subtitle Vault Memory](#subtitle-vault-memory)
  - [16. Video Fullscreen System](#16-video-fullscreen-system)
    - [Architecture Decision](#architecture-decision)
    - [Maximized State Detection](#maximized-state-detection)
    - [Auto-hide Controls](#auto-hide-controls)
    - [Shortcut Management](#shortcut-management)
  - [17. Window Management — Frameless Window](#17-window-management--frameless-window)
    - [Edge Resize Detection](#edge-resize-detection)
    - [App-level Event Filter](#app-level-event-filter)
    - [Dragging](#dragging-1)
    - [Minimum Size](#minimum-size)
  - [18. Vault System — Media and Subtitles](#18-vault-system--media-and-subtitles)
    - [Dual-panel Design](#dual-panel-design)
    - [Active Item Highlighting](#active-item-highlighting)
    - [Global Search](#global-search)
    - [Context Menu Removal](#context-menu-removal)
  - [19. Keyboard Shortcuts](#19-keyboard-shortcuts)
  - [20. Open With Support](#20-open-with-support)
  - [21. Audio File Visual Mode](#21-audio-file-visual-mode)
  - [21b. Audio Subtitle Overlay](#21b-audio-subtitle-overlay)
  - [22. Dependencies](#22-dependencies)
    - [Why python-mpv over alternatives](#why-python-mpv-over-alternatives)
  - [Known Limitations](#known-limitations)
  - [Memory Usage](#memory-usage)

---

## 1. Architecture Overview

CyberPlayer is a single-file Python application (`app.py`) with two classes:

- **`ClickableSlider`** — a subclass of `QSlider` that adds click-to-seek behavior, hover tooltips, and a mouse tracking callback hook.
- **`CyberPlayer`** — a `QMainWindow` subclass that contains the entire application.

The app uses **libmpv** (via `python-mpv`) as the media engine. mpv renders video directly to a native OS window handle (`winId()`), which means it bypasses Qt's paint system entirely. This has deep implications for how overlays and transparency work, detailed in section 7.

All persistent state is stored in a single `config.json` file next to `app.py`. There is no network activity, no telemetry, and no external services.

---

## 2. Bootstrap and Path Anchoring

```python
if getattr(sys, 'frozen', False):
    exe_dir = os.path.dirname(sys.executable)
else:
    exe_dir = os.path.dirname(os.path.abspath(__file__))

os.environ["PATH"] = exe_dir + os.pathsep + os.environ["PATH"]
CONFIG_FILE = os.path.join(exe_dir, "config.json")
```

**Why this exists:** When packaged with PyInstaller (`sys.frozen = True`), the executable directory is different from the script directory. `__file__` doesn't work reliably in frozen mode. The `getattr(sys, 'frozen', False)` check handles both development (running `app.py` directly) and distribution (running a compiled `.exe`).

**PATH injection:** libmpv needs to find its DLL (`mpv-2.dll` on Windows). Prepending `exe_dir` to `PATH` ensures mpv's DLL is found whether the app is run from the project folder or from any other working directory.

**CONFIG_FILE:** Anchored to `exe_dir` rather than the current working directory, so the config is always found next to the executable regardless of where the app is launched from.

---

## 3. Stylesheet System

The entire visual theme is defined in a single `STYLESHEET` string applied to `QMainWindow`. Key design decisions:

**Object name targeting (`#TitleBar`, `#SidePanel`, `#BottomBar`):** Qt's stylesheet system supports CSS-like ID selectors via `setObjectName()`. This lets us style specific widgets without affecting all widgets of that type.

**Class property targeting (`.PanelTitle`):** Qt also supports property-based selectors. `lbl.setProperty("class", "PanelTitle")` enables the `.PanelTitle {}` rule, which is used for the vault section headers.

**The bottom bar gradient:**
```css
background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
    stop:0 rgba(0,0,0,0),
    stop:0.4 rgba(5,5,5,0.85),
    stop:1 rgba(5,5,5,0.95));
```
The top is fully transparent so video shows through, fading to near-opaque at the bottom. This creates the "controls floating over video" effect without actually overlaying the controls on the video widget (which would cause the airspace problem described in section 7).

**Slider theming:** The timeline slider uses `#ff00ea` (magenta) for the played portion and `#00f3ff` (cyan) for the handle. The volume slider inverts this. They share the same `ClickableSlider` class but are distinguished by object name (`#VolumeSlider`).

**`QToolTip` styling in `app.setStyleSheet()`:** Qt's tooltip styling only applies reliably when set on the `QApplication` instance, not on individual widgets or the main window stylesheet. Setting it at the app level guarantees it applies globally before any widget is created.

**SVG icons:** Play and pause icons are stored as inline SVG bytes and rendered via `QSvgRenderer` into a `QPixmap`. This avoids external icon files and ensures the icons scale correctly at any DPI.

---

## 4. ClickableSlider

Standard `QSlider` in Qt has a frustrating behavior: clicking anywhere on the slider track moves to the nearest "step" rather than jumping directly to where you clicked. This is overridden in `ClickableSlider`.

**`_value_from_x(x)`:** Converts a mouse X coordinate to a slider value by linear interpolation across the slider's width. This gives exact click-to-position behavior.

**`mousePressEvent` / `mouseMoveEvent`:** Both call `_value_from_x` and emit `sliderMoved`, which is connected to the preview/seek handlers. `is_user_dragging` is set on press and cleared on release to prevent the timeline update loop from overwriting the slider position while the user is dragging.

**`setMouseTracking(True)`:** Makes Qt fire `mouseMoveEvent` even when no mouse button is held. Without this, the tooltip only appears while clicking, not on hover.

**Hover tooltip:**
```python
QToolTip.showText(
    event.globalPosition().toPoint(),
    self._format_time_fn(seconds),
    self,
    self.rect(),
    99999999
)
```
The fifth argument (`msecDisplayTime`) is set to a very large number so Qt's auto-hide timer never fires while the mouse is over the slider. `leaveEvent` calls `QToolTip.hideText()` to dismiss it when the mouse exits. `_format_time_fn` is injected from outside (`self.slider._format_time_fn = self.format_time`) rather than being hardcoded, keeping `ClickableSlider` reusable.

**`_on_hover_fn`:** A callback hook called on every `mouseMoveEvent`. The timeline slider wires this to `_reset_controls_timer` so that hovering over the slider in video fullscreen keeps the controls bar visible and prevents the cursor from hiding.

---

## 5. CyberPlayer Class — State Initialization

All state is initialized in `__init__` before `init_ui()` is called. Key state variables:

**`media_files` / `subtitle_files`:** Python lists of normalized (lowercase, forward-slash) file paths. These are the canonical in-memory representation of the vault contents. The UI list widgets are driven from these, not the other way around.

**`custom_subs_map`:** A dict mapping media file paths to subtitle file paths (or the string `"none"` if the user explicitly disabled subs for that video). This is the subtitle memory system — it persists subtitle choices across sessions.

**`playback_positions`:** A dict mapping media file paths to playback timestamps in seconds. Updated every 100ms during playback, saved to disk at most every 5 seconds.

**`is_initializing`:** A flag that suppresses config saves during the startup sequence. Without this, loading the playlist from config would trigger saves before the player is fully ready.

**`is_awaiting_resume`:** Set when a file has a saved position past 0.5 seconds. During this period, `update_timeline` watches for the file to finish loading (indicated by `duration > 0`), then triggers the resume dialog.

**`video_fs_window`:** Used as a boolean flag (`True` / `None`) to indicate whether video fullscreen is active. It's named "window" for historical reasons (it used to be an actual second window), but now it's just a flag since fullscreen is handled within the main window.

**`_controls_opacity` / `_controls_hide_timer`:** The fullscreen auto-hide system. A `QGraphicsOpacityEffect` is applied to the bottom bar in fullscreen mode. A `QTimer` triggers `_hide_controls` after 5 seconds of mouse inactivity, which animates the opacity to 0 and hides the cursor.

---

## 6. UI Layout

The main layout is a horizontal split:

```
┌─────────────────────────────────────────────────────────┐
│  Side Panel (160-260px)  │  Right Widget                │
│  ├── Search bar          │  ├── Title bar               │
│  ├── Media Vault         │  └── Viewport Container      │
│  │   └── file_list       │      ├── video_frame (mpv)   │
│  ├── Subtitle Vault      │      └── bottom_bar          │
│  │   └── sub_list        │                              │
└─────────────────────────────────────────────────────────┘
```

**Side panel sizing:** `setMinimumWidth(160)` + `setMaximumWidth(260)` allows the side panel to shrink at small window sizes rather than being fixed at 260px. This prevents the bottom bar controls from overlapping at minimum window size.

**`NoSelection` on list widgets:** Both `file_list` and `sub_list` use `QListWidget.SelectionMode.NoSelection`. This prevents Qt's default blue selection highlight when clicking, since we manage our own pink/bold active-item highlighting via `_highlight_active_media` and `_highlight_active_sub`.

**`viewport_container`:** A container widget that holds both `video_frame` (where mpv renders) and `bottom_bar` (the controls). The container receives click events to toggle play/pause.

**`video_frame`:** The widget whose `winId()` is passed to mpv. mpv renders directly into this widget's native OS window handle, bypassing Qt's paint system entirely.

**Bottom bar as a child of `viewport_container`:** The bottom bar is a fixed-height (85px) child of `viewport_container`, not a separate layout item. This means it overlaps the bottom of `video_frame`, creating the "floating controls" appearance.

**Time label fixed width:** The time label is locked to a fixed width calculated from the actual font metrics of "Consolas 12px" after `init_ui()` runs. Measuring before the stylesheet is applied gives wrong results because Qt uses the default system font, not Consolas, during early widget construction:
```python
fm = QFontMetrics(QFont("Consolas", 12))
self.time_label.setFixedWidth(fm.horizontalAdvance("00:00:00 / 00:00:00") + 16)
```

---

## 7. Render API Architecture — MpvRenderContext

This branch replaces `wid=` embedding with `MpvRenderContext` — mpv's official render API for embedding into external applications. This is the architecturally correct approach and enables the libplacebo (gpu-next) quality pipeline.

### Why We Migrated

The original codebase used `wid=str(int(self.video_frame.winId()))` — passing a native OS window handle directly to mpv. This is the "quick and dirty" embedding method. It works but has two fundamental problems:

1. **Subtitle initialization race with `gpu-next`:** mpv 0.41 switched the default renderer to `gpu-next` (libplacebo), whose subtitle pipeline initializes asynchronously. When embedded via `wid=`, mpv's renderer has no lifecycle hooks into Qt's window creation, so subtitle properties written during initialization land on an unready renderer non-deterministically. The `wid=` branch works around this with `vo='gpu'`, sacrificing libplacebo quality. The render API solves it architecturally.

2. **Airspace problem:** `wid=` surrenders that screen region to the GPU, making Qt child widget compositing impossible. The old branch required a separate top-level OS window for the pause overlay. With the render API, Qt owns the surface and normal child compositing works.

### MpvGLWidget

`video_frame` is now an instance of `MpvGLWidget(QOpenGLWidget)` rather than a plain `QWidget`.

```python
class MpvGLWidget(QOpenGLWidget):
    _schedule_render = pyqtSignal()
    _force_repaint = pyqtSignal()
```

**`initializeGL()`:** Called once by Qt when the OpenGL context is fully ready. This is the correct point to create `MpvRenderContext` — by this point, `QOpenGLContext.currentContext()` is valid and `getProcAddress` returns real function pointers.

```python
def get_proc_addr(_, name):
    glctx = QOpenGLContext.currentContext()
    if isinstance(name, str):
        name = name.encode('utf-8')
    addr = glctx.getProcAddress(name)
    try:
        return int(addr) if addr else 0
    except Exception:
        return 0
```

**`get_proc_addr` pitfall — bytes vs str:** libmpv passes GL function names as `bytes`. `QOpenGLContext.getProcAddress()` requires `bytes` (not `str`). The name must be encoded if it arrives as `str`. The return value is a `sip.voidptr` which must be converted to `int`.

**Threading model:** mpv fires `update_cb` from its internal render thread. Qt requires all widget operations on the main thread. We use a `QueuedConnection` signal to safely hop threads:

```python
self._schedule_render.connect(self._render_frame, Qt.ConnectionType.QueuedConnection)
```

**The render loop problem:** mpv's render API requires `render()` to be called on every `update_cb` invocation. If `render()` is not called promptly, mpv stops sending `update_cb`. Deferring through Qt's normal repaint queue (which coalesces repaints) causes mpv to stall after a few frames. The solution is a 60fps `QTimer` that calls `self.update()` unconditionally, driving `paintGL()` at 60fps regardless of whether `update_cb` fired:

```python
self._render_timer = QTimer()
self._render_timer.setInterval(16)
self._render_timer.timeout.connect(self.update)
self._render_timer.start()
```

**`paintGL()`:** The only place `render()` is called. Qt guarantees the GL context is current on the main thread when `paintGL` runs — no `makeCurrent()` needed, no threading issues possible.

```python
def paintGL(self):
    if not self._ctx or self._destroyed:
        return
    ratio = self.devicePixelRatioF()
    w = int(self.width() * ratio)
    h = int(self.height() * ratio)
    self._ctx.render(
        flip_y=True,
        opengl_fbo={'fbo': self.defaultFramebufferObject(), 'w': w, 'h': h}
    )
```

**`report_swap()`:** Must be called after each frame is presented on screen. Without this, mpv's frame queue stalls — on short files the queue drains quickly so stalling is invisible, but on long files (e.g. a 9-hour audiobook) the queue backs up, causing the video to only update when the window is resized. `frameSwapped` is the correct Qt signal for this:

```python
self.frameSwapped.connect(self._on_frame_swapped, Qt.ConnectionType.DirectConnection)

def _on_frame_swapped(self):
    if self._ctx and not self._destroyed:
        self._ctx.report_swap()
```

**`DirectConnection` on `frameSwapped`:** Must be `DirectConnection` so `report_swap()` is called synchronously in the same call stack as the swap, before Qt can coalesce another frame. `QueuedConnection` would deliver it too late.

**`cleanup()`:** Must be called before the widget is destroyed. Frees the render context while the GL context is still current, preventing a crash in mpv's destructor. Called from `safely_handle_app_exit()`.

### What Broke Along the Way

**`AA_UseDesktopOpenGL` crash:** Setting this attribute before `QApplication` causes a C-level crash (`0xC0000409`) because it conflicts with how libmpv initializes its GL context. Do not set any `AA_UseOpenGL*` attributes — let Qt choose the default.

**`wglGetProcAddress` crash:** Using Windows's `wglGetProcAddress` directly (instead of `QOpenGLContext.getProcAddress`) crashes because `wglGetProcAddress` requires a current rendering context on the calling thread — but libmpv calls `get_proc_addr` during `MpvRenderContext.__init__()`, before the context is made current on that thread. `QOpenGLContext.getProcAddress` handles this correctly.

**`BlockingQueuedConnection` deadlock:** Attempting to use `BlockingQueuedConnection` to guarantee `render()` is called synchronously on every `update_cb` causes a deadlock when switching files — mpv's render thread blocks waiting for the main thread, but the main thread is busy processing the file switch (which itself waits for mpv). Use `QueuedConnection` + the 60fps polling timer instead.

**`makeCurrent()` from background thread:** `QOpenGLWidget` does not support `makeCurrent()` from non-main threads. Attempting to render directly from mpv's `update_cb` thread corrupts the framebuffer (produces visual garbage). All GL operations must happen in `paintGL()` on the main thread.

**`vo='gpu-next'` with render API:** With `MpvRenderContext`, the correct `vo` is `'libmpv'` — a special pseudo-output that tells mpv to delegate rendering to the render context. Setting `vo='gpu-next'` makes mpv try to set up its own rendering pipeline in parallel, conflicting with the render context. The libplacebo quality pipeline is provided by `MpvRenderContext` internally, not by the `vo` setting.

### Quality Upgrades Now Available

With the render API, the full libplacebo pipeline is active. Quality options added to the MPV constructor:

```python
deband=True,               # removes banding on gradients
deband_iterations=4,
deband_threshold=35,
deband_range=16,
scale='ewa_lanczossharp', # high quality upscaling
dscale='mitchell',
cscale='sinc',
linear_upscaling=True,
sigmoid_upscaling=True,
```

`ewa_lanczossharp` is computationally expensive. On low-end GPUs, drop it to `scale='lanczos'` if stuttering occurs on high-resolution content.

---

## 7b. The Pause Overlay — Airspace Problem (Resolved)

In the `wid=` branch, the pause overlay required a separate top-level OS window because `wid=` surrenders the video region to the GPU, making Qt child widget transparency impossible (the **airspace problem**).

With `MpvGLWidget` (a `QOpenGLWidget`), Qt owns the OpenGL surface and composites child widgets normally. The pause overlay is now a plain child widget:

```python
self.pause_overlay = QLabel(self.video_frame)
self.pause_overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
self.pause_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
```

No separate OS window, no global coordinate mapping, no `ActivationChange` visibility management. The `_user_paused` flag logic is unchanged — see the original README for that explanation.

---

## 8. MPV Engine Initialization

```python
self.player = mpv.MPV(
    keep_open='yes',
    volume_max=150.0,
    vo='libmpv',
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
    sub_visibility=True,
    deband=True,
    deband_iterations=4,
    deband_threshold=35,
    deband_range=16,
    scale='ewa_lanczossharp',
    dscale='mitchell',
    cscale='sinc',
    linear_upscaling=True,
    sigmoid_upscaling=True,
)
# Wire the player into the GL widget so initializeGL() can create the render context
self.video_frame._mpv = self.player
```

**No `wid=`:** The render API takes over from `wid=`. `MpvRenderContext` is created inside `MpvGLWidget.initializeGL()` once Qt's GL context is ready. The player is wired into the widget via `self.video_frame._mpv = self.player` after construction.

**No `force_window=True`:** Not needed without `wid=` — mpv doesn't try to create its own window when `vo='libmpv'` is set.

**`vo='libmpv'`:** A special pseudo video output that delegates all rendering to the application via `MpvRenderContext`. This is not a real display backend — it's a signal to mpv that the host application controls the render loop. The actual rendering quality (libplacebo pipeline, upscaling shaders, etc.) is determined by `MpvRenderContext`, not by this `vo` value.

**`keep_open='yes'`:** Keeps mpv alive after a file finishes playing. Required for the "restart from beginning" feature in `_is_at_end()`.

**`volume_max=150.0`:** Allows volume amplification up to 150% for quiet media. The slider UI maps 0-100 to mpv's 0-150 via a logarithmic curve (see section 14).

**`sub_visibility=True`:** Explicitly enables subtitle rendering. Without this, mpv may suppress subtitle display for audio-only files since there is no video track to anchor the subtitle overlay to. Setting it in the constructor ensures it is active from the first frame.

**`sub_ass_override='force'`:** Tells mpv to ignore embedded ASS stylesheet data in subtitle files and use our explicit style properties instead. Without this, mpv uses the style embedded in the subtitle file (font, color, border-size, etc.), which overrides anything we set. `.srt` files don't have embedded styles, but mpv converts them internally to ASS format before rendering, and this conversion can produce unexpected default styles.

**`sub_ass_force_style='ScaledBorderAndShadow=yes'`:** Fixes a libass regression introduced around mpv 0.35 where border thickness was calculated differently depending on whether `ScaledBorderAndShadow` was explicitly set. Without this, borders can appear much thicker than `sub_border_size` suggests, particularly on high-resolution displays. Setting it explicitly locks the calculation to the correct mode.

**Constructor kwargs for defaults:** All subtitle style properties are passed at construction time. This matters because mpv processes constructor kwargs before any file loads, before the subtitle renderer initializes, and before any user config is applied. These become the "ground truth" defaults. Runtime property sets (via `update_sub_styles`) then update on top of this baseline. The reason for setting them twice (constructor + runtime) is that some mpv versions reset certain properties when a new subtitle track is parsed.

**User config blocking:** No `config_dir` is set, which means mpv will read the user's `%APPDATA%\mpv\mpv.conf` on Windows. If that file has conflicting settings (as was the case during development — it had `sub-font='Rajdhani'` and wrong color formats), those settings load after constructor kwargs and override them. The solution for end users who have custom mpv configs is to be aware that CyberPlayer's constructor kwargs take precedence for most properties, but a conflicting user config can still interfere.

---

## 9. Subtitle Reliability — The Full Investigation

Subtitle behavior was the most complex problem in this codebase. This section documents the full investigation for future reference.

### The Symptoms
- ~1 in 5-10 launches: subtitles either don't appear at all, or appear as thick white text regardless of the saved color/font
- The problem was completely non-deterministic — the same config produced different results on different runs
- The problem existed before any custom code touched subtitle properties

### What We Tried That Didn't Work

**Fixed timers (150ms, 300ms, 600ms, 1200ms):** The theory was that mpv's subtitle renderer needs time to initialize before `sub-color` etc. take effect. We tried applying properties after various delays. None of these fixed the problem — they changed the failure frequency slightly but the non-determinism persisted regardless of the delay value.

**`track-list` observation:** We observed mpv's `track-list` property and applied styles when a subtitle track appeared. This fires after the track is parsed, which seemed like the right moment. The problem persisted with the same frequency — the underlying issue was never timing.

**`sub-ass-override = strip`:** Strips embedded ASS tags from subtitle text. Did not fix either symptom. Additionally introduced its own issues — `strip` also removes ASS positioning information, causing display problems with subtitle files that rely on it.

**`sub-ass-override = force`:** Overrides all ASS properties including positioning. Did not fix either symptom. Additionally introduced its own issues — `force` can override layout properties in ways that push text off-screen or make it zero-size on some files.

**`sub-ass = no`:** Disables ASS rendering entirely and uses plain text mode. Did not fix either symptom. Additionally broke `.ass` subtitle files and was reverted.

**PyQt label subtitle renderer:** We attempted to render subtitles in a Qt label by polling `player['sub-text']` every 100ms. This failed entirely because `sub-text` is not a readable property in the python-mpv version used. Abandoned.

**`sub-ass-override` observer:** We observed the `sub-ass-override` property and re-applied when it changed. The observer was returning `True` (Python bool) instead of `'yes'` or `'force'` (string), causing an infinite feedback loop where every re-application triggered the observer again. Made things worse, removed.

**The actual fix — `vo='gpu'`:** Adding version logging revealed mpv 0.41.0. Researching that version revealed it changed the default video output from `gpu` to `gpu-next`. The `gpu-next` renderer (libplacebo) has an async subtitle pipeline that initializes non-deterministically — the same properties, set in the same order, produce different visual results depending on internal thread scheduling. Forcing `vo='gpu'` restored the old deterministic renderer and eliminated both symptoms entirely.

### The `loadfile` Change

During investigation, the subtitle loading code was refactored from:
```python
self.player.play(norm_path)
# ... then later:
self.player.sub_add(sub_path)
```
to:
```python
self.player.loadfile(norm_path, 'replace', sub_file=saved_sub_path)
```

This is a cleaner approach — the subtitle is passed atomically with the load command rather than as a separate command that could theoretically race. However, this did **not** fix the invisible subtitle symptom. Both symptoms (thick-white and invisible) were ultimately caused by `gpu-next` and fixed by `vo='gpu'`.

---

## 10. Thread Safety — Signals and the MPV Callback Problem

mpv fires its event callbacks (`file-loaded`, `track-list` changes) on mpv's internal worker thread, not the Qt main thread. Qt requires that all UI operations happen on the main thread. Calling Qt methods from mpv's thread causes crashes or silent failures.

**The wrong approach (what doesn't work):**
```python
@self.player.event_callback('file-loaded')
def _on_file_loaded(_event):
    QTimer.singleShot(600, self.update_sub_styles)  # WRONG — QTimer from wrong thread
```

`QTimer.singleShot` must be called from the Qt main thread. Calling it from mpv's thread silently fails on some runs, which was a contributing factor to the intermittent subtitle issues.

**The correct approach — `pyqtSignal`:**
```python
class CyberPlayer(QMainWindow):
    _file_loaded = pyqtSignal()

@self.player.event_callback('file-loaded')
def _on_file_loaded(_event):
    self._file_loaded.emit()  # thread-safe
```

`pyqtSignal.emit()` is thread-safe — it posts the signal to Qt's event queue, which is then processed on the main thread. The connected slot (`update_sub_styles`) runs on the main thread regardless of which thread emitted the signal.

**`_file_loaded` and `_sub_ready`:** Two signals are used:
- `_file_loaded`: emitted from mpv's `file-loaded` event callback. Triggers `update_sub_styles`.
- `_sub_ready`: emitted from the `track-list` observer when a subtitle track appears. Triggers both `_apply_pending_sub` and `update_sub_styles`.

The `track-list` observer fires specifically when a subtitle track is added to the track list (i.e., when mpv has parsed the subtitle file), which is a more precise moment than `file-loaded` for subtitle-specific operations.

**Keeping references alive:** mpv's Python binding uses weak references for callbacks. If a callback function goes out of scope, it gets garbage collected and mpv silently stops calling it. `self._on_file_loaded_cb = _on_file_loaded` and `self._on_track_list_cb = _on_track_list_change` keep strong references on the instance, preventing premature garbage collection.

---

## 11. Configuration System

All persistent state is stored in `config.json` next to the executable.

### Config File Structure
```json
{
    "font_family": "Consolas",
    "font_size": 36,
    "font_color": "#00f3ff",
    "system_volume_level": 100,
    "playback_speed": 1.0,
    "last_active_media_file": "/path/to/last.mp4",
    "media_files_playlist": ["/path/to/video1.mp4", "..."],
    "subtitle_files_playlist": ["/path/to/subs.srt", "..."],
    "custom_subs_map": {
        "/path/to/video1.mp4": "/path/to/subs.srt",
        "/path/to/video2.mp4": "none"
    },
    "playback_positions": {
        "/path/to/video1.mp4": 1234.567
    }
}
```

### Path Normalization

All file paths are stored lowercase with forward slashes, regardless of OS:
```python
norm_path = filepath.lower().replace('\\', '/')
```

This prevents duplicate entries when the same file is accessed via different path representations (e.g., `C:\Users\` vs `c:/users/`), and ensures cross-platform compatibility if the config is ever moved.

### The `"none"` Sentinel

`custom_subs_map` uses the string `"none"` (not Python `None`) to mean "user explicitly disabled subtitles for this video." This is necessary because a missing key means "no saved preference" (use auto-detection), while `"none"` means "user said no subs." When loading, `"none"` is preserved as-is:
```python
self.custom_subs_map = {
    k: (v if v == "none" else v.lower().replace('\\', '/'))
    for k, v in raw_subs_map.items()
}
```

### Throttled Saving

Saving during active playback is expensive if done on every position update. Instead, `_schedule_save()` marks a dirty flag and starts a 5-second one-shot timer. If called again within 5 seconds, the existing timer is not restarted (it fires at the original 5-second mark). On exit, `safely_handle_app_exit()` bypasses the throttle and saves immediately.

### `is_initializing` Guard

`save_configuration_memory()` checks `if self.is_initializing: return` at the top. During startup, `load_configuration_memory()` populates the playlists by calling `_add_playlist_item()`, which calls `add_to_playlist()`, which calls `save_configuration_memory()`. Without the guard, each file being loaded from config would trigger a save, creating a cascade of disk writes during startup.

### Playlist as Source of Truth

The in-memory `self.media_files` and `self.subtitle_files` lists are the canonical source of truth. When saving, they are written directly — there is no merging with the on-disk version for playlists. This ensures that when a user removes a file from the vault, the removal persists. An earlier version merged in-memory with on-disk during save, which caused removed files to reappear after relaunch because they were still in the on-disk JSON.

Playback positions and subtitle mappings, by contrast, do merge with disk — these are additive (accumulating position data for many files over time) rather than replacing (the vault is what you see is what you get).

---

## 12. Playback Engine

### `play_file(filepath)`

The central playback method. Order of operations matters:

1. **Set `is_initializing = True`** to suppress saves during file transition.
2. **Look up saved position BEFORE `add_to_playlist`** — the lookup must happen before the file is added, or there could be a race where the position is cleared.
3. **Save current position** of the previously playing file (if any).
4. **Set `active_media_path`** and highlight it in the vault.
5. **Determine subtitle action** from `custom_subs_map`.
6. **Call `player.loadfile()`** with subtitle options passed atomically. This is a single mpv command that opens the file and configures the subtitle in one operation, eliminating the race between `play()` and `sub_add()`.
7. **Hide the pause overlay** (new file = playing, not paused).
8. **Check for saved position** — if > 0.5 seconds, set `is_awaiting_resume = True`.
9. **Call `handle_visual_frame_adjustments()`** to apply audio-file visual mode if needed.
10. **Save config** (the new `last_active_media_file` needs to persist).

### Resume Dialog

When `is_awaiting_resume = True`, `update_timeline()` watches for `player.duration > 0` (which means the file has loaded and duration is known). It then calls `prompt_user_playback_resume()`, which pauses playback and shows a dialog. The dialog is triggered from `update_timeline` rather than immediately in `play_file` because `player.duration` is `None` until mpv has opened the file — we can't seek to a position in a file that hasn't loaded yet.

### `_is_at_end()`

Returns `True` if `(duration - position) < 0.05`. This 50ms threshold exists because mpv's last decoded frame is always slightly behind the container's reported duration. Without the threshold, pressing play at the final frame wouldn't restart playback.

### Speed Control

Speed steps are `[0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]` indexed by `speed_index`. Saved to and loaded from config as `"playback_speed"`. Applied to mpv via `player.speed`. The speed menu shows a `▶` indicator next to the current speed and uses a lambda capture (`s=speed`) to avoid the Python closure-in-loop problem where all menu actions would otherwise reference the last value of `speed`.

---

## 13. Timeline and Seeking

### Slider Scale

The slider range is `0` to `math.ceil(duration * 100)`. Values are in centiseconds (1/100th of a second). This gives sub-second seek precision while keeping values as integers (Qt sliders work with integers). When converting back: `seconds = slider_value / 100.0`.

### `blockSignals(True/False)`

When `update_timeline` sets the slider's value programmatically during playback, it wraps the `setValue()` call in `blockSignals(True/False)`. Without this, `setValue` would emit `sliderMoved`, which is connected to `preview_time`, causing the time label to flicker or the seek to fire unintentionally.

### End-of-file Snap

```python
at_end = (dur - pos) < 0.05
display_pos = dur if at_end else pos
scaled_pos = scaled_max if at_end else int(pos * 100)
```

When the player reaches the end, `time_pos` stops slightly before `duration`. This would leave the slider and timestamp slightly short of the end, which looks like a bug. Snapping to the exact end position when within 50ms gives clean behavior.

### Dragging

When `is_user_dragging = True`, `update_timeline` skips the slider position update (the user is dragging, we don't want to fight them). `preview_time()` updates only the time label during drag without seeking. The actual seek happens in `apply_video_position()` on `sliderReleased`.

---

## 14. Volume System

### Logarithmic Curve

Human hearing is logarithmic — equal slider increments should feel like equal volume changes. A linear mapping would make the slider feel weighted toward the top. The formula:

```python
mpv_volume = min(150.0, 150.0 * math.log(1 + slider_value) / math.log(101))
```

This maps slider `0` → mpv `0`, slider `50` → mpv ~128, slider `100` → mpv `150`. The curve feels natural: the lower half of the slider covers quiet/moderate listening, the upper half covers loud/amplified.

**Why `volume_max=150.0`:** mpv's default maximum is 100 (no amplification). Many media files, particularly audiobooks, are mastered at low levels. 150% allows reasonable amplification without distortion artifacts that would appear at extreme values.

---

## 15. Subtitle Controls

### Font and Color Dialogs

Both dialogs stop the 100ms `timer` before opening (`self.timer.stop()`) and restart it after (`self.timer.start()`). This prevents `update_timeline` from running while a dialog blocks the event loop — without this, the position tracking could miss updates or behave unexpectedly.

**`QFontDialog` options:**
- `DontUseNativeDialog`: Uses Qt's cross-platform dialog instead of the OS native one. The native dialog on Windows doesn't support filtering options.
- `ScalableFonts`: Only shows fonts that scale cleanly (outline fonts), filtering out bitmap fonts that would look bad at arbitrary sizes.
- **Hiding Underline/Strikeout:** mpv's subtitle rendering doesn't support underline or strikeout. These options are hidden by searching `findChildren(QWidget)` for widgets whose text matches those labels.

### `update_sub_styles()`

Called whenever subtitle appearance changes. Sets all relevant mpv properties in a single loop:

- `sub-ass-override = 'force'`: Re-applied on every call to ensure it doesn't get reset
- `sub-ass-force-style = 'ScaledBorderAndShadow=yes'`: Locks border scaling
- `sub-font`, `sub-font-size`, `sub-color`, `sub-border-color`, `sub-border-size`, `sub-shadow-color`, `sub-shadow-offset`: The user's chosen style
- `osd-font`, `osd-font-size`, `osd-color`, `osd-border-color`, `osd-border-size`: Mirrors the subtitle style to OSD (on-screen display) messages for consistency

### Size Bounds

`adjust_sub_size()` clamps the size between 12px and 72px:
```python
self.current_sub_size = max(12, min(72, self.current_sub_size + delta))
```
12px is the minimum readable size; 72px is large enough for accessibility without being absurd.

### Subtitle Vault Memory

`custom_subs_map[media_path]` stores the subtitle choice for each video. Three possible values:
- A path string: load this subtitle file for this video
- `"none"`: user explicitly disabled subs for this video (never auto-detect)
- Missing key: no saved preference, use mpv's auto-detection (`sub-auto=fuzzy`)

`clear_subtitle()` (the `✕ OFF` button) sets the map entry to `"none"` and tells mpv `sid=no`. On next launch, mpv will be told `sub_auto='no'` and `sid='no'` before the file opens, preventing auto-detection.

---

## 16. Video Fullscreen System

### Architecture Decision

Video fullscreen hides the side panel and title bar, then calls `showFullScreen()` on the main window. **This is the same window, not a second window.** An earlier implementation created a second `QWidget` window, reparented `video_frame` into it, then called `showFullScreen()` on that. This caused:
- mpv losing its window binding (requiring a wid rebind with timing issues)
- Reparenting artifacts (black flashes, layout glitches)
- The pause overlay needing complex reparenting logic

The single-window approach is simpler and eliminates all these issues. mpv stays bound to the same `video_frame` throughout.

### Maximized State Detection

`isMaximized()` always returns `False` for frameless windows on Windows, because Qt's maximize state is tied to the OS window chrome (title bar, borders) which frameless windows don't have. Instead, we detect "maximized" by comparing geometry to the available screen area:
```python
screen_geom = QApplication.primaryScreen().availableGeometry()
self._pre_fs_maximized = self.geometry() == screen_geom
```

On exit, if `_pre_fs_maximized` is True, we call `showFullScreen()` (not `showMaximized()`) because the maximize button in the title bar uses `showFullScreen()` for its "maximized" state. Calling `showMaximized()` would put the window in a different state that the maximize button can't toggle out of.

### Auto-hide Controls

In video fullscreen, the bottom bar has a `QGraphicsOpacityEffect` applied. A 5-second single-shot timer (`_controls_hide_timer`) triggers `_hide_controls()`, which animates the opacity from 1.0 to 0.0. Any mouse movement over `viewport_container` calls `_reset_controls_timer()`, which shows the controls and restarts the timer.

The cursor is hidden (`BlankCursor`) when controls hide and restored (`ArrowCursor`) when controls show. The cursor restoration happens in `_show_controls()` before the opacity animation — this ensures the cursor reappears immediately on mouse movement, even if the controls are still mid-animation.

### Shortcut Management

In video fullscreen, a dedicated `_fs_space` shortcut handles spacebar, and the global `shortcut_space` is disabled (`setEnabled(False)`). This prevents both from firing simultaneously. On exit, `shortcut_space` is re-enabled and `_fs_space` is deleted.

---

## 17. Window Management — Frameless Window

The window uses `Qt.WindowType.FramelessWindowHint`, removing the OS title bar and borders. This requires manual implementation of dragging and resizing.

### Edge Resize Detection

`_get_resize_edge(pos)` checks if the mouse is within 6 pixels of any window edge or corner:
```python
m = 6  # margin in pixels
left, right, top, bottom = x < m, x > w - m, y < m, y > h - m
```
Corner combinations are checked first (tl, tr, bl, br), then individual edges. Each returns a string code (`'tl'`, `'r'`, `'b'`, etc.).

### App-level Event Filter

Child widgets (buttons, sliders, etc.) swallow mouse events and prevent them from reaching the main window. An application-level `QObject` event filter is installed that intercepts all `MouseButtonPress`, `MouseMove`, and `MouseButtonRelease` events across all widgets:

```python
class _ResizeFilter(QObject):
    def eventFilter(self_, obj, event):
        if t == QEvent.Type.MouseButtonPress:
            return self_._win._handle_mouse_press(event)
        # ...
```

Returning `True` from `eventFilter` consumes the event (prevents child widgets from receiving it). `_handle_mouse_press` returns `True` only when a resize edge is detected, allowing normal clicks on buttons/sliders to pass through.

### Dragging

When the mouse is pressed on the title bar (not on an edge or button), `oldPos` is set to the cursor's global position. On subsequent mouse moves, the delta between the current position and `oldPos` is applied to the window position.

### Minimum Size

`setMinimumSize(900, 500)` prevents the window from being resized so small that the bottom bar controls overlap. 900px is the calculated minimum width for all controls to fit without wrapping (side panel at minimum 160px + ~740px for controls).

---

## 18. Vault System — Media and Subtitles

### Dual-panel Design

Two separate `QListWidget` instances (`file_list` for media, `sub_list` for subtitles) with identical behavior. Items are added via `_add_playlist_item()`, which stores the full path in `Qt.ItemDataRole.UserRole` and displays only the filename. This allows files with identical names in different directories to coexist in the vault without confusion.

### Active Item Highlighting

`_highlight_active_media()` and `_highlight_active_sub()` iterate all items in their respective list and set bold + magenta (`#ff00ea`) for the active item, grey for all others. This is manual because the lists use `NoSelection` mode (no Qt selection highlight), so we manage the visual state ourselves. The highlight is updated whenever a file starts playing.

### Global Search

`filter_files(text)` shows/hides list items by matching the search text against the filename. Both media and subtitle lists are filtered simultaneously. The search bar uses `Qt.FocusPolicy.ClickFocus` so it doesn't grab keyboard focus on launch (which would prevent spacebar from working immediately).

### Context Menu Removal

Right-clicking any vault item shows a `QMenu` with a single "Remove from vault" action. `_remove_from_vault()` handles three cases:
- **Media removal:** Remove from `media_files`, clear its `custom_subs_map` entry (so subtitle preference is forgotten), clear `active_media_path` if it was the currently playing file.
- **Subtitle removal:** Remove from `subtitle_files`, if it's currently active call `clear_subtitle()` to disable it immediately, remove all `custom_subs_map` entries that point to it.

After removal, `save_configuration_memory()` is called so the removal persists. Since playlists are saved as the in-memory list directly (not merged with disk), the item won't reappear on next launch.

---

## 19. Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Toggle play/pause |
| `→` (Right arrow) | Skip forward 5 seconds |
| `←` (Left arrow) | Skip backward 5 seconds |
| `Escape` | Exit video fullscreen (fullscreen mode only) |

Shortcuts are `QShortcut` instances bound to `self` (the main window). In video fullscreen, the global `Space` shortcut is disabled and a new one is created bound to the same window — this prevents double-firing while ensuring the shortcut still works when the side panel is hidden.

---

## 20. Open With Support

```python
if __name__ == '__main__':
    player = CyberPlayer()
    player.show()

    if len(sys.argv) > 1:
        target_file = os.path.normpath(sys.argv[1]).lower().replace('\\', '/')
        if os.path.exists(target_file):
            QTimer.singleShot(250, lambda: player.play_file(target_file))
```

When launched with a file argument (e.g., from Windows "Open With"), the file is played via a 250ms deferred timer. The delay allows the window to fully initialize and render before playback starts. Without the delay, `play_file` could be called before mpv is ready to accept commands.

In `__init__`, when `len(sys.argv) > 1`, `is_initializing` is set to `False` immediately without restoring the last session — the argv file is played instead. This prevents the confusing behavior of briefly loading the previous session before switching to the requested file.

---

## 21. Audio File Visual Mode

In the `wid=` branch, `handle_visual_frame_adjustments()` applied a CSS dot-grid background to `video_frame` for audio files. With `MpvGLWidget` (`QOpenGLWidget`), `setStyleSheet()` has no effect on the GL framebuffer — mpv controls the surface entirely. For audio files mpv renders a black frame naturally. `handle_visual_frame_adjustments()` is a no-op in this branch.

The `video-format` property observer handles the audio/video switch: when `video-format` becomes `None` (audio-only file loaded), `trigger_clear()` forces a repaint, and the `AudioSubOverlay` is shown. When `video-format` becomes non-`None`, the overlay hides.

---

## 21b. Audio Subtitle Overlay

For audio-only files, mpv's render API does not render subtitles through the GL pipeline — there is no video frame for mpv to attach the subtitle overlay to. The solution is `AudioSubOverlay`: a transparent `QWidget` child of `viewport_container` that draws the current subtitle line using `QPainter`.

**Why `viewport_container` not `video_frame`:** `video_frame` is a `QOpenGLWidget`. Qt's GL compositing pipeline may draw the GL surface over child widgets' paint output. By parenting the overlay to `viewport_container` (a plain `QWidget`), it sits at the same level as `video_frame` in the widget tree and is drawn on top.

**Thread safety:** mpv's `sub-text` and `video-format` observers fire on mpv's internal thread, not the Qt main thread. All Qt operations are routed through signals:

```python
class AudioSubOverlay(QWidget):
    _sub_text_signal = pyqtSignal(str)
    _visibility_signal = pyqtSignal(bool)
```

`set_sub_text()` and `set_audio_mode()` are the public API — safe to call from any thread. They emit signals which Qt delivers to `_apply_sub_text()` and `_apply_visibility()` on the main thread.

**Geometry management:** The overlay must cover `video_frame` exactly. `_apply_visibility()` calls `findChild(QOpenGLWidget)` on the parent to locate `video_frame` and calls `setGeometry(vf.geometry())` at show time. `resizeEvent` on `CyberPlayer` updates the geometry on every window resize.

**Font size matching:** mpv renders SRT subtitles via libass using `sub-font-size` as "script pixels" at a 720p reference height. The equivalent screen pixel size is:

```
screen_px = sub_font_size * display_height / 720
```

The overlay reads `sub-font-size` directly from the mpv player at paint time and applies the same formula using `QFont.setPixelSize()` (not point size — Qt points are DPI-scaled, mpv script pixels are not). A `0.8` correction factor accounts for libass's internal padding which makes mpv-rendered text appear slightly smaller than raw QPainter text at the same nominal pixel size.

**`sub-text` property:** mpv exposes the current subtitle line via the `sub-text` property. The observer fires on every subtitle change (including empty string when a subtitle ends). Empty strings clear the overlay text and trigger a repaint, producing a black screen between subtitle lines.

---

## 22. Dependencies

| Package | Purpose |
|---------|---------|
| `python-mpv` | Python bindings for libmpv. Handles all media decoding, rendering, and playback. |
| `PyQt6` | Qt6 framework for the UI. Widgets, layouts, signals/slots, event handling. |
| `PyQt6-Qt6` | Qt6 runtime libraries. |
| `PyQt6-sip` | SIP bindings layer between Python and Qt. |

System requirement: `mpv-2.dll` (Windows) or `libmpv.so` (Linux) must be present in the same directory as `app.py` or on the system PATH.

### Why python-mpv over alternatives

- **VLC (python-vlc):** VLC's Python bindings have poor support for subtitle style overrides at runtime.
- **GStreamer (python-gst):** More complex setup, worse Windows support.
- **Custom ffmpeg:** Would require building an entire rendering pipeline.

mpv has a mature C API (`libmpv`) designed specifically for embedding in other applications, with full support for all playback features, subtitle rendering, and property observation.

---

## Known Limitations

- **User mpv config (`%APPDATA%\mpv\mpv.conf`):** If a user has a conflicting mpv config, it may override CyberPlayer's subtitle settings. Solution: ensure no conflicting `sub-font`, `sub-color`, or `sub-ass-override` entries in the user config.

- **Subtitle auto-detection in same directory:** mpv's `sub-auto=fuzzy` will auto-load subtitle files with similar names to the video file. This is intentional for convenience but can't be controlled granularly.

- **Single instance:** No inter-process communication; launching a second instance creates a second player rather than passing the file to the existing one.

- **Playback position precision:** Saved every 5 seconds during playback. If the app crashes, up to 5 seconds of position progress is lost.

- **Audio subtitle font size:** The `AudioSubOverlay` matches mpv's subtitle size using a `0.8` correction factor for libass padding. This is approximate — if font sizes look mismatched between audio and video files, adjust the constant in `paintEvent`.

- **`ewa_lanczossharp` on low-end GPUs:** This upscaling algorithm is expensive. On low-end GPUs it may cause dropped frames on high-resolution video. Drop to `scale='lanczos'` or remove the `scale` option if stuttering occurs.

- **`vo='libmpv'` requires render context before playback:** If a file is somehow loaded before `initializeGL()` fires (before the window is shown), mpv will fail to initialize its VO. The `app.processEvents()` calls in `__main__` after `player.show()` mitigate this by forcing Qt to process the initial paint event before any file load.

- **PyQt6 without ANGLE:** The render API requires Qt's native desktop OpenGL (WGL on Windows). ANGLE (OpenGL ES over D3D11) was removed from Qt 6 and is not available in any PyPI PyQt6 build. Attempts to use `AA_UseOpenGLES` or `AA_UseDesktopOpenGL` with `MpvRenderContext` cause crashes.

---

## Memory Usage

This branch uses approximately 250MB of RAM at runtime, compared to ~150MB for the main (`wid=`) branch. The ~100MB difference has four causes:

**60fps render timer (largest factor):** In the `wid=` branch, mpv drives its own render loop internally at the OS level — Python and Qt are mostly idle between events. In this branch, a `QTimer` fires every 16ms, waking the Qt event loop, calling `paintGL()`, which calls `ctx.render()`, which invokes libplacebo's full shader pipeline. That's 60 GPU→CPU round trips per second even when paused or playing audio-only content. The process stays hot in memory rather than idling.

**libplacebo shader compilation:** When `MpvRenderContext` initializes, libplacebo compiles the `ewa_lanczossharp` and debanding shaders and caches the compiled objects in process memory for the lifetime of the app. `vo='gpu'` uses much simpler shaders that compile smaller.

**`QOpenGLWidget` GL context overhead:** `QOpenGLWidget` maintains its own OpenGL context, framebuffer objects, and texture buffers that a plain `QWidget` doesn't. On Windows this includes a shadow copy of the backbuffer. Rough cost: 20-40MB depending on window resolution.

**Property observer overhead:** Two additional constantly-firing mpv property observers (`video-format`, `sub-text`) keep Python callbacks alive and processing on every subtitle change.

**Reducing memory usage:** The two highest-impact changes are dropping the render timer from 60fps to 30fps (`setInterval(33)`) and replacing `scale='ewa_lanczossharp'` with `scale='lanczos'`. Together these would recover approximately 30-50MB with minimal perceptible quality difference for typical content.