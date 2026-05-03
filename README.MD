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
- [x] **Automated Script Generation:** Generate highly detailed scripts dynamically to fit +60s timelines.
- [x] **Professional Narration:** High-fidelity English TTS using neural voices (Toggleable for when you just want to subtitle a local video).
- [x] **Dynamic Media Handling:** Support for importing local `.mp4`, `.mov`, `.png`, `.jpg` files alongside automated web images.
- [x] **Smart Internet Search:** Automatically calculates how many images you need and fetches them via DuckDuckGo to hit your exact requested media count.
- [x] **Native Synchronized Subtitles:** Word-by-word synced subtitles drawn completely in-memory using Pillow (no ImageMagick required!).
- [x] **Background Audio Engine:** Add background music with adjustable volume that automatically loops to fit the video length.
- [x] **Vertical Composition:** Videos and images are dynamically resized to standard 9:16 vertical format (1080x1920).
- [x] **Highly Resilient Architecture:** Includes HTTP auto-retries for rate limits, memory-safe image validation to avoid render crashes, and fallback mechanisms for broken API metadata.

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
- [ ] Implement specific first/last image selection mechanics.
- [ ] Overhaul GUI (corner layouts, dedicated slider sections, modern aesthetic window name).
- [ ] Integrate alternative Image APIs (e.g., Pexels, Unsplash).
- [ ] Add visual effects (smooth transitions and zoom-in/pan for static images).