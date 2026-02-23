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
    chunk_ready = pyqtSignal(object)   # emits np.ndarray from audio thread


# ── Constants ─────────────────────────────────────────────────────────────────
BLOCK_SIZE  = 1024
SAVE_DIR    = Path.cwd()

ACCENT  = "#7C6EFA"
BG      = "#0C0C0E"
SURFACE = "#141417"
CARD    = "#1C1C21"
BORDER  = "#2A2A32"
TEXT    = "#F0F0F5"
MUTED   = "#606070"
RED     = "#FA4D56"

STYLE = f"""
* {{ font-family: 'SF Pro Display', 'Segoe UI Variable', 'Ubuntu', sans-serif; }}

QMainWindow, QWidget#root {{ background: {BG}; }}
QWidget {{ background: transparent; color: {TEXT}; font-size: 13px; }}

QTabWidget::pane {{ border: none; background: {BG}; }}
QTabBar {{ background: {SURFACE}; border-bottom: 1px solid {BORDER}; }}
QTabBar::tab {{
    background: transparent; color: {MUTED};
    padding: 13px 28px; border: none;
    border-bottom: 2px solid transparent;
    font-size: 13px; letter-spacing: 0.3px;
    min-width: 100px;
}}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 2px solid {ACCENT}; }}
QTabBar::tab:hover:!selected {{ color: #aaa; }}

QPushButton {{
    background: {CARD}; color: {TEXT};
    border: 1px solid {BORDER}; border-radius: 8px;
    padding: 8px 16px; font-size: 13px;
}}
QPushButton:hover {{ background: #22222A; border-color: #3A3A45; }}
QPushButton:pressed {{ background: #1A1A20; }}

QPushButton#primary {{
    background: {ACCENT}; border: none; color: white;
    font-weight: 600; border-radius: 10px;
    padding: 11px 28px; font-size: 14px;
}}
QPushButton#primary:hover {{ background: #8C7EFF; }}
QPushButton#primary:pressed {{ background: #6C5EEA; }}

QPushButton#danger {{
    background: {RED}; border: none; color: white;
    font-weight: 600; border-radius: 10px;
    padding: 11px 28px; font-size: 14px;
}}
QPushButton#danger:hover {{ background: #FF5D65; }}

QPushButton#flat {{
    background: transparent; border: 1px solid {BORDER};
    border-radius: 7px; padding: 7px 14px; color: {MUTED};
    font-size: 12px;
}}
QPushButton#flat:hover {{ color: {TEXT}; border-color: {ACCENT}; }}

QComboBox {{
    background: {CARD}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 7px 12px;
    color: {TEXT}; font-size: 12px;
    selection-background-color: {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {MUTED};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background: {CARD}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 4px;
    selection-background-color: #2C2C36; outline: none;
}}

QListWidget {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 10px; color: {TEXT};
    font-size: 12px; padding: 4px; outline: none;
}}
QListWidget::item {{
    padding: 9px 12px; border-radius: 6px; color: #C0C0CC;
}}
QListWidget::item:selected {{ background: #22222A; color: {TEXT}; }}
QListWidget::item:hover:!selected {{ background: #1A1A20; }}

QScrollBar:vertical {{
    background: transparent; width: 5px; margin: 4px 2px; border: none;
}}
QScrollBar::handle:vertical {{
    background: {BORDER}; border-radius: 2px; min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0; background: none;
}}
QScrollBar:horizontal {{
    background: transparent; height: 5px; margin: 2px 4px; border: none;
}}
QScrollBar::handle:horizontal {{ background: {BORDER}; border-radius: 2px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0; background: none;
}}

QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QSplitter::handle:vertical {{
    background: {BORDER}; height: 6px; margin: 0;
    border-top: 1px solid {BORDER}; border-bottom: 1px solid {BORDER};
}}
QSplitter::handle:vertical:hover {{
    background: {ACCENT};
}}

QLabel#heading {{
    font-size: 20px; font-weight: 700; color: {TEXT}; letter-spacing: -0.5px;
}}
QLabel#sub   {{ font-size: 12px; color: {MUTED}; letter-spacing: 0.2px; }}
QLabel#timer {{
    font-size: 48px; font-weight: 200; color: {TEXT}; letter-spacing: 4px;
}}
QLabel#status {{ font-size: 11px; color: {MUTED}; letter-spacing: 1px; }}
QLabel#badge {{
    background: {CARD}; border: 1px solid {BORDER};
    border-radius: 6px; padding: 4px 10px; font-size: 11px; color: {MUTED};
}}
QLineEdit {{
    background: {CARD}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 8px 12px;
    color: {TEXT}; font-size: 12px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus {{ border-color: {ACCENT}; }}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Live Waveform  (Record tab)
# ─────────────────────────────────────────────────────────────────────────────

class LiveWaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.samples   = np.zeros(512)
        self.recording = False
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(60)
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
        p  = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        cy   = H / 2

        p.fillRect(self.rect(), QColor(SURFACE))
        p.setPen(QPen(QColor(BORDER), 1))
        p.drawLine(0, int(cy), W, int(cy))

        if not self.recording:
            p.setPen(QColor(MUTED))
            f = p.font(); f.setPointSize(10); p.setFont(f)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "● press record")
            return

        n   = len(self.samples)
        top = QPainterPath()
        top.moveTo(0, cy)
        for i, v in enumerate(self.samples):
            top.lineTo(i * W / n, cy - v * cy * 0.82)
        top.lineTo(W, cy)

        bot = QPainterPath()
        bot.moveTo(0, cy)
        for i, v in enumerate(self.samples):
            bot.lineTo(i * W / n, cy + v * cy * 0.82)
        bot.lineTo(W, cy)

        g1 = QLinearGradient(0, 0, 0, H)
        g1.setColorAt(0,   QColor(ACCENT + "BB"))
        g1.setColorAt(0.5, QColor(ACCENT + "55"))
        g1.setColorAt(1,   QColor(ACCENT + "00"))
        p.fillPath(top, QBrush(g1))

        g2 = QLinearGradient(0, 0, 0, H)
        g2.setColorAt(0,   QColor(ACCENT + "00"))
        g2.setColorAt(0.5, QColor(ACCENT + "33"))
        g2.setColorAt(1,   QColor(ACCENT + "99"))
        p.fillPath(bot, QBrush(g2))
        p.end()


# ─────────────────────────────────────────────────────────────────────────────
# Trim Waveform  (Trim tab)
# ─────────────────────────────────────────────────────────────────────────────

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
        self.playhead    = -1.0   # 0..1 ratio; <0 means hidden
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(80)
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

        p.fillRect(self.rect(), QColor(SURFACE))

        if len(self.waveform) == 0:
            p.setPen(QColor(MUTED))
            f = p.font(); f.setPointSize(10); p.setFont(f)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Load an audio file to trim")
            return

        sx = int(self._start * W)
        ex = int(self._end   * W)

        p.fillRect(0,  0, sx,     H, QColor(0, 0, 0, 130))
        p.fillRect(ex, 0, W - ex, H, QColor(0, 0, 0, 130))

        n   = len(self.waveform)
        pen = QPen(QColor(ACCENT + "99"), max(1.0, W / n))
        p.setPen(pen)
        for i, v in enumerate(self.waveform):
            x  = int(i * W / n)
            hy = int(v * cy * 0.82)
            p.drawLine(x, int(cy) - hy, x, int(cy) + hy)

        p.fillRect(sx, 0, ex - sx, H, QColor(ACCENT + "1A"))

        hw = max(3, W // 180)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(ACCENT))
        p.drawRect(sx - hw // 2, 0, hw, H)
        p.drawRect(ex - hw // 2, 0, hw, H)

        gh, gw = min(32, H // 3), 14
        for hx in [sx, ex]:
            p.drawRoundedRect(hx - gw // 2, int(cy) - gh // 2, gw, gh, 4, 4)

        p.setPen(QColor(TEXT))
        f = QFont("Courier New"); f.setPointSize(9); p.setFont(f)
        st, et = self.get_times()
        p.drawText(sx + 6, 16, self._fmt(st))
        p.drawText(max(0, ex - 54), 16, self._fmt(et))

        # ── playhead ─────────────────────────────────────────────────────────
        if 0.0 <= self.playhead <= 1.0:
            px = int(self.playhead * W)
            # bright white line
            p.setPen(QPen(QColor("#FFFFFF"), 1.5))
            p.drawLine(px, 0, px, H)
            # small downward triangle at top
            tri = QPainterPath()
            tri.moveTo(px - 6, 0)
            tri.lineTo(px + 6, 0)
            tri.lineTo(px,     10)
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
    def _hit(self, x, r):  return abs(x - r * self.width()) < 14

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
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def h_sep():
    w = QFrame()
    w.setFrameShape(QFrame.Shape.HLine)
    w.setStyleSheet(f"background: {BORDER}; max-height: 1px; border: none;")
    return w


# ─────────────────────────────────────────────────────────────────────────────
# Record Tab
# ─────────────────────────────────────────────────────────────────────────────

class RecordTab(QWidget):
    def __init__(self):
        super().__init__()
        self._pa         = pyaudio.PyAudio()
        self._stream     = None
        self._frames: list[bytes] = []
        self._recording  = False
        self._start_time = 0.0
        self._channels   = 2
        self._sample_rate = 48000
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._update_timer)
        # thread-safe bridge: audio callback → GUI
        self._bridge = _AudioBridge()
        self._bridge.chunk_ready.connect(self._on_chunk_gui)
        self._build_ui()
        self._populate_devices()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._splitter = QSplitter(Qt.Orientation.Vertical)
        self._splitter.setChildrenCollapsible(False)
        outer.addWidget(self._splitter)

        # ── top panel ────────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._top_widget = QWidget()
        self._top_layout = top = QVBoxLayout(self._top_widget)
        top.setContentsMargins(28, 24, 28, 18)
        top.setSpacing(16)
        scroll.setWidget(self._top_widget)
        self._splitter.addWidget(scroll)

        # header
        hdr = QHBoxLayout()
        title = QLabel("🌊 Wave"); title.setObjectName("heading")
        sub   = QLabel("System Audio Recorder"); sub.setObjectName("sub")
        col   = QVBoxLayout(); col.setSpacing(2)
        col.addWidget(title); col.addWidget(sub)
        hdr.addLayout(col); hdr.addStretch()
        top.addLayout(hdr)
        top.addWidget(h_sep())

        # device row
        dev_row = QHBoxLayout()
        lbl = QLabel("Capture"); lbl.setObjectName("badge")
        self.device_combo = QComboBox()
        self.device_combo.setSizePolicy(QSizePolicy.Policy.Expanding,
                                        QSizePolicy.Policy.Fixed)
        ref = QPushButton("↺ Refresh"); ref.setObjectName("flat")
        ref.setFixedWidth(90); ref.setToolTip("Refresh devices")
        ref.clicked.connect(self._populate_devices)
        dev_row.addWidget(lbl)
        dev_row.addWidget(self.device_combo)
        dev_row.addWidget(ref)
        top.addLayout(dev_row)

        self.tip_label = QLabel(
            "🔊 Loopback devices capture speaker output  ·  🎙 Mic devices capture microphone input"
        )
        self.tip_label.setObjectName("status"); self.tip_label.setWordWrap(True)
        top.addWidget(self.tip_label)

        # ── gain row ─────────────────────────────────────────────────────────
        gain_row = QHBoxLayout()

        self.normalize_chk = QCheckBox("Normalize to -1 dBFS")
        self.normalize_chk.setChecked(True)
        self.normalize_chk.setStyleSheet(f"""
            QCheckBox {{ color: {MUTED}; font-size: 12px; spacing: 6px; }}
            QCheckBox::indicator {{
                width: 14px; height: 14px; border-radius: 3px;
                border: 1px solid {BORDER}; background: {CARD};
            }}
            QCheckBox::indicator:checked {{
                background: {ACCENT}; border-color: {ACCENT};
            }}
        """)

        gain_lbl = QLabel("Manual gain"); gain_lbl.setObjectName("badge")
        self.gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.gain_slider.setRange(1, 20)
        self.gain_slider.setValue(5)
        self.gain_slider.setEnabled(False)   # disabled when normalize is on
        self.gain_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {BORDER}; height: 4px; border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {ACCENT}; width: 16px; height: 16px;
                margin: -6px 0; border-radius: 8px;
            }}
            QSlider::sub-page:horizontal {{
                background: {ACCENT}; height: 4px; border-radius: 2px;
            }}
            QSlider::handle:horizontal:disabled {{
                background: {BORDER};
            }}
            QSlider::sub-page:horizontal:disabled {{
                background: {BORDER};
            }}
        """)
        self.gain_value_lbl = QLabel("5×"); self.gain_value_lbl.setObjectName("badge")
        self.gain_value_lbl.setFixedWidth(32)
        self.gain_slider.valueChanged.connect(
            lambda v: self.gain_value_lbl.setText(f"{v}×"))
        self.normalize_chk.toggled.connect(
            lambda on: self.gain_slider.setEnabled(not on))

        gain_row.addWidget(self.normalize_chk)
        gain_row.addStretch()
        gain_row.addWidget(gain_lbl)
        gain_row.addWidget(self.gain_slider)
        gain_row.addWidget(self.gain_value_lbl)
        top.addLayout(gain_row)

        # waveform
        self.wave = LiveWaveformWidget()
        top.addWidget(self.wave, stretch=1)

        # timer + button
        ctrl = QVBoxLayout(); ctrl.setSpacing(10)
        ctrl.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.timer_label = QLabel("00:00.0")
        self.timer_label.setObjectName("timer")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setSizePolicy(QSizePolicy.Policy.Expanding,
                                       QSizePolicy.Policy.Preferred)
        ctrl.addWidget(self.timer_label)

        self.status_label = QLabel("READY")
        self.status_label.setObjectName("status")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl.addWidget(self.status_label)

        self.rec_btn = QPushButton("⏺  Record")
        self.rec_btn.setObjectName("primary")
        self.rec_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.rec_btn.setMaximumWidth(240)
        self.rec_btn.clicked.connect(self._toggle_record)

        btn_row = QHBoxLayout()
        btn_row.addStretch(); btn_row.addWidget(self.rec_btn); btn_row.addStretch()
        ctrl.addLayout(btn_row)
        top.addLayout(ctrl)

        # ── bottom panel: file list ───────────────────────────────────────────
        self._bot_widget = QWidget()
        self._bot_layout = bot = QVBoxLayout(self._bot_widget)
        bot.setContentsMargins(28, 14, 28, 20)
        bot.setSpacing(10)
        self._splitter.addWidget(self._bot_widget)

        list_hdr = QHBoxLayout()
        list_hdr.addWidget(QLabel("Recordings"))
        list_hdr.addStretch()
        open_btn = QPushButton("Open folder"); open_btn.setObjectName("flat")
        open_btn.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(SAVE_DIR))))
        list_hdr.addWidget(open_btn)
        bot.addLayout(list_hdr)

        self.file_list = QListWidget()
        self.file_list.setSizePolicy(QSizePolicy.Policy.Expanding,
                                     QSizePolicy.Policy.Expanding)
        bot.addWidget(self.file_list)
        self._refresh_list()

        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 0)
        # minimum heights so neither panel can be squashed to nothing
        scroll.setMinimumHeight(400)
        self._bot_widget.setMinimumHeight(120)
        # use QTimer to set pixel sizes after widget is realized
        QTimer.singleShot(0, self._init_splitter_sizes)

    def _init_splitter_sizes(self):
        """Set a sensible initial split: top gets ~65%, bottom ~35%."""
        total = self._splitter.height()
        if total > 0:
            self._splitter.setSizes([int(total * 0.65), int(total * 0.35)])

    # ── responsive ───────────────────────────────────────────────────────────
    def resizeEvent(self, e):
        super().resizeEvent(e)
        w  = self.width()
        pt = max(20, min(54, int(w * 0.057)))
        f  = self.timer_label.font()
        if pt > 0 and f.pointSize() != pt:
            f.setPointSize(pt); self.timer_label.setFont(f)
        m = max(12, min(28, w // 28))
        self._top_layout.setContentsMargins(m, 20, m, 16)
        self._bot_layout.setContentsMargins(m, 12, m, 18)

    # ── device population ─────────────────────────────────────────────────────
    def _populate_devices(self):
        self.device_combo.clear()
        try:
            # First: show loopback devices (speaker capture) — pyaudiowpatch only
            loopback_added = False
            for i in range(self._pa.get_device_count()):
                d = self._pa.get_device_info_by_index(i)
                if d.get("isLoopbackDevice", False):
                    self.device_combo.addItem(f"🔊  {d['name']}", i)
                    loopback_added = True

            # Then: show regular input devices (microphones etc.)
            for i in range(self._pa.get_device_count()):
                d = self._pa.get_device_info_by_index(i)
                if (d.get("maxInputChannels", 0) > 0
                        and not d.get("isLoopbackDevice", False)):
                    self.device_combo.addItem(f"🎙  {d['name']}", i)

            # Pre-select default loopback (first loopback entry = default speakers)
            if loopback_added:
                self.device_combo.setCurrentIndex(1)
                self.tip_label.setText(
                    "🔊 Loopback = captures speaker output  ·  "
                    "🎙 Mic = captures microphone input")
            else:
                self.tip_label.setText(
                    "No loopback devices found. "
                    "Install pyaudiowpatch for speaker capture on Windows.")
        except Exception as e:
            self.device_combo.addItem(f"Error: {e}", None)

    # ── recording ─────────────────────────────────────────────────────────────
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
                format            = pyaudio.paFloat32,
                channels          = self._channels,
                rate              = self._sample_rate,
                input             = True,
                input_device_index= dev_idx,
                frames_per_buffer = BLOCK_SIZE,
                stream_callback   = self._audio_callback,
            )
            self._stream.start_stream()

        except Exception as e:
            QMessageBox.critical(self, "Stream error", str(e))
            self._recording = self.wave.recording = False
            return

        self.rec_btn.setText("⏹  Stop")
        self.rec_btn.setObjectName("danger")
        self.rec_btn.setStyle(self.rec_btn.style())
        self.status_label.setText("● RECORDING")
        self._tick_timer.start(100)

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Called from PyAudio's background thread."""
        self._frames.append(in_data)
        # Convert to numpy and send to GUI for waveform display
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

        self.rec_btn.setText("⏺  Record")
        self.rec_btn.setObjectName("primary")
        self.rec_btn.setStyle(self.rec_btn.style())
        self.status_label.setText("SAVING…")
        self.wave.recording = False

        if self._frames: self._save_recording()
        else:            self.status_label.setText("READY")

    def _save_recording(self):
        # Convert raw float32 bytes → numpy array
        raw  = b"".join(self._frames)
        data = np.frombuffer(raw, dtype=np.float32).reshape(-1, self._channels)

        # ── Apply gain / normalize before saving ─────────────────────────────
        peak = np.abs(data).max()
        if peak > 0:
            if self.normalize_chk.isChecked():
                # Normalize to -1 dBFS
                target = 0.891   # 10 ** (-1/20)
                data   = data * (target / peak)
            else:
                # Manual gain boost
                gain = self.gain_slider.value()
                data = data * gain
        data = np.clip(data, -1.0, 1.0)

        ts   = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = SAVE_DIR / f"recording_{ts}.wav"
        try:
            sf.write(str(path), data, self._sample_rate, subtype="FLOAT")
            self.status_label.setText(f"Saved → {path.name}")
        except Exception as e:
            self.status_label.setText(f"Error: {e}")
        self._refresh_list()

    def _update_timer(self):
        elapsed = time.time() - self._start_time
        m = int(elapsed // 60); s = elapsed % 60
        self.timer_label.setText(f"{m:02d}:{s:04.1f}")

    def _refresh_list(self):
        self.file_list.clear()
        wavs = sorted(SAVE_DIR.glob("*.wav"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
        for wav in wavs[:40]:
            size = wav.stat().st_size / 1024
            self.file_list.addItem(f"  {wav.name}   ·   {size:.0f} KB")

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
        self._drop_active   = False
        # playback state
        self._pa            = pyaudio.PyAudio()
        self._pb_stream     = None
        self._pb_thread     = None
        self._pb_stop_evt   = None
        self._pb_loop       = False
        self._pb_pos        = 0.0   # current play position as 0..1 ratio
        self._pb_active     = False
        self._ph_timer      = QTimer(self)
        self._ph_timer.setInterval(33)   # ~30fps
        self._ph_timer.timeout.connect(self._tick_playhead)
        self._build_ui()
        self.setAcceptDrops(True)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        self._root_layout = root = QVBoxLayout(container)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)
        scroll.setWidget(container)
        outer.addWidget(scroll)

        hdr = QHBoxLayout()
        title = QLabel("Trim"); title.setObjectName("heading")
        sub   = QLabel("Cut / Trim Audio"); sub.setObjectName("sub")
        col   = QVBoxLayout(); col.setSpacing(2)
        col.addWidget(title); col.addWidget(sub)
        hdr.addLayout(col); hdr.addStretch()
        root.addLayout(hdr)
        root.addWidget(h_sep())

        pick = QHBoxLayout()
        self.file_line = QLineEdit()
        self.file_line.setPlaceholderText("Select a .wav / .flac / .ogg file…")
        self.file_line.setReadOnly(True)
        self.file_line.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        browse = QPushButton("Browse"); browse.setObjectName("flat")
        browse.clicked.connect(self._browse)
        pick.addWidget(self.file_line); pick.addWidget(browse)
        root.addLayout(pick)

        # ── waveform wrapped in a drop-zone container ───────────────────────
        self._drop_zone = QWidget()
        self._drop_zone.setSizePolicy(QSizePolicy.Policy.Expanding,
                                      QSizePolicy.Policy.Expanding)
        dz_layout = QVBoxLayout(self._drop_zone)
        dz_layout.setContentsMargins(0, 0, 0, 0)
        dz_layout.setSpacing(0)

        self.wave = TrimWaveformWidget()
        self.wave.selectionChanged.connect(self._on_selection)
        self.wave.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.wave.setMinimumHeight(100)
        dz_layout.addWidget(self.wave)

        # Overlay hint shown while no file is loaded
        self._drop_hint = QLabel("Drop an audio file here  or  use Browse above")
        self._drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_hint.setObjectName("drop_hint")
        self._drop_hint.setStyleSheet(f"""
            QLabel#drop_hint {{
                color: {MUTED};
                font-size: 13px;
                letter-spacing: 0.3px;
                border: 2px dashed {BORDER};
                border-radius: 10px;
                padding: 24px;
                background: transparent;
            }}
        """)
        dz_layout.addWidget(self._drop_hint)

        self.wave.hide()          # shown once a file is loaded
        root.addWidget(self._drop_zone, stretch=1)

        time_row = QHBoxLayout(); time_row.setSpacing(8)
        self.start_label = QLabel("Start: 0:00.00"); self.start_label.setObjectName("badge")
        self.end_label   = QLabel("End:   0:00.00"); self.end_label.setObjectName("badge")
        self.dur_label   = QLabel("Duration: —");    self.dur_label.setObjectName("badge")
        for lbl in [self.start_label, self.end_label, self.dur_label]:
            time_row.addWidget(lbl)
        time_row.addStretch()
        root.addLayout(time_row)

        # ── transport bar ────────────────────────────────────────────────────
        transport = QHBoxLayout(); transport.setSpacing(10)

        self.play_btn = QPushButton("▶  Play")
        self.play_btn.setObjectName("primary")
        self.play_btn.setFixedWidth(110)
        self.play_btn.clicked.connect(self._toggle_play)

        self.loop_btn = QPushButton("⟳  Loop")
        self.loop_btn.setObjectName("flat")
        self.loop_btn.setFixedWidth(90)
        self.loop_btn.setCheckable(True)
        self.loop_btn.setStyleSheet(f"""
            QPushButton#flat {{
                background: transparent; border: 1px solid {BORDER};
                border-radius: 7px; padding: 7px 14px; color: {MUTED};
                font-size: 12px;
            }}
            QPushButton#flat:hover  {{ color: {TEXT}; border-color: {ACCENT}; }}
            QPushButton#flat:checked {{
                background: {ACCENT}22; border-color: {ACCENT}; color: {ACCENT};
            }}
        """)
        self.loop_btn.toggled.connect(self._on_loop_toggled)

        self.pos_label = QLabel("0:00.00"); self.pos_label.setObjectName("badge")
        self.pos_label.setFixedWidth(70)
        self.pos_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        transport.addWidget(self.play_btn)
        transport.addWidget(self.loop_btn)
        transport.addWidget(self.pos_label)
        transport.addStretch()
        root.addLayout(transport)

        hint = QLabel("Drag the purple handles or the selected region to set in / out points")
        hint.setObjectName("status"); hint.setWordWrap(True)
        root.addWidget(hint)
        root.addWidget(h_sep())

        act = QHBoxLayout(); act.setSpacing(12)
        self.trim_btn = QPushButton("✂  Trim and Save")
        self.trim_btn.setObjectName("primary")
        self.trim_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.trim_btn.setMaximumWidth(220)
        self.trim_btn.clicked.connect(self._do_trim)
        self.result_label = QLabel(""); self.result_label.setObjectName("status")
        act.addWidget(self.trim_btn); act.addWidget(self.result_label); act.addStretch()
        root.addLayout(act)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        m = max(12, min(28, self.width() // 28))
        self._root_layout.setContentsMargins(m, 20, m, 20)

    # ── drag-and-drop ─────────────────────────────────────────────────────────
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            urls = e.mimeData().urls()
            if urls and self._is_audio(urls[0].toLocalFile()):
                e.acceptProposedAction()
                self._set_drop_highlight(True)
                return
        e.ignore()

    def dragLeaveEvent(self, e):
        self._set_drop_highlight(False)
        e.accept()

    def dropEvent(self, e):
        self._set_drop_highlight(False)
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if self._is_audio(path):
                self._load_file(path)
                e.acceptProposedAction()
                return
        e.ignore()

    @staticmethod
    def _is_audio(path: str) -> bool:
        return Path(path).suffix.lower() in {".wav", ".flac", ".ogg", ".aiff", ".aif", ".mp3"}

    def _set_drop_highlight(self, on: bool):
        self._drop_active = on
        colour = ACCENT if on else BORDER
        self._drop_hint.setStyleSheet(f"""
            QLabel#drop_hint {{
                color: {"#B0A8FF" if on else MUTED};
                font-size: 13px;
                letter-spacing: 0.3px;
                border: 2px dashed {colour};
                border-radius: 10px;
                padding: 24px;
                background: {"#7C6EFA11" if on else "transparent"};
            }}
        """)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Audio File", str(SAVE_DIR),
            "Audio Files (*.wav *.flac *.ogg *.aiff);;All files (*)")
        if path: self._load_file(path)

    def _load_file(self, path: str):
        self._stop_playback()
        try:
            data, sr = sf.read(path, always_2d=True, dtype='float32')
        except Exception as e:
            QMessageBox.critical(self, "Load error", str(e)); return
        # show waveform, hide the drop hint
        self._drop_hint.hide()
        self.wave.show()
        self._filepath   = path
        self._audio_data = data
        self._samplerate = sr
        self._duration   = len(data) / sr
        self.file_line.setText(Path(path).name)
        n    = min(2000, len(data))
        step = max(1, len(data) // n)
        mono = data[::step].mean(axis=1)
        mx   = mono.max() or 1.0
        self.wave.load(mono / mx, self._duration)
        self._update_labels(0.0, 1.0)

    def _on_selection(self, s, e):
        self._start = s; self._end = e
        self._update_labels(s, e)
        if self._pb_active:
            self._stop_playback()

    def _update_labels(self, s, e):
        st, et = s * self._duration, e * self._duration
        def fmt(v):
            m = int(v // 60); sec = v % 60
            return f"{m}:{sec:05.2f}"
        self.start_label.setText(f"Start: {fmt(st)}")
        self.end_label.setText(  f"End:   {fmt(et)}")
        self.dur_label.setText(  f"Duration: {fmt(et - st)}")

    # ── playback ──────────────────────────────────────────────────────────────
    def _toggle_play(self):
        if self._pb_active:
            self._stop_playback()
        else:
            self._start_playback()

    def _on_loop_toggled(self, on: bool):
        self._pb_loop = on

    def _start_playback(self):
        if self._audio_data is None:
            return
        self._stop_playback()   # clean up any previous stream

        s_samp = int(self._start * len(self._audio_data))
        e_samp = int(self._end   * len(self._audio_data))
        region = self._audio_data[s_samp:e_samp].copy()
        if len(region) == 0:
            return

        ch       = region.shape[1]
        sr       = self._samplerate
        dur      = len(region) / sr
        start_r  = self._start
        span     = self._end - self._start

        self._pb_stop_evt = threading.Event()
        self._pb_pos      = self._start
        self._pb_active   = True
        self.play_btn.setText("⏹  Stop")

        def run():
            stop = self._pb_stop_evt
            loop = lambda: self._pb_loop

            try:
                stream = self._pa.open(
                    format             = pyaudio.paFloat32,
                    channels           = ch,
                    rate               = sr,
                    output             = True,
                    frames_per_buffer  = 1024,
                )
            except Exception:
                self._pb_active = False
                return

            CHUNK = 1024
            while not stop.is_set():
                idx = 0
                total = len(region)
                while idx < total and not stop.is_set():
                    end_idx = min(idx + CHUNK, total)
                    chunk   = region[idx:end_idx]
                    stream.write(chunk.astype(np.float32).tobytes())
                    # update position ratio
                    self._pb_pos = start_r + (idx / total) * span
                    idx = end_idx
                if not loop() or stop.is_set():
                    break
                # loop: restart from beginning of region
            stream.stop_stream()
            stream.close()
            # reset UI from GUI thread
            QMetaObject.invokeMethod(self, "_on_playback_finished",
                                     Qt.ConnectionType.QueuedConnection)

        self._pb_thread = threading.Thread(target=run, daemon=True)
        self._pb_thread.start()
        self._ph_timer.start()

    def _stop_playback(self):
        if self._pb_stop_evt:
            self._pb_stop_evt.set()
        if self._pb_thread and self._pb_thread.is_alive():
            self._pb_thread.join(timeout=0.5)
        self._pb_thread   = None
        self._pb_stop_evt = None
        self._pb_active   = False
        self._ph_timer.stop()
        self.wave.playhead = -1.0
        self.wave.update()
        if hasattr(self, "play_btn"):
            self.play_btn.setText("▶  Play")

    @pyqtSlot()
    def _on_playback_finished(self):
        self._stop_playback()

    def _tick_playhead(self):
        """Called by QTimer every ~33ms to update the playhead on the waveform."""
        if self._pb_active:
            self.wave.playhead = self._pb_pos
            self.wave.update()
            # update position label
            secs = self._pb_pos * self._duration
            m = int(secs // 60); s = secs % 60
            self.pos_label.setText(f"{m}:{s:05.2f}")

    def _do_trim(self):
        if self._audio_data is None:
            QMessageBox.information(self, "No file", "Please load an audio file first.")
            return
        s  = int(self._start * len(self._audio_data))
        e  = int(self._end   * len(self._audio_data))
        tr = self._audio_data[s:e]
        src = Path(self._filepath)
        out = src.parent / (src.stem + "_trimmed" + src.suffix)
        ctr = 1
        while out.exists():
            out = src.parent / (src.stem + f"_trimmed_{ctr}" + src.suffix)
            ctr += 1
        try:
            sf.write(str(out), tr, self._samplerate)
            self.result_label.setText(f"Saved → {out.name}")
            QTimer.singleShot(5000, lambda: self.result_label.setText(""))
        except Exception as e:
            QMessageBox.critical(self, "Save error", str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wave")
        self.setWindowIcon(QIcon("ocean.png"))
        self.setMinimumSize(380, 460)
        self.resize(600, 720)

        central = QWidget(); central.setObjectName("root")
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tabs = QTabWidget()
        tabs.addTab(RecordTab(), "  Record  ")
        tabs.addTab(TrimTab(),   "  Trim    ")
        layout.addWidget(tabs)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("WAVE")
    app.setStyleSheet(STYLE)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()