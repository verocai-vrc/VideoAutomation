# To-do list

## Pending Tasks

---

## Completed

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
- [x] Option to Add visual Effects (Zoom-In, Zoom-Out, Pan) to medias
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
