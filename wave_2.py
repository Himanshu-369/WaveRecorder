import sys
import time
import threading
import struct
import numpy as np
from datetime import datetime
from pathlib import Path

# ── Dependency check ─────────────────────────────────────────────────────────
missing = []
try:
    import pyaudiowpatch as pyaudio
    PYAUDIO_OK = True
except ImportError:
    try:
        import pyaudio
        PYAUDIO_OK = True
        print("WARNING: pyaudiowpatch not found, falling back to pyaudio. "
              "Loopback capture may not work. Run: pip install pyaudiowpatch")
    except ImportError:
        PYAUDIO_OK = False
        missing.append("pyaudiowpatch")

try:
    import soundfile as sf
except ImportError:
    missing.append("soundfile")

if missing:
    print(f"Missing packages. Run:\n  pip install {' '.join(missing)} numpy PyQt6")
    sys.exit(1)

from PyQt6.QtWidgets import *
from PyQt6.QtCore    import *
from PyQt6.QtGui     import *


# ── Thread-safe bridge: audio callback → GUI thread ──────────────────────────
class _AudioBridge(QObject):
    chunk_ready = pyqtSignal(object)


# ── Theme & Constants ─────────────────────────────────────────────────────────
BLOCK_SIZE  = 1024

# Modern Dark Pro Palette
BG           = "#09090B"  # Deepest background
SURFACE      = "#121215"  # Slightly lighter for panels
CARD         = "#1C1C22"  # Elevated elements
BORDER       = "#2E2E38"  # Subtle borders
TEXT         = "#F3F3F5"  # Primary text
MUTED        = "#8F8F9D"  # Secondary text
ACCENT       = "#5E6AD2"  # Indigo accent
ACCENT_HOVER = "#737DF0"
RED          = "#8C7EFF"  # Record red
RED_HOVER    = "#FF6B78"

FONT_SANS = "'Inter', 'Segoe UI', '-apple-system', sans-serif"
FONT_MONO = "'JetBrains Mono', 'SF Mono', 'Consolas', monospace"

STYLE = f"""
* {{
    font-family: {FONT_SANS};
    color: {TEXT};
    font-size: 13px;
}}

QMainWindow, QDialog, QWidget#root {{ background: {BG}; }}
QWidget {{ background: transparent; }}

/* Tabs */
QTabWidget::pane {{ border: none; background: {BG}; }}
QTabBar {{ background: {SURFACE}; border-bottom: 1px solid {BORDER}; }}
QTabBar::tab {{
    background: transparent; color: {MUTED};
    padding: 10px 16px; border: none;
    border-bottom: 3px solid transparent;
    font-size: 13px; font-weight: 600;
    min-width: 100px;
}}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 3px solid {ACCENT}; }}
QTabBar::tab:hover:!selected {{ color: #D0D0D5; }}

/* Cards & Containers */
QWidget#card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}

/* Buttons */
QPushButton {{
    background: {SURFACE}; color: {TEXT};
    border: 1px solid {BORDER}; border-radius: 6px;
    padding: 6px 12px; font-weight: 500;
}}
QPushButton:hover {{ background: #24242C; border-color: #40404C; }}
QPushButton:pressed {{ background: #16161B; }}

QPushButton#primary {{
    background: {ACCENT}; border: none; color: white;
    font-weight: 600; border-radius: 6px;
    padding: 8px 16px; font-size: 13px;
}}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#primary:pressed {{ background: #4A56B8; }}

QPushButton#record {{
    background: {RED}; border: none; color: white;
    font-weight: 700; border-radius: 8px;
    padding: 10px 24px; font-size: 14px;
}}
QPushButton#record:hover {{ background: {RED_HOVER}; }}

QPushButton#flat {{
    background: transparent; border: 1px solid {BORDER};
    border-radius: 6px; padding: 6px 12px; color: {MUTED};
}}
QPushButton#flat:hover {{ color: {TEXT}; border-color: {ACCENT}; background: #5E6AD211; }}

/* Inputs */
QComboBox, QLineEdit {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 6px; padding: 6px 10px;
    selection-background-color: {ACCENT};
}}
QComboBox:hover, QLineEdit:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox::down-arrow {{
    image: none; border-left: 4px solid transparent;
    border-right: 4px solid transparent; border-top: 5px solid {MUTED};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background: {CARD}; border: 1px solid {BORDER};
    border-radius: 6px; padding: 4px; outline: none;
}}

/* List */
QListWidget {{
    background: {CARD}; border: 1px solid {BORDER};
    border-radius: 10px; padding: 4px; outline: none;
}}
QListWidget::item {{
    padding: 8px 12px; border-radius: 6px; color: #D0D0D5;
}}
QListWidget::item:selected {{ background: {ACCENT}33; color: white; border-left: 3px solid {ACCENT}; }}
QListWidget::item:hover:!selected {{ background: {SURFACE}; }}

/* Scrollbars */
QScrollBar:vertical {{ background: transparent; width: 6px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 3px; min-height: 20px; }}
QScrollBar::handle:vertical:hover {{ background: {MUTED}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* Typography */
QLabel#heading {{ font-size: 20px; font-weight: 800; letter-spacing: -0.5px; }}
QLabel#sub {{ font-size: 12px; color: {MUTED}; }}
QLabel#timer {{ font-family: {FONT_MONO}; font-size: 42px; font-weight: 300; letter-spacing: 2px; }}
QLabel#status {{ font-size: 11px; color: {MUTED}; font-weight: 600; }}
QLabel#badge {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 4px; padding: 4px 8px; font-size: 11px; font-weight: 600; color: {MUTED};
}}

/* Sliders */
QSlider::groove:horizontal {{ background: {BORDER}; height: 4px; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {TEXT}; width: 14px; height: 14px;
    margin: -5px 0; border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{ background: {ACCENT}; transform: scale(1.1); }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; height: 4px; border-radius: 2px; }}
QSlider::handle:horizontal:disabled, QSlider::sub-page:horizontal:disabled {{ background: {BORDER}; }}

/* Splitter */
QSplitter::handle:vertical {{
    background: transparent; height: 8px;
}}
QSplitter::handle:vertical:hover {{ background: {BORDER}; }}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Settings Management & Dialog
# ─────────────────────────────────────────────────────────────────────────────

def get_save_dir() -> Path:
    settings = QSettings()
    path_str = settings.value("save_dir", str(Path.cwd()))
    p = Path(path_str)
    if not p.exists():
        try: p.mkdir(parents=True, exist_ok=True)
        except: p = Path.cwd()
    return p

def generate_filename() -> str:
    settings = QSettings()
    prefix = settings.value("file_prefix", "recording").strip()
    suffix = settings.value("file_suffix", "").strip()
    dfmt   = settings.value("date_format", "%Y-%m-%d_%H-%M-%S").strip()

    parts = []
    if prefix: parts.append(prefix)
    if dfmt:
        try: parts.append(datetime.now().strftime(dfmt))
        except: parts.append(datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    if suffix: parts.append(suffix)

    if not parts:
        return "recording.wav"
    return "_".join(parts) + ".wav"


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(400, 420)
        self.settings = QSettings()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # ── Save Directory ──
        layout.addWidget(QLabel("Save Directory", objectName="status"))
        dir_layout = QHBoxLayout()
        self.dir_input = QLineEdit()
        self.dir_input.setReadOnly(True)
        browse_btn = QPushButton("Browse", objectName="flat")
        browse_btn.clicked.connect(self._browse)
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(browse_btn)
        layout.addLayout(dir_layout)
        
        layout.addWidget(h_sep())

        # ── Naming Format ──
        layout.addWidget(QLabel("File Naming Syntax", objectName="status"))
        
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("e.g. recording")
        
        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText("%Y-%m-%d_%H-%M-%S")
        self.date_input.setToolTip("Uses standard Python strftime format codes.")
        
        self.suffix_input = QLineEdit()
        self.suffix_input.setPlaceholderText("e.g. raw")
        
        form_layout.addRow("Prefix:", self.prefix_input)
        form_layout.addRow("Date Format:", self.date_input)
        form_layout.addRow("Suffix:", self.suffix_input)
        layout.addLayout(form_layout)

        # ── Preview ──
        self.preview_label = QLabel()
        self.preview_label.setObjectName("badge")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(36)
        layout.addWidget(self.preview_label)

        layout.addStretch()

        # ── Buttons ──
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel", objectName="flat")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Settings", objectName="primary")
        save_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        self._load()

        self.prefix_input.textChanged.connect(self._update_preview)
        self.suffix_input.textChanged.connect(self._update_preview)
        self.date_input.textChanged.connect(self._update_preview)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.dir_input.text())
        if path:
            self.dir_input.setText(path)

    def _load(self):
        self.dir_input.setText(self.settings.value("save_dir", str(Path.cwd())))
        self.prefix_input.setText(self.settings.value("file_prefix", "recording"))
        self.suffix_input.setText(self.settings.value("file_suffix", ""))
        self.date_input.setText(self.settings.value("date_format", "%Y-%m-%d_%H-%M-%S"))
        self._update_preview()

    def accept(self):
        self.settings.setValue("save_dir", self.dir_input.text())
        self.settings.setValue("file_prefix", self.prefix_input.text())
        self.settings.setValue("file_suffix", self.suffix_input.text())
        self.settings.setValue("date_format", self.date_input.text())
        super().accept()

    def _update_preview(self):
        prefix = self.prefix_input.text().strip()
        suffix = self.suffix_input.text().strip()
        dfmt   = self.date_input.text().strip()

        parts = []
        if prefix: parts.append(prefix)
        if dfmt:
            try: parts.append(datetime.now().strftime(dfmt))
            except: parts.append("[INVALID FORMAT]")
        if suffix: parts.append(suffix)

        fname = "_".join(parts) + ".wav" if parts else "recording.wav"
        self.preview_label.setText(f"Preview:  {fname}")


# ─────────────────────────────────────────────────────────────────────────────
# Custom UI Components
# ─────────────────────────────────────────────────────────────────────────────

def make_card():
    w = QWidget()
    w.setObjectName("card")
    return w

def h_sep():
    w = QFrame()
    w.setFrameShape(QFrame.Shape.HLine)
    w.setStyleSheet(f"background: {BORDER}; max-height: 1px; border: none; margin: 4px 0;")
    return w


class LiveWaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.samples   = np.zeros(512)
        self.recording = False
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(80)
        self.startTimer(33)

    def timerEvent(self, _):
        self.update()

    def push(self, data: np.ndarray):
        mono = data.mean(axis=1) if data.ndim > 1 else data
        n = min(len(mono), len(self.samples))
        self.samples = np.roll(self.samples, -n)
        self.samples[-n:] = mono[-n:]

    def reset(self):
        self.samples[:] = 0

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        cy   = H / 2

        p.fillRect(self.rect(), QColor(SURFACE))
        p.setPen(QPen(QColor(BORDER), 1, Qt.PenStyle.DashLine))
        p.drawLine(0, int(cy), W, int(cy))

        if not self.recording:
            p.setPen(QColor(MUTED))
            f = QFont("Inter", 10, QFont.Weight.Medium)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Ready to Record")
            return

        n = len(self.samples)
        path = QPainterPath()
        path.moveTo(0, cy)
        
        for i, v in enumerate(self.samples):
            x = i * W / n
            y = cy - (v * cy * 0.85)
            path.lineTo(x, y)
            
        p.setPen(QPen(QColor(ACCENT + "40"), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPath(path)
        
        p.setPen(QPen(QColor(ACCENT), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPath(path)


class TrimWaveformWidget(QWidget):
    selectionChanged = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.waveform    = np.array([])
        self.duration    = 0.0
        self._start      = 0.0
        self._end        = 1.0
        self._drag       = None
        self._drag_off   = 0.0
        self.playhead    = -1.0
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(100)
        self.setMouseTracking(True)

    def load(self, samples: np.ndarray, duration: float):
        self.waveform = samples
        self.duration = duration
        self._start   = 0.0
        self._end     = 1.0
        self.update()

    def get_times(self):
        return self._start * self.duration, self._end * self.duration

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        cy   = H / 2

        p.fillRect(self.rect(), QColor(CARD))
        p.setPen(QPen(QColor(BORDER), 1))
        p.drawLine(0, int(cy), W, int(cy))

        if len(self.waveform) == 0: return

        sx = int(self._start * W)
        ex = int(self._end   * W)

        n = len(self.waveform)
        pen = QPen(QColor(MUTED), max(1.0, W / n))
        p.setPen(pen)
        for i, v in enumerate(self.waveform):
            x  = int(i * W / n)
            hy = int(v * cy * 0.85)
            p.drawLine(x, int(cy) - hy, x, int(cy) + hy)

        p.fillRect(sx, 0, ex - sx, H, QColor(ACCENT + "22"))
        p.fillRect(0,  0, sx,     H, QColor(0, 0, 0, 160))
        p.fillRect(ex, 0, W - ex, H, QColor(0, 0, 0, 160))

        p.setPen(QPen(QColor(ACCENT), 2))
        p.drawLine(sx, 0, sx, H)
        p.drawLine(ex, 0, ex, H)

        handle_h, handle_w = 30, 10
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(ACCENT))
        for hx in [sx, ex]:
            p.drawRoundedRect(hx - handle_w // 2, int(cy) - handle_h // 2, handle_w, handle_h, 4, 4)

        p.setPen(QColor(TEXT))
        p.setFont(QFont("JetBrains Mono", 9))
        st, et = self.get_times()
        p.drawText(sx + 6, 16, self._fmt(st))
        p.drawText(max(0, ex - 50), 16, self._fmt(et))

        if 0.0 <= self.playhead <= 1.0:
            px = int(self.playhead * W)
            p.setPen(QPen(QColor("#FFFFFF"), 2))
            p.drawLine(px, 0, px, H)
            
            tri = QPainterPath()
            tri.moveTo(px - 5, 0)
            tri.lineTo(px + 5, 0)
            tri.lineTo(px, 6)
            tri.closeSubpath()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#FFFFFF"))
            p.drawPath(tri)
            
        p.end()

    @staticmethod
    def _fmt(secs: float) -> str:
        m = int(secs // 60); s = secs % 60
        return f"{m}:{s:05.2f}"

    def _ratio(self, x):   return max(0.0, min(1.0, x / self.width()))
    def _hit(self, x, r):  return abs(x - r * self.width()) < 12

    def mousePressEvent(self, e):
        x = e.position().x()
        if self._hit(x, self._start):         self._drag = 'start'
        elif self._hit(x, self._end):         self._drag = 'end'
        elif self._start * self.width() < x < self._end * self.width():
            self._drag     = 'region'
            self._drag_off = x / self.width() - self._start

    def mouseMoveEvent(self, e):
        x = e.position().x(); r = self._ratio(x)
        if   self._drag == 'start':  self._start = min(r, self._end - 0.005)
        elif self._drag == 'end':    self._end   = max(r, self._start + 0.005)
        elif self._drag == 'region':
            w = self._end - self._start
            s = max(0.0, min(1.0 - w, r - self._drag_off))
            self._start, self._end = s, s + w
        if self._drag:
            self.selectionChanged.emit(self._start, self._end)
            self.update()
        cur = (Qt.CursorShape.SizeHorCursor
               if self._hit(x, self._start) or self._hit(x, self._end)
               else Qt.CursorShape.ArrowCursor)
        self.setCursor(cur)

    def mouseReleaseEvent(self, _):
        self._drag = None


# ─────────────────────────────────────────────────────────────────────────────
# Record Tab
# ─────────────────────────────────────────────────────────────────────────────

class RecordTab(QWidget):
    def __init__(self):
        super().__init__()
        self._pa          = pyaudio.PyAudio()
        self._stream      = None
        self._frames      = []
        self._recording   = False
        self._start_time  = 0.0
        self._channels    = 2
        self._sample_rate = 48000
        
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._update_timer)
        self._bridge = _AudioBridge()
        self._bridge.chunk_ready.connect(self._on_chunk_gui)
        
        self._build_ui()
        self._populate_devices()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        
        self._splitter = QSplitter(Qt.Orientation.Vertical)
        self._splitter.setHandleWidth(8)
        main_layout.addWidget(self._splitter)

        # --- Top Section ---
        top_scroll = QScrollArea()
        top_scroll.setWidgetResizable(True)
        top_scroll.setFrameShape(QFrame.Shape.NoFrame)
        top_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(16, 16, 16, 16)
        top_layout.setSpacing(12)
        top_scroll.setWidget(top_widget)
        self._splitter.addWidget(top_scroll)

        # Header
        hdr = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("Waveform Studio")
        title.setObjectName("heading")
        sub = QLabel("Capture system audio & mics.")
        sub.setObjectName("sub")
        title_col.addWidget(title)
        title_col.addWidget(sub)
        hdr.addLayout(title_col)
        hdr.addStretch()
        
        # Settings Button
        settings_btn = QPushButton("⚙️ Settings")
        settings_btn.setObjectName("flat")
        settings_btn.setFixedSize(100, 36)
        settings_btn.setToolTip("Settings")
        settings_btn.clicked.connect(self._open_settings)
        hdr.addWidget(settings_btn)
        
        top_layout.addLayout(hdr)

        # Settings Grid
        grid = QVBoxLayout()
        grid.setSpacing(10)

        # Card 1: Device
        dev_card = make_card()
        dev_layout = QVBoxLayout(dev_card)
        dev_layout.setContentsMargins(12, 12, 12, 12)
        
        dev_hdr = QHBoxLayout()
        dev_hdr.addWidget(QLabel("INPUT DEVICE", objectName="status"))
        dev_hdr.addStretch()
        ref_btn = QPushButton("↺ Refresh", objectName="flat")
        ref_btn.clicked.connect(self._populate_devices)
        dev_hdr.addWidget(ref_btn)
        dev_layout.addLayout(dev_hdr)

        self.device_combo = QComboBox()
        self.device_combo.setMinimumHeight(30)
        dev_layout.addWidget(self.device_combo)
        
        self.tip_label = QLabel("🔊 Speakers  ·  🎙 Mic")
        self.tip_label.setObjectName("sub")
        dev_layout.addWidget(self.tip_label)
        grid.addWidget(dev_card)

        # Card 2: Gain
        gain_card = make_card()
        gain_layout = QVBoxLayout(gain_card)
        gain_layout.setContentsMargins(12, 12, 12, 12)
        
        gain_hdr = QHBoxLayout()
        gain_hdr.addWidget(QLabel("AUDIO GAIN", objectName="status"))
        gain_hdr.addStretch()
        self.normalize_chk = QCheckBox("Normalize")
        self.normalize_chk.setChecked(True)
        self.normalize_chk.setStyleSheet(f"QCheckBox {{ color: {MUTED}; font-size: 11px; }}")
        gain_hdr.addWidget(self.normalize_chk)
        gain_layout.addLayout(gain_hdr)

        slider_row = QHBoxLayout()
        self.gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.gain_slider.setRange(1, 20)
        self.gain_slider.setValue(5)
        self.gain_slider.setEnabled(False)
        self.gain_value_lbl = QLabel("5×", objectName="badge")
        self.gain_value_lbl.setFixedWidth(32)
        self.gain_value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.gain_slider.valueChanged.connect(lambda v: self.gain_value_lbl.setText(f"{v}×"))
        self.normalize_chk.toggled.connect(lambda on: self.gain_slider.setEnabled(not on))
        
        slider_row.addWidget(self.gain_slider)
        slider_row.addWidget(self.gain_value_lbl)
        gain_layout.addLayout(slider_row)
        grid.addWidget(gain_card)

        top_layout.addLayout(grid)

        # Waveform Display
        wave_card = make_card()
        wave_card.setStyleSheet(f"QWidget#card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; }}")
        wave_layout = QVBoxLayout(wave_card)
        wave_layout.setContentsMargins(2, 2, 2, 2)
        self.wave = LiveWaveformWidget()
        wave_layout.addWidget(self.wave)
        top_layout.addWidget(wave_card, stretch=1)

        # Transport / Timer
        ctrl_layout = QVBoxLayout()
        ctrl_layout.setSpacing(6)
        ctrl_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.timer_label = QLabel("00:00.0")
        self.timer_label.setObjectName("timer")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl_layout.addWidget(self.timer_label)

        self.status_label = QLabel("READY TO RECORD")
        self.status_label.setObjectName("status")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl_layout.addWidget(self.status_label)

        ctrl_layout.addSpacing(6)

        self.rec_btn = QPushButton("⏺  Record")
        self.rec_btn.setObjectName("record")
        self.rec_btn.setFixedSize(160, 40)
        self.rec_btn.clicked.connect(self._toggle_record)
        
        btn_row = QHBoxLayout()
        btn_row.addStretch(); btn_row.addWidget(self.rec_btn); btn_row.addStretch()
        ctrl_layout.addLayout(btn_row)
        
        top_layout.addLayout(ctrl_layout)

        # --- Bottom Section ---
        bot_widget = QWidget()
        bot_layout = QVBoxLayout(bot_widget)
        bot_layout.setContentsMargins(16, 12, 16, 16)
        bot_layout.setSpacing(10)
        self._splitter.addWidget(bot_widget)

        list_hdr = QHBoxLayout()
        list_hdr.addWidget(QLabel("Recent Recordings", objectName="status"))
        list_hdr.addStretch()
        open_btn = QPushButton("📂 Folder", objectName="flat")
        open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(get_save_dir()))))
        list_hdr.addWidget(open_btn)
        bot_layout.addLayout(list_hdr)

        self.file_list = QListWidget()
        bot_layout.addWidget(self.file_list)
        self._refresh_list()

        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 0)
        QTimer.singleShot(0, lambda: self._splitter.setSizes([400, 200]))

    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self._refresh_list()

    def _populate_devices(self):
        self.device_combo.clear()
        try:
            loopback_added = False
            for i in range(self._pa.get_device_count()):
                d = self._pa.get_device_info_by_index(i)
                if d.get("isLoopbackDevice", False):
                    self.device_combo.addItem(f"🔊 {d['name']}", i)
                    loopback_added = True

            for i in range(self._pa.get_device_count()):
                d = self._pa.get_device_info_by_index(i)
                if d.get("maxInputChannels", 0) > 0 and not d.get("isLoopbackDevice", False):
                    self.device_combo.addItem(f"🎙 {d['name']}", i)

            if loopback_added:
                self.device_combo.setCurrentIndex(1)
            else:
                self.tip_label.setText("No loopback found. (Needs pyaudiowpatch)")
        except Exception as e:
            self.device_combo.addItem(f"Error: {e}", None)

    def _toggle_record(self):
        if not self._recording: self._start_recording()
        else:                   self._stop_recording()

    def _start_recording(self):
        dev_idx = self.device_combo.currentData()
        if dev_idx is None:
            QMessageBox.warning(self, "No device", "Please select a capture device.")
            return

        try:
            dev_info          = self._pa.get_device_info_by_index(dev_idx)
            self._channels    = max(1, int(dev_info["maxInputChannels"]))
            self._sample_rate = int(dev_info["defaultSampleRate"])

            self._frames.clear()
            self._recording  = True
            self._start_time = time.time()
            self.wave.recording = True
            self.wave.reset()

            self._stream = self._pa.open(
                format=pyaudio.paFloat32, channels=self._channels,
                rate=self._sample_rate, input=True,
                input_device_index=dev_idx, frames_per_buffer=BLOCK_SIZE,
                stream_callback=self._audio_callback,
            )
            self._stream.start_stream()

        except Exception as e:
            QMessageBox.critical(self, "Stream error", str(e))
            self._recording = self.wave.recording = False
            return

        self.rec_btn.setText("⏹ STOP")
        self.rec_btn.setStyleSheet(f"background: {CARD}; border: 2px solid {RED}; color: {RED};")
        self.status_label.setText("● RECORDING")
        self.status_label.setStyleSheet(f"color: {RED}; font-weight: bold;")
        self._tick_timer.start(100)

    def _audio_callback(self, in_data, frame_count, time_info, status):
        self._frames.append(in_data)
        chunk = np.frombuffer(in_data, dtype=np.float32).reshape(-1, self._channels)
        self._bridge.chunk_ready.emit(chunk)
        return (None, pyaudio.paContinue)

    @pyqtSlot(object)
    def _on_chunk_gui(self, chunk):
        self.wave.push(chunk)

    def _stop_recording(self):
        self._recording = False
        self._tick_timer.stop()
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

        self.rec_btn.setText("⏺ RECORD")
        self.rec_btn.setStyleSheet("") 
        self.status_label.setText("SAVING...")
        self.status_label.setStyleSheet(f"color: {MUTED};")
        self.wave.recording = False

        if self._frames: self._save_recording()
        else:            self.status_label.setText("READY TO RECORD")

    def _save_recording(self):
        raw  = b"".join(self._frames)
        data = np.frombuffer(raw, dtype=np.float32).reshape(-1, self._channels)

        peak = np.abs(data).max()
        if peak > 0:
            if self.normalize_chk.isChecked():
                data = data * (0.891 / peak)
            else:
                data = data * self.gain_slider.value()
        data = np.clip(data, -1.0, 1.0)

        # Save using dynamic filename and directory
        fname = generate_filename()
        save_dir = get_save_dir()
        path = save_dir / fname
        
        # Ensure unique filename
        ctr = 1
        base_path = path
        while path.exists():
            path = base_path.with_name(f"{base_path.stem}_{ctr}{base_path.suffix}")
            ctr += 1

        try:
            sf.write(str(path), data, self._sample_rate, subtype="FLOAT")
            self.status_label.setText(f"Saved: {path.name}")
        except Exception as e:
            self.status_label.setText(f"Error: {e}")
        self._refresh_list()

    def _update_timer(self):
        elapsed = time.time() - self._start_time
        m = int(elapsed // 60); s = elapsed % 60
        self.timer_label.setText(f"{m:02d}:{s:04.1f}")

    def _refresh_list(self):
        self.file_list.clear()
        save_dir = get_save_dir()
        wavs = sorted(save_dir.glob("*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)
        for wav in wavs[:40]:
            size = wav.stat().st_size / 1024
            self.file_list.addItem(f"🎵  {wav.name}   |   {size:.0f} KB")

    def closeEvent(self, e):
        if self._stream:
            self._stream.stop_stream(); self._stream.close()
        self._pa.terminate()
        super().closeEvent(e)


# ─────────────────────────────────────────────────────────────────────────────
# Trim Tab
# ─────────────────────────────────────────────────────────────────────────────

class TrimTab(QWidget):
    def __init__(self):
        super().__init__()
        self._audio_data = None
        self._samplerate = 48000
        self._duration   = 0.0
        self._filepath   = None
        self._start      = 0.0
        self._end        = 1.0
        
        self._pa            = pyaudio.PyAudio()
        self._pb_stream     = None
        self._pb_thread     = None
        self._pb_stop_evt   = None
        self._pb_loop       = False
        self._pb_pos        = 0.0
        self._pb_active     = False
        
        self._ph_timer = QTimer(self)
        self._ph_timer.setInterval(33)
        self._ph_timer.timeout.connect(self._tick_playhead)
        
        self.setAcceptDrops(True)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Header
        hdr = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(QLabel("Trim & Edit", objectName="heading"))
        title_col.addWidget(QLabel("Cut and export sections of audio.", objectName="sub"))
        hdr.addLayout(title_col)
        hdr.addStretch()
        root.addLayout(hdr)

        # File Picker
        pick_card = make_card()
        pick_layout = QHBoxLayout(pick_card)
        pick_layout.setContentsMargins(12, 12, 12, 12)
        
        self.file_line = QLineEdit()
        self.file_line.setPlaceholderText("Select or drop a file...")
        self.file_line.setReadOnly(True)
        self.file_line.setMinimumHeight(32)
        
        browse_btn = QPushButton("📂 Browse", objectName="primary")
        browse_btn.setMinimumHeight(32)
        browse_btn.clicked.connect(self._browse)
        
        pick_layout.addWidget(self.file_line)
        pick_layout.addWidget(browse_btn)
        root.addWidget(pick_card)

        # Waveform / Drop Zone
        self._drop_zone = make_card()
        dz_layout = QVBoxLayout(self._drop_zone)
        dz_layout.setContentsMargins(2, 2, 2, 2)
        
        self.wave = TrimWaveformWidget()
        self.wave.selectionChanged.connect(self._on_selection)
        dz_layout.addWidget(self.wave)

        self._drop_hint = QLabel("Drop an audio file here")
        self._drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_hint.setStyleSheet(f"color: {MUTED}; font-size: 14px; font-weight: 500;")
        dz_layout.addWidget(self._drop_hint)
        
        self.wave.hide()
        root.addWidget(self._drop_zone, stretch=1)

        # Info & Transport
        transport_card = make_card()
        trans_layout = QVBoxLayout(transport_card)
        trans_layout.setContentsMargins(16, 16, 16, 16)
        trans_layout.setSpacing(12)

        # Stats Grid 
        stats_layout = QGridLayout()
        self.start_label = QLabel("START: 0:00.00", objectName="badge")
        self.end_label   = QLabel("END: 0:00.00", objectName="badge")
        self.dur_label   = QLabel("DURATION: —", objectName="badge")
        
        stats_layout.addWidget(self.start_label, 0, 0)
        stats_layout.addWidget(self.end_label, 0, 1)
        stats_layout.addWidget(self.dur_label, 1, 0, 1, 2)
        trans_layout.addLayout(stats_layout)

        trans_layout.addWidget(h_sep())

        # Controls
        ctrl_layout = QVBoxLayout()
        ctrl_layout.setSpacing(10)
        
        top_ctrl_row = QHBoxLayout()
        self.play_btn = QPushButton("⏵ PLAY")
        self.play_btn.setObjectName("primary")
        self.play_btn.setFixedSize(100, 36)
        self.play_btn.clicked.connect(self._toggle_play)

        self.loop_btn = QPushButton("🔁 LOOP")
        self.loop_btn.setObjectName("flat")
        self.loop_btn.setFixedSize(80, 36)
        self.loop_btn.setCheckable(True)
        self.loop_btn.setStyleSheet(f"QPushButton:checked {{ background: {ACCENT}33; color: {ACCENT}; border-color: {ACCENT}; }}")
        self.loop_btn.toggled.connect(self._on_loop_toggled)

        self.pos_label = QLabel("0:00.00", objectName="timer")
        self.pos_label.setStyleSheet("font-size: 20px;")
        
        top_ctrl_row.addWidget(self.play_btn)
        top_ctrl_row.addWidget(self.loop_btn)
        top_ctrl_row.addStretch()
        top_ctrl_row.addWidget(self.pos_label)
        
        self.trim_btn = QPushButton("✂️ EXPORT SELECTION")
        self.trim_btn.setObjectName("primary")
        self.trim_btn.setStyleSheet(f"background: {CARD}; border: 2px solid {ACCENT}; color: {TEXT}; font-weight: 700;")
        self.trim_btn.setMinimumHeight(38)
        self.trim_btn.clicked.connect(self._do_trim)

        ctrl_layout.addLayout(top_ctrl_row)
        ctrl_layout.addWidget(self.trim_btn)
        
        trans_layout.addLayout(ctrl_layout)
        root.addWidget(transport_card)

        # Status
        self.result_label = QLabel("", objectName="status")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.result_label)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and self._is_audio(e.mimeData().urls()[0].toLocalFile()):
            e.acceptProposedAction()
            self._drop_zone.setStyleSheet(f"QWidget#card {{ background: {ACCENT}22; border: 2px dashed {ACCENT}; border-radius: 10px; }}")

    def dragLeaveEvent(self, e):
        self._drop_zone.setStyleSheet("")
        e.accept()

    def dropEvent(self, e):
        self._drop_zone.setStyleSheet("")
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if self._is_audio(path):
                self._load_file(path)
                e.acceptProposedAction()

    @staticmethod
    def _is_audio(path: str) -> bool:
        return Path(path).suffix.lower() in {".wav", ".flac", ".ogg", ".aiff", ".aif", ".mp3"}

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Audio File", str(get_save_dir()), "Audio Files (*.wav *.flac *.ogg *.aiff);;All files (*)")
        if path: self._load_file(path)

    def _load_file(self, path: str):
        self._stop_playback()
        try:
            data, sr = sf.read(path, always_2d=True, dtype='float32')
        except Exception as e:
            QMessageBox.critical(self, "Load error", str(e)); return
            
        self._drop_hint.hide()
        self.wave.show()
        self._filepath   = path
        self._audio_data = data
        self._samplerate = sr
        self._duration   = len(data) / sr
        self.file_line.setText(Path(path).name)
        
        n    = min(3000, len(data))
        step = max(1, len(data) // n)
        mono = data[::step].mean(axis=1)
        mx   = mono.max() or 1.0
        self.wave.load(mono / mx, self._duration)
        self._update_labels(0.0, 1.0)

    def _on_selection(self, s, e):
        self._start = s; self._end = e
        self._update_labels(s, e)
        if self._pb_active: self._stop_playback()

    def _update_labels(self, s, e):
        st, et = s * self._duration, e * self._duration
        def fmt(v):
            m = int(v // 60); sec = v % 60
            return f"{m}:{sec:05.2f}"
        self.start_label.setText(f"START: {fmt(st)}")
        self.end_label.setText(f"END: {fmt(et)}")
        self.dur_label.setText(f"DURATION: {fmt(et - st)}")

    def _toggle_play(self):
        if self._pb_active: self._stop_playback()
        else:               self._start_playback()

    def _on_loop_toggled(self, on: bool):
        self._pb_loop = on

    def _start_playback(self):
        if self._audio_data is None: return
        self._stop_playback()

        s_samp = int(self._start * len(self._audio_data))
        e_samp = int(self._end   * len(self._audio_data))
        region = self._audio_data[s_samp:e_samp].copy()
        if len(region) == 0: return

        ch, sr = region.shape[1], self._samplerate
        start_r, span = self._start, self._end - self._start

        self._pb_stop_evt = threading.Event()
        self._pb_pos      = self._start
        self._pb_active   = True
        self.play_btn.setText("⏸ PAUSE")
        self.play_btn.setStyleSheet(f"background: {CARD}; border: 2px solid {ACCENT}; color: {TEXT};")

        def run():
            stop = self._pb_stop_evt
            loop = lambda: self._pb_loop
            try:
                stream = self._pa.open(format=pyaudio.paFloat32, channels=ch, rate=sr, output=True, frames_per_buffer=1024)
            except Exception:
                self._pb_active = False; return

            CHUNK = 1024
            while not stop.is_set():
                idx, total = 0, len(region)
                while idx < total and not stop.is_set():
                    end_idx = min(idx + CHUNK, total)
                    stream.write(region[idx:end_idx].astype(np.float32).tobytes())
                    self._pb_pos = start_r + (idx / total) * span
                    idx = end_idx
                if not loop() or stop.is_set(): break
            
            stream.stop_stream(); stream.close()
            QMetaObject.invokeMethod(self, "_on_playback_finished", Qt.ConnectionType.QueuedConnection)

        self._pb_thread = threading.Thread(target=run, daemon=True)
        self._pb_thread.start()
        self._ph_timer.start()

    def _stop_playback(self):
        if self._pb_stop_evt: self._pb_stop_evt.set()
        if self._pb_thread and self._pb_thread.is_alive(): self._pb_thread.join(timeout=0.5)
        self._pb_thread = self._pb_stop_evt = None
        self._pb_active = False
        self._ph_timer.stop()
        self.wave.playhead = -1.0
        self.wave.update()
        if hasattr(self, "play_btn"):
            self.play_btn.setText("⏵ PLAY")
            self.play_btn.setStyleSheet("")

    @pyqtSlot()
    def _on_playback_finished(self):
        self._stop_playback()

    def _tick_playhead(self):
        if self._pb_active:
            self.wave.playhead = self._pb_pos
            self.wave.update()
            secs = self._pb_pos * self._duration
            m, s = int(secs // 60), secs % 60
            self.pos_label.setText(f"{m}:{s:05.2f}")

    def _do_trim(self):
        if self._audio_data is None:
            QMessageBox.information(self, "No file", "Please load an audio file first.")
            return
        s = int(self._start * len(self._audio_data))
        e = int(self._end   * len(self._audio_data))
        tr = self._audio_data[s:e]
        
        src = Path(self._filepath)
        out = src.parent / f"{src.stem}_trimmed{src.suffix}"
        ctr = 1
        while out.exists():
            out = src.parent / f"{src.stem}_trimmed_{ctr}{src.suffix}"
            ctr += 1
            
        try:
            sf.write(str(out), tr, self._samplerate)
            self.result_label.setText(f"✅ Saved successfully: {out.name}")
            self.result_label.setStyleSheet(f"color: #10B981; font-weight: bold;")
            QTimer.singleShot(4000, lambda: self.result_label.setText(""))
        except Exception as e:
            QMessageBox.critical(self, "Save error", str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Waveform Studio")
        self.setWindowIcon(QIcon("ocean.png"))
        self.setMinimumSize(400, 500)
        self.resize(450, 600)

        central = QWidget()
        central.setObjectName("root")
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tabs = QTabWidget()
        tabs.addTab(RecordTab(), "⏺ Record")
        tabs.addTab(TrimTab(),   "✂️ Trim")
        layout.addWidget(tabs)

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("WaveformStudio")
    app.setOrganizationName("WaveformStudioApp")
    app.setStyleSheet(STYLE)
    
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
        
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":

    main()
