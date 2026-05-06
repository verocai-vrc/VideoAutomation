import tkinter as tk
import time

class TimelineEditor(tk.Frame):
    def __init__(self, parent, duration=60, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.duration = duration
        self.pixels_per_second = 50
        self.track_height = 60
        self.ruler_height = 30
        self.canvas_width = self.duration * self.pixels_per_second
        self.canvas_height = self.ruler_height + (self.track_height * 3) # 3 default tracks
        
        self.control_frame = tk.Frame(self, bg="#1e1e1e")
        self.control_frame.pack(side=tk.TOP, fill=tk.X)
        self.play_btn = tk.Button(self.control_frame, text="▶ Play", command=self.toggle_playback, bg="#4CAF50", fg="white", font=("Arial", 9, "bold"), width=8)
        self.play_btn.pack(side=tk.LEFT, padx=5, pady=5)
        self.time_lbl = tk.Label(self.control_frame, text=f"0.00s / {self.duration:.2f}s", bg="#1e1e1e", fg="#aaaaaa", font=("Arial", 9))
        self.time_lbl.pack(side=tk.LEFT, padx=5)
        
        # Setup Canvas with horizontal scrollbar
        self.canvas = tk.Canvas(self, width=800, height=self.canvas_height, bg="#1e1e1e", highlightthickness=0, scrollregion=(0, 0, self.canvas_width, self.canvas_height))
        self.scrollbar = tk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self._drag_data = {"x": 0, "y": 0, "item": None, "group_tag": None}
        self.is_playing = False
        self._last_time = 0.0
        self.selected_group_tag = None
        
        self.draw_ruler()
        self.draw_tracks(3)
        
        self.playhead_time = 0.0
        self.playhead_id = self.canvas.create_line(0, 0, 0, self.canvas_height, fill="#ff3333", width=2, tags="playhead")
        
        self.canvas.tag_bind("ruler", "<ButtonPress-1>", self.on_ruler_click)
        self.canvas.tag_bind("ruler", "<B1-Motion>", self.on_ruler_drag)
        
        # Bind drag and drop events to anything tagged as "draggable"
        self.canvas.tag_bind("draggable", "<ButtonPress-1>", self.on_drag_start)
        self.canvas.tag_bind("draggable", "<B1-Motion>", self.on_drag_motion)
        self.canvas.tag_bind("draggable", "<ButtonRelease-1>", self.on_drag_release)
        self.canvas.tag_bind("draggable", "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
        self.canvas.tag_bind("draggable", "<Leave>", lambda e: self.canvas.config(cursor=""))
        
        self.canvas.tag_bind("draggable", "<Button-3>", self.on_right_click_delete)
        self.canvas.bind("<Delete>", self.on_delete_key)
        
        self.canvas.tag_bind("resize_left", "<ButtonPress-1>", self.on_drag_start)
        self.canvas.tag_bind("resize_left", "<B1-Motion>", self.on_resize_left_motion)
        self.canvas.tag_bind("resize_left", "<Enter>", lambda e: self.canvas.config(cursor="sb_h_double_arrow"))
        self.canvas.tag_bind("resize_left", "<Leave>", lambda e: self.canvas.config(cursor=""))
        
        self.canvas.tag_bind("resize_right", "<ButtonPress-1>", self.on_drag_start)
        self.canvas.tag_bind("resize_right", "<B1-Motion>", self.on_resize_right_motion)
        self.canvas.tag_bind("resize_right", "<Enter>", lambda e: self.canvas.config(cursor="sb_h_double_arrow"))
        self.canvas.tag_bind("resize_right", "<Leave>", lambda e: self.canvas.config(cursor=""))
        
    def draw_ruler(self):
        self.canvas.create_rectangle(0, 0, self.canvas_width, self.ruler_height, fill="#2b2b2b", outline="", tags="ruler")
        for sec in range(int(self.duration) + 1):
            x = sec * self.pixels_per_second
            # Major tick every 5 seconds, minor every 1 second
            if sec % 5 == 0:
                self.canvas.create_line(x, self.ruler_height - 15, x, self.ruler_height, fill="#ffffff", tags="ruler")
                self.canvas.create_text(x + 2, self.ruler_height - 22, text=f"{sec}s", fill="#aaaaaa", anchor="w", font=("Arial", 8), tags="ruler")
            else:
                self.canvas.create_line(x, self.ruler_height - 5, x, self.ruler_height, fill="#777777", tags="ruler")
                
    def draw_tracks(self, num_tracks):
        colors = ["#252525", "#2a2a2a"]
        for i in range(num_tracks):
            y1 = self.ruler_height + (i * self.track_height)
            y2 = y1 + self.track_height
            bg_color = colors[i % len(colors)]
            self.canvas.create_rectangle(0, y1, self.canvas_width, y2, fill=bg_color, outline="#333333")
            
            # Track labels
            labels = ["Audio / TTS", "Base Video", "Overlays"]
            label = labels[i] if i < len(labels) else f"Track {i+1}"
            self.canvas.create_text(10, y1 + 10, text=label, fill="#888888", anchor="w", font=("Arial", 9, "bold"))
            
    def add_clip(self, track_index, start_time, duration, color, text, clip_id):
        x1 = start_time * self.pixels_per_second
        x2 = (start_time + duration) * self.pixels_per_second
        y1 = self.ruler_height + (track_index * self.track_height) + 20
        y2 = y1 + self.track_height - 10
        
        group_tag = f"clip_group_{clip_id}"
        
        # The visual block
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#ffffff", tags=("draggable", "clip_rect", group_tag))
        
        # Resize handles
        handle_w = 6
        self.canvas.create_rectangle(x1, y1, x1 + handle_w, y2, fill="#111111", outline="", tags=("resize_left", group_tag, "handle_left"))
        self.canvas.create_rectangle(x2 - handle_w, y1, x2, y2, fill="#111111", outline="", tags=("resize_right", group_tag, "handle_right"))
        
        # The inner text
        self.canvas.create_text(x1 + handle_w + 5, y1 + (self.track_height-30)/2, text=text, fill="#ffffff", anchor="w", font=("Arial", 9), tags=("draggable", "clip_text", group_tag))
        
    def on_drag_start(self, event):
        item = self.canvas.find_withtag("current")[0]
        tags = self.canvas.gettags(item)
        
        group_tag = next((t for t in tags if t.startswith("clip_group_")), None)
        if group_tag:
            self.selected_group_tag = group_tag
            self._drag_data["item"] = item
            self._drag_data["group_tag"] = group_tag
            self._drag_data["x"] = self.canvas.canvasx(event.x)
            self._drag_data["y"] = self.canvas.canvasy(event.y)
            
            # Bring the dragged clip to the visual front
            for i in self.canvas.find_withtag(group_tag):
                self.canvas.tag_raise(i)

    def on_drag_motion(self, event):
        if not self._drag_data["group_tag"]: return
            
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        delta_x = canvas_x - self._drag_data["x"]
        delta_y = canvas_y - self._drag_data["y"]
        
        # Boundary constraint: don't let it go before 0 seconds
        rect_item = next((item for item in self.canvas.find_withtag(self._drag_data["group_tag"]) if "clip_rect" in self.canvas.gettags(item)), None)
                
        if rect_item:
            coords = self.canvas.coords(rect_item)
            if coords[0] + delta_x < 0:
                delta_x = -coords[0] # Force X position exactly to 0
                
        self.canvas.move(self._drag_data["group_tag"], delta_x, delta_y)
        self._drag_data["x"] += delta_x
        self._drag_data["y"] += delta_y
        self.canvas.tag_raise(self.playhead_id)
        
    def on_drag_release(self, event):
        if not self._drag_data["group_tag"]: return
        
        group_tag = self._drag_data["group_tag"]
        rect_item = next((item for item in self.canvas.find_withtag(group_tag) if "clip_rect" in self.canvas.gettags(item)), None)
        
        if rect_item:
            coords = self.canvas.coords(rect_item)
            center_y = (coords[1] + coords[3]) / 2
            
            # Find closest track index (0, 1, or 2)
            track_index = int((center_y - self.ruler_height) / self.track_height)
            track_index = max(0, min(track_index, 2))
            
            # Snap clip to the nearest valid track
            target_y1 = self.ruler_height + (track_index * self.track_height) + 20
            delta_y = target_y1 - coords[1]
            
            if delta_y != 0:
                self.canvas.move(group_tag, 0, delta_y)
                
        self._drag_data["group_tag"] = None

    def on_right_click_delete(self, event):
        item = self.canvas.find_withtag("current")[0]
        tags = self.canvas.gettags(item)
        group_tag = next((t for t in tags if t.startswith("clip_group_")), None)
        if group_tag:
            if self.selected_group_tag == group_tag:
                self.selected_group_tag = None
            self.canvas.delete(group_tag)

    def on_delete_key(self, event):
        if self.selected_group_tag:
            self.canvas.delete(self.selected_group_tag)
            self.selected_group_tag = None

    def on_resize_left_motion(self, event):
        if not self._drag_data["group_tag"]: return
        canvas_x = self.canvas.canvasx(event.x)
        
        group_tag = self._drag_data["group_tag"]
        rect_item = next((item for item in self.canvas.find_withtag(group_tag) if "clip_rect" in self.canvas.gettags(item)), None)
        left_handle = next((item for item in self.canvas.find_withtag(group_tag) if "handle_left" in self.canvas.gettags(item)), None)
        text_item = next((item for item in self.canvas.find_withtag(group_tag) if "clip_text" in self.canvas.gettags(item)), None)
        
        if rect_item and left_handle:
            coords = self.canvas.coords(rect_item)
            min_width = 15
            new_x1 = min(max(0, canvas_x), coords[2] - min_width)
            
            self.canvas.coords(rect_item, new_x1, coords[1], coords[2], coords[3])
            handle_w = 6
            self.canvas.coords(left_handle, new_x1, coords[1], new_x1 + handle_w, coords[3])
            if text_item:
                text_coords = self.canvas.coords(text_item)
                self.canvas.coords(text_item, new_x1 + handle_w + 5, text_coords[1])
        self.canvas.tag_raise(self.playhead_id)
                
    def on_resize_right_motion(self, event):
        if not self._drag_data["group_tag"]: return
        canvas_x = self.canvas.canvasx(event.x)
        
        group_tag = self._drag_data["group_tag"]
        rect_item = next((item for item in self.canvas.find_withtag(group_tag) if "clip_rect" in self.canvas.gettags(item)), None)
        right_handle = next((item for item in self.canvas.find_withtag(group_tag) if "handle_right" in self.canvas.gettags(item)), None)
        
        if rect_item and right_handle:
            coords = self.canvas.coords(rect_item)
            min_width = 15
            new_x2 = max(canvas_x, coords[0] + min_width)
            
            self.canvas.coords(rect_item, coords[0], coords[1], new_x2, coords[3])
            handle_w = 6
            self.canvas.coords(right_handle, new_x2 - handle_w, coords[1], new_x2, coords[3])
        self.canvas.tag_raise(self.playhead_id)

    def set_playhead(self, x_pos):
        x_pos = max(0, min(x_pos, self.canvas_width))
        self.canvas.coords(self.playhead_id, x_pos, 0, x_pos, self.canvas_height)
        self.playhead_time = x_pos / self.pixels_per_second
        self.canvas.tag_raise(self.playhead_id)
        
        if hasattr(self, 'time_lbl'):
            self.time_lbl.config(text=f"{self.playhead_time:.2f}s / {self.duration:.2f}s")
            
        # Auto-scroll canvas if playhead moves out of view during playback
        if getattr(self, 'is_playing', False):
            scroll_info = self.scrollbar.get()
            if len(scroll_info) == 2:
                view_start_x = scroll_info[0] * self.canvas_width
                view_end_x = scroll_info[1] * self.canvas_width
                if x_pos > view_end_x - 50:
                    new_start_x = x_pos - (view_end_x - view_start_x) + 50
                    self.canvas.xview_moveto(new_start_x / max(1, self.canvas_width))
        
    def on_ruler_click(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        self.set_playhead(canvas_x)
        if self.is_playing:
            self._last_time = time.time() # Reset delta time to prevent jumping
        
    def on_ruler_drag(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        self.set_playhead(canvas_x)
        if self.is_playing:
            self._last_time = time.time()
            
    def toggle_playback(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_btn.config(text="⏸ Pause", bg="#f44336")
            if self.playhead_time >= self.duration:
                self.set_playhead(0) # Auto-rewind if at the end
            self._last_time = time.time()
            self._update_playback()
        else:
            self.play_btn.config(text="▶ Play", bg="#4CAF50")
            
    def _update_playback(self):
        if not self.is_playing: return
        now = time.time()
        dt = now - self._last_time
        self._last_time = now
        new_time = self.playhead_time + dt
        if new_time >= self.duration:
            new_time = self.duration
            self.is_playing = False
            self.play_btn.config(text="▶ Play", bg="#4CAF50")
        self.set_playhead(new_time * self.pixels_per_second)
        if self.is_playing:
            self.after(16, self._update_playback) # Run approx at 60fps
            
    def get_clips(self):
        clips = []
        for item in self.canvas.find_withtag("clip_rect"):
            tags = self.canvas.gettags(item)
            group_tag = next((t for t in tags if t.startswith("clip_group_")), None)
            if group_tag:
                clip_id = group_tag.replace("clip_group_", "")
                coords = self.canvas.coords(item)
                if len(coords) >= 4:
                    start_time = coords[0] / self.pixels_per_second
                    duration = (coords[2] - coords[0]) / self.pixels_per_second
                    
                    y1 = coords[1]
                    track_index = int(round((y1 - self.ruler_height - 20) / self.track_height))
                    
                    clips.append({
                        "id": clip_id,
                        "track": track_index,
                        "start": start_time,
                        "duration": duration
                    })
        return clips

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Timeline Editor Test")
    root.geometry("900x400")
    root.configure(bg="#2b2b2b")
    
    # Create timeline for a 60-second video
    timeline = TimelineEditor(root, duration=60)
    timeline.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Populate with some mock clips
    timeline.add_clip(0, 0, 60, "#e74c3c", "TTS Audio Waveform", "audio_1")
    timeline.add_clip(1, 0, 60, "#3498db", "Base Background.mp4", "base_1")
    timeline.add_clip(2, 5, 4, "#2ecc71", "Overlay Image 1", "ov_1")
    timeline.add_clip(2, 15, 6, "#2ecc71", "Overlay Image 2", "ov_2")
    timeline.add_clip(2, 35, 4, "#f1c40f", "DuckDuckGo Image", "ov_3")
    
    root.mainloop()