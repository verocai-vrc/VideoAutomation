# 🤖 AI Social Media Video Generator (Self-Hosted)

This project is an intelligent automation ecosystem for creating short-form video content (Reels, TikTok, Shorts). The system orchestrates local AI models and free APIs to generate scripts, professional narration, source visuals (local media and web scraping), and synchronize subtitles, resulting in a final video ready for publishing.

---

## 🚀 Overview
The program acts as an end-to-end production pipeline:
1.  **Brainstorming & Scripting:** Ollama (e.g., Llama 3) generates an educational script based on your prompt.
2.  **Voice Generation:** Edge-TTS converts the text into high-quality audio and generates precise word-level timestamps.
3.  **Visual Sourcing:** The system seamlessly merges your local videos/images with images automatically scraped from the web (via DuckDuckGo) to fill the timeline.
4.  **Video Editing:** MoviePy pieces all the elements together, overlays background music, and cleanly renders the synchronized subtitles natively via Pillow.

---

## 🛠️ Tech Stack
*   **Language:** Python 3.10+
*   **Text AI:** [Ollama](https://ollama.com/)
*   **Voice & Subtitles:** Edge-TTS (Microsoft) & Pysubs2
*   **Video & Image Processing:** MoviePy, Pillow (PIL), NumPy
*   **Asset Searching:** DuckDuckGo Search API
*   **GUI:** Tkinter

---

## 📋 Features

### Currently Implemented:
- [x] **Automated Script Generation & Review:** Generate highly detailed scripts dynamically to fit +60s timelines, with the ability to pause, review, and manually edit the script before generation.
- [x] **Professional Narration:** High-fidelity English TTS using neural voices (Toggleable for when you just want to subtitle a local video).
- [x] **Dynamic Media Handling:** Import local videos/images and view live thumbnail previews directly in the modern UI.
- [x] **Smart Internet Search & Fallback:** Automatically fetches images via DuckDuckGo, with a seamless fallback to Wikimedia Commons if rate-limited. Includes a UI window to review, approve, or retry image searches.
- [x] **Video Overlays & B-Roll:** Intelligently overlays images on top of base videos, automatically timed to when their descriptive keywords are spoken (using Whisper AI).
- [x] **Cinematic Effects & Transitions:** Easily apply visual effects (Zoom-in, Zoom-out, Pan) and transitions (Fade In/Out, Cut) directly from the GUI.
- [x] **Advanced Subtitle Engine:** Word-by-word synced subtitles drawn completely in-memory using Pillow. Supports custom fonts, colors, sizing, and Y-positioning, complete with a real-time cellphone-shaped preview screen.
- [x] **Background Audio Engine:** Add background music with adjustable volume that automatically loops to fit the video length.
- [x] **Vertical Composition:** Videos and images are dynamically resized to standard 9:16 vertical format (1080x1920) with smart layout boundaries so overlays never cover subtitles.
- [x] **Highly Resilient Architecture:** Includes HTTP auto-retries, memory-safe image validation, fallback mechanisms, and robust timestamped file exports to prevent overwriting.
- [x] **Modern GUI:** Clean, horizontal UI layout with real-time progress spinners and a one-click shortcut to immediately open the generated media.

---

## ⚙️ Installation & Usage

1. **Clone & Prepare the Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install requests moviepy edge-tts pysubs2 duckduckgo_search pillow numpy
   ```

2. **External Dependencies:**
   - Have **Ollama** running locally (e.g., `ollama run llama3`).
   - Place an `ffmpeg.exe` binary directly in the root folder of this project (this bypasses complex Windows PATH configurations).

3. **Execution:**
   ```bash
   python VideoAutomation.py
   ```

---

## 🎯 Development Roadmap
- [ ] Advanced timeline editor for manual image/overlay timing adjustments:
  - [ ] Create a GUI timeline component to visualize tracks.
  - [ ] Implement drag-and-drop for start times and durations.
  - [ ] Add preview playback for synchronization checking.