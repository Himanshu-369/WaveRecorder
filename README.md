# Wave-Recorder
Handy tool to record system audio and Trim it too. Useful when doing voice cloning 🪢 and don't know from where to download audio samples. Just play a youtube video and record system audio that's it.


# 🌊 WAVEFORM STUDIO — Minimal System Audio Recorder & Trimmer

**WAVEFORM STUDIO** is a sleek, minimalist desktop application built with Python and PyQt6. It allows you to record system audio (what you hear) or microphone input, visualize the waveform in real-time, and perform basic trimming operations—all within a modern, dark-themed interface.

Designed for Windows using `pyaudiowpatch` for WASAPI loopback support, it serves as a lightweight tool for quickly capturing audio snippets without the bloat of professional DAWs.

## ✨ Features

- **System Audio Capture:** Record "What You Hear" (Loopback) directly from your speakers on Windows.
- **Microphone Support:** Switch easily between loopback devices and standard input devices.
- **Real-time Waveform:** Live visual feedback while recording.
- **Configurable Settings:**
  - **Custom Save Directory:** Choose where your recordings are saved.
  - **File Naming Syntax:** Customize filenames with Prefix, Date/Time formatting (using `strftime`), and Suffix.
- **Audio Trimming:** 
  - Load `.wav`, `.flac`, `.ogg`, and `.mp3` files.
  - Visual selection of start/end points.
  - Drag-and-drop region selection.
- **Playback Controls:** Preview selections with play/pause and loop functionality.
- **Audio Processing:** 
  - Auto-normalization to -1 dBFS.
  - Manual gain control.
- **Modern UI:** Clean, dark aesthetic with custom styled widgets and smooth animations.

## 📸 Screenshots
|Record Section|Trim Section|
|:---:|:---:|
|<img width="100%" height="100%" alt="1" src="https://github.com/user-attachments/assets/ba365d2a-c77b-48b6-be8d-3722faf83087" />|<img width="100%" height="100%" alt="2" src="https://github.com/user-attachments/assets/eedc0a14-7878-45c8-99d8-003d9c1bce81" />|

|Settings for Filename Syntax|
|:---:|
|<img width="100%" height="100%" alt="3" src="https://github.com/user-attachments/assets/51563a5a-d4cf-4da6-bcd6-dd87bf8787ce" />|

|Trim Section (Active)|
|:---:|
|<img width="100%" height="100%" alt="4" src="https://github.com/user-attachments/assets/1c1b3905-32ee-41ab-a734-030fd3da92d8" />|


---

## 🛠️ Requirements

- Python 3.10+
- Windows (recommended for Loopback functionality) or any OS with PyAudio support.

## 🚀 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/wave-recorder.git
   cd wave-recorder
   ```

2. **Install dependencies:**
   The application requires `PyQt6`, `pyaudiowpatch`, `numpy`, and `soundfile`.
   ```bash
   pip install PyQt6 pyaudiowpatch numpy soundfile
   ```
   > **Note:** `pyaudiowpatch` is a drop-in replacement for PyAudio that enables WASAPI Loopback (recording system audio) on Windows. If you are on Linux or macOS, it will fall back to standard `pyaudio`.

3. **Run the application:**
   ```bash
   python wave_2.py
   ```
   *(Assuming you saved the script as `wave_2.py`)*

## 📖 Usage

### Configuration (Settings)
Before recording, click the **⚙️ Settings** button in the top-right corner of the Record tab to configure:
- **Save Directory:** Select the default folder where recordings are stored.
- **File Naming:** Set a prefix (e.g., "recording"), date format (e.g., `%Y-%m-%d`), and suffix.
- A live preview of the filename is shown at the bottom of the dialog.

### Recording
1. Select your **Capture Device** from the dropdown.
   - 🎙 Indicates microphone/input devices.
   - 🔊 Indicates loopback (speaker) devices.
2. Toggle **Normalize** for automatic leveling or adjust **Manual Gain**.
3. Press **⏺ Record** to start capturing. The waveform will update in real-time.
4. Press **⏹ Stop** to save the file. The file will be named according to your **Settings** configuration.

### Trimming
1. Switch to the **Trim** tab.
2. **Open** a file or **Drag & Drop** an audio file onto the window.
3. Drag the purple handles to select your start and end points.
4. Use **▶ Play** to preview the selection.
5. Click **✂ Trim and Save** to export the selection as a new file.

### Future Changes 
- [ ] Renaming functionality (to rename file within gui)
- [x] Option to change file name saving pattern (eg. filename_1.wav, filename_2.wav, ...)
- [ ] Support for saving files in various extensions (.wav, mp3, .wma, etc.)

---

## 📄 License

This project is open source. Feel free to modify and distribute as needed.
