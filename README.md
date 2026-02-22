# MazeRecorder
Handy tool to record system audio and Trim it too. Useful when doing voice cloning 🪢 and don't know from where to download audio samples. Just play a youtube video and record system audio that's it.


# 🌊 WAVE — Minimal System Audio Recorder & Trimmer

**WAVE** is a sleek, minimalist desktop application built with Python and PyQt6. It allows you to record system audio (what you hear) or microphone input, visualize the waveform in real-time, and perform basic trimming operations—all within a modern, dark-themed interface.

Designed for Windows using `pyaudiowpatch` for WASAPI loopback support, it serves as a lightweight tool for quickly capturing audio snippets without the bloat of professional DAWs.

## ✨ Features

- **System Audio Capture:** Record "What You Hear" (Loopback) directly from your speakers on Windows.
- **Microphone Support:** Switch easily between loopback devices and standard input devices.
- **Real-time Waveform:** Live visual feedback while recording.
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
|Record Section|Trim Section|Trim Section (Active)|
|:---:|:---:|:---:|
|<img width="100%" height="100%" alt="1" src="https://github.com/user-attachments/assets/8804d1fa-80be-4d58-829b-a9febd296fee" />|<img width="100%" height="100%" alt="2" src="https://github.com/user-attachments/assets/46342b93-81e4-4bc5-ae42-c44c0f33a05d" />|<img width="100%" height="100%" alt="3" src="https://github.com/user-attachments/assets/e567c2c2-5471-43bb-8c74-c444c0cc7bc6" />|



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
   python wave.py
   ```
   *(Assuming you saved the script as `wave.py`)*

## 📖 Usage

### Recording
1. Select your **Capture Device** from the dropdown.
   - 🎙 Indicates microphone/input devices.
   - 🔊 Indicates loopback (speaker) devices.
2. Toggle **Normalize** for automatic leveling or adjust **Manual Gain**.
3. Press **⏺ Record** to start capturing. The waveform will update in real-time.
4. Press **⏹ Stop** to save the file. Recordings are saved as `.wav` in the current working directory.

### Trimming
1. Switch to the **Trim** tab.
2. **Open** a file or **Drag & Drop** an audio file onto the window.
3. Drag the purple handles to select your start and end points.
4. Use **▶ Play** to preview the selection.
5. Click **✂ Trim and Save** to export the selection as a new file.

### Future Changes 
- [ ] Renaming functionality (to rename a file in gui)
- [ ] Option to change file name saving pattern (eg. filename_1.wav, filename_2.wav, ...)
- [ ] Support for saving files in various extensions (.wav, mp3, .wma, etc.)

---

## 📄 License

This project is open source. Feel free to modify and distribute as needed.
```
