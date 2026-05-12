# To-do list
## Issues (Diagnose Cause, Plan Solution, Segment into Steps to take)
g- when thinking about image order, the file name for each image has keywords relating to the content they represent. The image order must match the video narration context.
h- The live preview must start working after the user clicks generate video (currently it doesnt display anything). So i can hear the narration and check subtitles before the final rendering. How can we implement that?

### AI & Scripting Enhancements
- [ ] Implement Saveable/Loadable Custom Prompt Templates
- [ ] Add Video Theme Presets (e.g., Top 5, Fun Fact) that auto-adjust prompt, tone, and pacing
- [ ] Integrate other AI Voice APIs

### Media & Visuals
- [ ] Implement Advanced Visual Effects (Ken Burns, Parallax, Glitch, VHS)
- [ ] Add a Transition Duration Slider

### Audio & Subtitles
- [ ] Add Subtitle Style Presets (e.g., "Hormozi Bold", "Minimalist Tech", "TikTok Standard")
- [ ] Develop Word-by-Word Subtitle Animations (Pop-in, Color Highlighting, Spring) (and its toggle button)
- [ ] Implement Auto-Emoji Insertion (AI adds context-aware emojis to subtitles)
- [ ] Upgrade Subtitle Preview to an Interactive Canvas (drag-and-drop to position subtitles)

### UI & Project Management
- [x] Transform app into a persistent "Studio" workspace (opens maximized/full window size by default)
- [x] Add a fullscreen view option toggle in the main UI
- [x] Implement a live project preview screen (9:16 aspect ratio) directly in the main window showing the currently built project
- [x] Make the left column sections (including Subtitle Style) toggleable/collapsible to declutter the workspace
- [ ] Allow regenerating/editing the script and re-generating narration/subtitles directly from the preview workspace if unsatisfied
- [ ] Implement Project State Handling (Save/Load GUI settings as a `.json` file)
- [ ] Create a History / Recent Projects Dashboard
- [x] Transition the Timeline Editor to a persistent Expandable Integrated Timeline panel at the bottom of the main UI
- [x] Add a "Pre-Generate Assets" button to separate the asset generation/review phase from the final rendering phase

### Output, Rendering & Publishing
- [ ] Investigate/Implement GPU acceleration for MoviePy rendering

### Functionalities
- [x] Advanced timeline editor for manual image/overlay timing adjustments
- [x] Create a GUI timeline component to visualize video duration, audio, and media tracks.
- [x] Implement drag-and-drop to manually adjust start times and durations of images/overlays.
- [x] Modify the video generation core to accept custom timestamps from the timeline editor.
- [x] Add a preview playback feature to check synchronization before rendering.
- [x] Alternate to DuckDuckGo API for image search when request denyed
- [x] After images are loaded, the user must be able to aprove or deny them and request another search if wanted
- [x] When loading in a video, add an Option to add images over the video to ilustrate the topics talked
- [x] Embeded images must appear when mentioned in the video and disappear afterwards
- [x] Make sure embeded images dont cover the subtitles
- [x] Add Transition effects (fade in, fade out, cut) + Controll for this on the GUI
- [x] Add an option `< Subtitle this video >` to exclusively transcribe and subtitle an inputted video while skipping other visual generation.
- [x] Option to Add visual Effects (Zoom-In, Zoom-Out, Pan) to medias
- [x] Implement hook generators to maximize engagement (via Opening Hook AI directive)
- [x] AI Image Generation (mages to generate.
    - [x] Prompt each image separately via the UI.
    - [x] Enforce 9:16 aspect ratio for generated images.
    - [x] Save generated images locally to the assets folder.
    - [x] Implement rate limit monitoring and cost control via a daily usage tracker.
    - [x] Use a configurable `DAILY_LIMIT` to prevent over-usage.
- [x] Add cellphone shaped preview screen
    - [x] to preview the changes on subtitle style and placement
    - [x] Make subtitle boundary editable on the subtitle section

### GUI
- [x] When files are loaded, show a tiny preview in the file sect area (mimicking win file explorer)
- [x] better GUI
    - [x] Toggle boxes organized by list vertically
    - [x] Use Images, Number of images and image search prompt on its own section
    - [x] Prettier volume slider
    - [x] Prompt box section for script generator
    - [x] New app name on window: VideoMaekar
    - [x] % Number by the side of progress bar + Rotating bar to indicate activeness ( |, /, --, \ )
    - [x] Horizontal rectangle window (instead of vertical)
    - [x] More stilized GUI, organized in sections for more intuitive design

### Bug fixes
- [x] Subtitles get cropped by invisible bars when close to the video border: Lets add boundaries to make line breaks 
- [x] when making a video with images, using the AI narration, subtitles arent visible
- [x] the narration is including the time stamps and ruining user experience
- [x] timeline editor window is blank, Cant edit the timeline or even tell the program to keep going without editing. Program gets softlocked waiting for response that cant be given
- [x] Subtitles are STILL not visible when generating videos with images
- [x] volume bar doesnt change background audio volume
- [x] program must analize script to customize every selected image duration and order relating to ( and in sync with) the narration
- [x] The fix you made for image sync didnt work. now most of the video is a black screen and images dont appear when their topic is brought up.
- [x] Every image uploaded MUST be in the video.
- [x] the program needs to infere image order.
- [x] image doesnt have to vanish right after its word mention passess, rather it only goes out when the next image is called, to prevent image-less black screens
- [x] in testing the output: the video only showed the first image, and by alphabetical order rather than contextual order.
- [x] Separate video generation from subtitle rendering to rely on manual Whisper pass for perfect timestamps
