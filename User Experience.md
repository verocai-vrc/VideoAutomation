# Chain of Events when user opens the app. (Future Ideal Version)
This section of the file describes the app (when done) usage in absctration to elicit functionalities and requirements set as goals.

## Interface Opens (fullscreen) (Future Ideal Version)
0 - GUI Displays main dashboard (Modern, dark-mode, multi-panel fullscreen layout)
    A.1- AI & Scripting Options
        A.1.1- Scripting AI Model Selection (Dropdown: Ollama, OpenAI, Claude, DeepSeek)
            A.1.1.1- Saveable/Loadable Custom Prompt Templates
            A.1.1.2- Script AI prompt Box (Persistent base prompt + editable user prompt)
        A.1.2- AI Personality & Voice Options
            A.1.2.1- Script Tone Selection (Dropdown)
            A.1.2.2- Video Theme Presets (e.g., Top 5, Fun Fact, Deep Dive, Storytime) 
                A.1.2.2.1- Theme Preset Configuration (Auto-adjusts prompt, tone, and pacing)
            A.1.2.3- AI Voice Selection (Dropdown: ElevenLabs, OpenAI TTS, EdgeTTS)
            A.1.2.4- Voice Emotion & Pacing Control Sliders
    B.1- Visuals & Media Options
        B.1.1- Asset Sourcing
            B.1.1.1- Load Local Media (Drag-and-drop zone with gallery preview)
            B.1.1.2- Web/AI Media Generator (DuckDuckGo, Google Imagen, Midjourney API)
            B.1.1.3- Auto B-Roll Integration (Pexels/Pixabay stock video fetching based on script)
        B.1.2- Media Editing & Effects
            B.1.2.1- Advanced Visual Effects (Ken Burns, Parallax, Glitch, VHS)
            B.1.2.2- Transition Style & Transition Duration Slider
            B.1.2.3- Custom Watermark / Channel Logo Overlay Uploader
    C.1- Audio & Subtitle Engine
        C.1.1- Audio Mixing
            C.1.1.1- Narration usage Toggle & Volume Slider
            C.1.1.2- Background song usage Toggle & Volume Slider
        C.1.2- Subtitle Customization
            C.1.2.1- Subtitle Style Presets (e.g., "Hormozi Bold", "Minimalist Tech", "TikTok Standard")
            C.1.2.2- Word-by-Word Animation Toggles (Pop-in, Color Highlighting, Spring)
            C.1.2.3- Auto-Emoji Insertion Toggle (AI adds context-aware emojis to subs)
            C.1.2.4- Font, Size, Text Color, and Stroke Thickness adjusters
            C.1.2.5- Interactive Preview Canvas (Drag to position subtitles directly on screen)
    D.1- Output, Rendering & Project Management
        D.1.1- Video Format Options
            D.1.1.1- Aspect Ratio Selector (9:16 Shorts, 16:9 YouTube, 1:1 Instagram)
            D.1.1.2- Resolution (1080p, 4K) & Rendering Quality Presets (Fast, Studio)
        D.1.2- Project Handling
            D.1.2.1- Save / Load Project buttons (.json state saving)
            D.1.2.2- History / Recent Projects Dashboard
    E.1- Main Action Bar & Integrated Timeline
        E.1.1- Expandable Integrated Timeline panel (Persistent at the bottom of the screen)
        E.1.2- Pre-Generate Assets Button (Creates script/audio/images for review before rendering)
        E.1.3- Final Render Button
        E.1.4- Detailed HUD: Visual Progress bar, ETA, and collapsible debug log


## Program Usage workflow / pipeline (Future Ideal Version)
1. User opens the application and lands on a fullscreen dashboard.
2. User either loads a previous project state or begins a new video.
3. User selects a "Video Theme Preset", which automatically sets up the AI Tone, Voice, Subtitle Style, and Output resolution.
4. User refines the script prompt or drops an existing video file to initiate Transcribe Mode.
5. User clicks "Pre-Generate Assets".
    5.1. The AI generates the script, text-to-speech audio, and transcription simultaneously.
    5.2. Background fetchers scrape web images, stock B-roll, or generate AI images based on the script's keywords.
6. A unified "Review & Edit Dashboard" opens.
    6.1. User can read and manually edit the generated text script.
    6.2. User can approve/deny/regenerate images and videos in a gallery view.
7. Approved media automatically populates the Integrated Timeline at the bottom of the screen.
    7.1. User can drag clips, adjust exact timing, swap out images, and preview audio in real-time.
8. User clicks "Final Render".
    8.1. System utilizes GPU acceleration (if available) and multi-threading to composite the video.
    8.2. Subtitles with animations and emojis are rendered directly onto the video.
9. Upon completion, a playback window appears alongside output options.
10. (Optional) System automatically uploads the final .mp4 to the selected social media platforms using stored API keys.

# Chain of Events when user opens the app. (Currently implemented Version)
This section of the file describes the apps (current version) usage in absctration to elicit functionalities and requirements already implemented and working perfectly

## Interface Opens (Window mode) (Currently implemented Version)
0 - GUI displays 3 main vertical columns and a bottom action bar
    A.1- AI & Scripting (Column 1)
        A.1.1- Ollama Model Selection (Dropdown)
        A.1.2- Transcribe Uploaded Video Mode (Toggle)
        A.1.3- Script Tone Selection (Dropdown)
        A.1.4- Opening Hook Selection (Dropdown)
        A.1.5- AI Prompt Box (Editable text area for script generation)
    B.1- Visuals & Media (Column 2)
        B.1.1- Local Media Selection
            B.1.1.1- Browse Button for Images/Videos
            B.1.1.2- Selected files count and preview thumbnails
        B.1.2- Media Usage Toggles
            B.1.2.1- Use Videos (Toggle)
            B.1.2.2- Use Images (Toggle)
        B.1.3- Image Sourcing
            B.1.3.1- Image Source Selection (Dropdown: DuckDuckGo or AI Generator)
            B.1.3.2- Test API Button (For AI Generator)
            B.1.3.3- Number of Images to generate/fetch (Spinbox)
            B.1.3.4- Image Search Terms / Prompts (Editable text area)
        B.1.4- Effects
            B.1.4.1- Transition Effect (Dropdown)
            B.1.4.2- Visual Effect (Dropdown: Zoom, Pan, etc.)
    C.1- Audio & Output (Column 3)
        C.1.1- Output Directory Selection (Text box & Browse button)
        C.1.2- Narration Audio Options
            C.1.2.1- Enable Narration Audio (Toggle)
        C.1.3- Background Music Options
            C.1.3.1- Background Music File Selection (Browse button)
            C.1.3.2- Background Volume (%) (Slider)
            C.1.3.3- Loop Background Music (Toggle)
        C.1.4- Subtitles Styling Options
            C.1.4.1- Font Selection & Custom Font Browse
            C.1.4.2- Colors (Text and Outline)
            C.1.4.3- Outline Width and Text Size (Spinboxes)
            C.1.4.4- Subtitle Y-Position (Spinbox)
        C.1.5- Visual Preview
            C.1.5.1- Cellphone-shaped Mock Screen (Real-time subtitle style/position preview)
    D.1- Action Bar & Logging (Bottom Frame)
        D.1.1- Generate Video Button
        D.1.2- Open Last Video Button (Activates on completion)
        D.1.3- Progress Tracking (Percentage text, spinner, and progress bar)
        D.1.4- Progress Logs (Live terminal output mirror)

## Program Usage workflow / pipeline (Currently implemented Version)
1. User fills out configurations across the AI, Visuals, and Audio sections.
2. User clicks "GENERATE VIDEO".
3. AI Script & Audio Generation Phase:
    3.1. (If Transcribe Mode is OFF) System queries AI to generate a script based on the prompt, tone, and hook.
    3.2. A Script Review window opens: User reads, manually edits, and approves the script.
    3.3. TTS converts the approved script to audio.
    3.4. Whisper transcribes the TTS audio to generate precise `.srt` timestamps.
    3.5. (If Transcribe Mode is ON) System skips script generation and directly transcribes a user-provided video to get `.srt` timestamps.
4. Media Acquisition Phase:
    4.1. System processes any local images or videos provided by the user.
    4.2. If the quota of images isn't met, the system scrapes DuckDuckGo or prompts Google Imagen AI for the remaining images using the provided search terms.
5. Media Review Phase:
    5.1. An Image Review window opens, displaying all gathered visual assets.
    5.2. User can approve the images, cancel, or type new search terms and hit "Retry" to fetch new ones.
6. Timeline Synchronization & Editing Phase:
    6.1. The system's core logic analyzes script context and keywords to automatically map image timings to spoken words.
    6.2. A Timeline Editor window opens, showing the audio tracks and media overlays.
    6.3. User can preview audio, drag-and-drop clips to adjust start times, and drag edges to change durations.
    6.4. User clicks "Approve & Render Video".
7. Rendering Phase:
    7.1. MoviePy composites the base video/color background, overlay images/videos (with transitions and visual effects), background music (with volume adjustments), and TTS audio.
    7.2. Pillow/NumPy generates subtitles frame-by-frame on top of the composition.
    7.3. FFmpeg encodes the final video and saves it to the output directory.
8. Completion: User clicks "OPEN LAST VIDEO" to view the result.