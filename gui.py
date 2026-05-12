import os
import asyncio
import threading
import queue
import requests
import datetime
import platform
import subprocess
from PIL import Image, ImageTk, ImageDraw, ImageFont
import tkinter as tk
from tkinter import scrolledtext, filedialog, ttk
from config import OLLAMA_API_URL, OUTPUT_DIR, ASSETS_DIR
from core import ParceiroAutomacao
from timeline import TimelineEditor
from image_generator import AIImageGenerator
from web_scraper import WebScraper
from dialogs import show_script_review, show_image_review

class AutomacaoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("VideoMaekar Studio")
        
        try:
            self.root.state('zoomed')
        except tk.TclError:
            try:
                self.root.attributes('-zoomed', True)
            except tk.TclError:
                self.root.geometry("1400x900")
                
        # --- Fullscreen Toggle ---
        self.is_fullscreen = False
        def toggle_fullscreen(event=None):
            self.is_fullscreen = not self.is_fullscreen
            self.root.attributes('-fullscreen', self.is_fullscreen)
            return "break"
            
        def end_fullscreen(event=None):
            self.is_fullscreen = False
            self.root.attributes('-fullscreen', False)
            return "break"
            
        self.root.bind("<F11>", toggle_fullscreen)
        self.root.bind("<Escape>", end_fullscreen)
        
        # --- Theme Colors ---
        bg_color = "#2b2b2b"
        panel_bg = "#323232"
        fg_color = "#ffffff"
        entry_bg = "#3b3b3b"
        btn_bg = "#555555"
        
        self.root.configure(bg=bg_color)
        
        # --- Variables ---
        self.out_dir_var = tk.StringVar(value=os.path.abspath(OUTPUT_DIR))
        self.model_var = tk.StringVar()
        self.local_imgs = []
        self.bg_music_var = tk.StringVar()
        self.loop_bg_var = tk.BooleanVar(value=True)
        self.num_images_var = tk.IntVar(value=5)
        self.use_videos_var = tk.BooleanVar(value=True)
        self.use_images_var = tk.BooleanVar(value=True)
        self.image_source_var = tk.StringVar(value="DuckDuckGo")
        self.enable_narration_var = tk.BooleanVar(value=True)
        self.transcribe_mode_var = tk.BooleanVar(value=False)
        self.subtitle_only_var = tk.BooleanVar(value=False)
        self.workflow_mode_var = tk.StringVar(value="script")
        self.script_tone_var = tk.StringVar(value="Educational")
        self.hook_type_var = tk.StringVar(value="None")
        self.sub_font_var = tk.StringVar(value="Arial Bold")
        self.sub_font_file_var = tk.StringVar(value="")
        self.sub_color_var = tk.StringVar(value="yellow")
        self.sub_outline_color_var = tk.StringVar(value="black")
        self.sub_outline_width_var = tk.IntVar(value=3)
        self.sub_size_var = tk.IntVar(value=60)
        self.sub_y_var = tk.IntVar(value=1300)
        self.transition_var = tk.StringVar(value="Cut")
        self.visual_effect_var = tk.StringVar(value="None")
        self.terms_var = tk.StringVar(value="The simulation theory and our reality, matrix code, digital universe, abstract technology, future city")
        self.progress_var = tk.DoubleVar()
        self.is_generating = False
        self.spinner_states = ['|', '/', '-', '\\']
        self.spinner_idx = 0
        self.script_approved_event = threading.Event()
        self.approved_script = ""
        self.images_approved_event = threading.Event()
        self.images_retry = False
        self.new_search_terms = ""
        self.images_cancelled = False
        self.last_generated_media_path = None
        self.custom_timeline = None
        self.current_generation_id = None
        self.render_approved_event = threading.Event()
        
        # --- Main Workspace Layout ---
        self.main_paned = tk.PanedWindow(self.root, orient=tk.VERTICAL, bg=bg_color, bd=0, sashwidth=6, sashrelief=tk.RAISED)
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        
        self.workspace = tk.Frame(self.main_paned, bg=bg_color)
        self.main_paned.add(self.workspace, stretch="always")
        
        self.workspace.columnconfigure(0, weight=3)
        self.workspace.columnconfigure(1, weight=5)
        self.workspace.columnconfigure(2, weight=2)
        self.workspace.rowconfigure(0, weight=1)
        
        # --- Left Panel - Settings (Scrollable) ---
        left_panel_container = tk.Frame(self.workspace, bg=bg_color)
        left_panel_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.left_canvas = tk.Canvas(left_panel_container, bg=bg_color, highlightthickness=0)
        self.left_scrollbar = ttk.Scrollbar(left_panel_container, orient="vertical", command=self.left_canvas.yview)
        self.left_frame = tk.Frame(self.left_canvas, bg=bg_color)
        
        self.left_frame.bind("<Configure>", lambda e: self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all")))
        self.left_canvas_window = self.left_canvas.create_window((0, 0), window=self.left_frame, anchor="nw")
        self.left_canvas.bind("<Configure>", lambda e: self.left_canvas.itemconfig(self.left_canvas_window, width=e.width))
        self.left_canvas.configure(yscrollcommand=self.left_scrollbar.set)
        
        self.left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def _on_mousewheel(event):
            if isinstance(event.widget, (tk.Text, tk.Spinbox, ttk.Combobox)):
                return
            if platform.system() == "Windows":
                self.left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            elif platform.system() == "Darwin":
                self.left_canvas.yview_scroll(int(-1*event.delta), "units")
            else:
                if event.num == 4: self.left_canvas.yview_scroll(-1, "units")
                elif event.num == 5: self.left_canvas.yview_scroll(1, "units")

        if platform.system() == "Linux":
            self.root.bind_all("<Button-4>", _on_mousewheel)
            self.root.bind_all("<Button-5>", _on_mousewheel)
        else:
            self.root.bind_all("<MouseWheel>", _on_mousewheel)

        col1 = self._create_collapsible_section(self.left_frame, "AI & Scripting", bg_color, panel_bg, fg_color)
        col2 = self._create_collapsible_section(self.left_frame, "Visuals & Media", bg_color, panel_bg, fg_color)
        col3 = self._create_collapsible_section(self.left_frame, "Audio & Subtitles", bg_color, panel_bg, fg_color)
        
        # --- Column 1: AI & Scripting ---
        tk.Label(col1, text="Ollama Model:", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(10, 2))
        available_models = self.get_ollama_models()
        if available_models: self.model_var.set(available_models[0])
        self.model_cb = ttk.Combobox(col1, textvariable=self.model_var, values=available_models, state="readonly")
        self.model_cb.pack(fill=tk.X, padx=10, pady=2)
        
        tk.Label(col1, text="Workflow Mode:", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(10, 2))
        wf_frame = tk.Frame(col1, bg=panel_bg)
        wf_frame.pack(fill=tk.X, padx=10, pady=2)
        
        tk.Radiobutton(wf_frame, text="Generate AI Video (Script -> Video)", variable=self.workflow_mode_var, value="script", command=self.update_ui_states, bg=panel_bg, fg=fg_color, selectcolor=btn_bg, activebackground=panel_bg, activeforeground=fg_color).pack(anchor='w')
        tk.Radiobutton(wf_frame, text="Illustrate Uploaded Video (Whisper + Media)", variable=self.workflow_mode_var, value="illustrate", command=self.update_ui_states, bg=panel_bg, fg=fg_color, selectcolor=btn_bg, activebackground=panel_bg, activeforeground=fg_color).pack(anchor='w')
        tk.Radiobutton(wf_frame, text="< Subtitle this video > (Skip visuals)", variable=self.workflow_mode_var, value="subtitle", command=self.update_ui_states, bg=panel_bg, fg=fg_color, selectcolor=btn_bg, activebackground=panel_bg, activeforeground=fg_color).pack(anchor='w')
        
        tk.Label(col1, text="Script Tone:", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(5, 2))
        self.tone_cb = ttk.Combobox(col1, textvariable=self.script_tone_var, values=["Educational", "Professional", "Humorous", "Dramatic", "Casual", "Enthusiastic"], state="readonly")
        self.tone_cb.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        tk.Label(col1, text="Opening Hook:", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(5, 2))
        self.hook_cb = ttk.Combobox(col1, textvariable=self.hook_type_var, values=["None", "Surprising Fact", "Provocative Question", "Bold Statement", "Story/Anecdote", "Direct Challenge"], state="readonly")
        self.hook_cb.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        tk.Label(col1, text="AI Prompt:", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(5, 2))
        self.prompt_text = scrolledtext.ScrolledText(col1, height=10, bg=entry_bg, fg=fg_color, insertbackground=fg_color)
        self.prompt_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        default_prompt = (
            "Write a detailed educational script for a 70-second video about 'The simulation theory and our reality'. "
            "The script must be in English, engaging, and have at least 180 words. "
            "Return ONLY the spoken text. DO NOT include timestamps, scene descriptions, speaker labels, or any formatting."
        )
        self.prompt_text.insert(tk.END, default_prompt)
        
        # --- Column 2: Visuals & Media ---
        tk.Label(col2, text="Local Media (Images/Videos):", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(10, 2))
        media_btn_frame = tk.Frame(col2, bg=panel_bg)
        media_btn_frame.pack(fill=tk.X, padx=10, pady=2)
        tk.Button(media_btn_frame, text="Browse Media", command=self.browse_media, bg=btn_bg, fg=fg_color).pack(side=tk.LEFT)
        self.local_imgs_lbl = tk.Label(media_btn_frame, text="0 files selected", bg=panel_bg, fg=fg_color)
        self.local_imgs_lbl.pack(side=tk.LEFT, padx=10)
        
        self.media_preview_frame = tk.Frame(col2, bg=panel_bg)
        self.media_preview_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        self.preview_thumbnails = [] # Holds references to avoid garbage collection
        
        toggles_frame = tk.Frame(col2, bg=panel_bg)
        toggles_frame.pack(fill=tk.X, padx=10, pady=10)
        self.use_videos_cb = tk.Checkbutton(toggles_frame, text="Use Videos", variable=self.use_videos_var, command=self.update_ui_states, bg=panel_bg, fg=fg_color, selectcolor=btn_bg, activebackground=panel_bg, activeforeground=fg_color)
        self.use_videos_cb.pack(anchor='w', pady=2)
        self.use_images_cb = tk.Checkbutton(toggles_frame, text="Use Images", variable=self.use_images_var, command=self.update_ui_states, bg=panel_bg, fg=fg_color, selectcolor=btn_bg, activebackground=panel_bg, activeforeground=fg_color)
        self.use_images_cb.pack(anchor='w', pady=2)
        
        tk.Label(col2, text="Image Source:", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(10, 2))
        src_frame = tk.Frame(col2, bg=panel_bg)
        src_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        self.image_source_cb = ttk.Combobox(src_frame, textvariable=self.image_source_var, values=["DuckDuckGo", "AI Generator (Google Imagen)"], state="readonly")
        self.image_source_cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.test_api_btn = tk.Button(src_frame, text="Test API", command=self.test_api_connection, bg=btn_bg, fg=fg_color)
        self.test_api_btn.pack(side=tk.LEFT, padx=(5, 0))
        self.image_source_var.trace_add("write", self.update_ui_states)
        
        tk.Label(col2, text="Number of Images:", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(5, 2))
        self.num_images_spinbox = tk.Spinbox(col2, from_=1, to=100, textvariable=self.num_images_var, bg=entry_bg, fg=fg_color, insertbackground=fg_color, buttonbackground=btn_bg)
        self.num_images_spinbox.pack(fill=tk.X, padx=10, pady=2)
        
        self.prompts_lbl = tk.Label(col2, text="Image Search Terms (comma separated):", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold'))
        self.prompts_lbl.pack(anchor='w', padx=10, pady=(10, 2))
        self.prompts_text = scrolledtext.ScrolledText(col2, height=4, bg=entry_bg, fg=fg_color, insertbackground=fg_color)
        self.prompts_text.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.prompts_text.insert(tk.END, self.terms_var.get())
        
        tk.Label(col2, text="Transition Effect:", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(5, 2))
        ttk.Combobox(col2, textvariable=self.transition_var, values=["Cut", "Fade In", "Fade Out", "Fade In & Out"], state="readonly").pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Label(col2, text="Visual Effect:", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(5, 2))
        ttk.Combobox(col2, textvariable=self.visual_effect_var, values=["None", "Zoom-In", "Zoom-Out", "Pan Left", "Pan Right", "Pan Up", "Pan Down"], state="readonly").pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Checkbutton(col3, text="Enable Narration Audio", variable=self.enable_narration_var, bg=panel_bg, fg=fg_color, selectcolor=btn_bg, activebackground=panel_bg, activeforeground=fg_color).pack(anchor='w', padx=10, pady=(10, 5))
        
        tk.Label(col3, text="Background Music (.mp3):", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(5, 2))
        bg_btn_frame = tk.Frame(col3, bg=panel_bg)
        bg_btn_frame.pack(fill=tk.X, padx=10, pady=2)
        tk.Entry(bg_btn_frame, textvariable=self.bg_music_var, bg=entry_bg, fg=fg_color, insertbackground=fg_color).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(bg_btn_frame, text="Browse", command=self.browse_music, bg=btn_bg, fg=fg_color).pack(side=tk.LEFT, padx=(5,0))
        
        tk.Label(col3, text="Background Volume (%):", bg=panel_bg, fg=fg_color, font=('Arial', 9)).pack(anchor='w', padx=10, pady=(10, 0))
        vol_frame = tk.Frame(col3, bg=panel_bg)
        vol_frame.pack(fill=tk.X, padx=10, pady=2)
        self.volume_var = tk.DoubleVar(value=10.0)
        self.volume_scale = ttk.Scale(vol_frame, from_=0.0, to=100.0, orient=tk.HORIZONTAL, variable=self.volume_var)
        self.volume_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.vol_lbl = tk.Label(vol_frame, text="10%", bg=panel_bg, fg=fg_color, font=('Arial', 8), width=4)
        self.vol_lbl.pack(side=tk.LEFT, padx=5)
        self.volume_var.trace_add("write", lambda *a: self.vol_lbl.config(text=f"{int(self.volume_var.get())}%"))
        
        tk.Checkbutton(col3, text="Loop Background Music", variable=self.loop_bg_var, bg=panel_bg, fg=fg_color, selectcolor=btn_bg, activebackground=panel_bg, activeforeground=fg_color).pack(anchor='w', padx=10, pady=10)
        
        tk.Label(col3, text="Subtitles Styling:", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(5, 2))
        sub_frame = tk.Frame(col3, bg=panel_bg)
        sub_frame.pack(fill=tk.X, padx=10, pady=2)
        ttk.Combobox(sub_frame, textvariable=self.sub_font_var, values=["Arial", "Arial Bold", "Impact", "Comic Sans", "Times New Roman"], state="readonly", width=15).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(sub_frame, text="...", command=self.browse_font, bg=btn_bg, fg=fg_color, width=3).pack(side=tk.LEFT, padx=(2,5))
        ttk.Combobox(sub_frame, textvariable=self.sub_color_var, values=["yellow", "white", "cyan", "green", "red", "magenta"], state="readonly", width=8).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Combobox(sub_frame, textvariable=self.sub_outline_color_var, values=["black", "white", "gray", "red", "blue", "green"], state="readonly", width=8).pack(side=tk.LEFT, padx=(0, 5))
        tk.Spinbox(sub_frame, from_=0, to=20, textvariable=self.sub_outline_width_var, width=3, bg=entry_bg, fg=fg_color, buttonbackground=btn_bg).pack(side=tk.LEFT, padx=(0, 5))
        tk.Spinbox(sub_frame, from_=30, to=120, textvariable=self.sub_size_var, width=4, bg=entry_bg, fg=fg_color, buttonbackground=btn_bg).pack(side=tk.LEFT)
        
        y_frame = tk.Frame(col3, bg=panel_bg)
        y_frame.pack(fill=tk.X, padx=10, pady=2)
        tk.Label(y_frame, text="Subtitle Y-Position (0-1920):", bg=panel_bg, fg=fg_color, font=('Arial', 9)).pack(side=tk.LEFT)
        tk.Spinbox(y_frame, from_=0, to=1920, textvariable=self.sub_y_var, width=5, bg=entry_bg, fg=fg_color, buttonbackground=btn_bg).pack(side=tk.LEFT, padx=5)
        
        self.sub_font_var.trace_add("write", self.on_font_change)
        self.sub_color_var.trace_add("write", lambda *args: self.update_preview())
        self.sub_outline_color_var.trace_add("write", lambda *args: self.update_preview())
        self.sub_outline_width_var.trace_add("write", lambda *args: self.update_preview())
        self.sub_size_var.trace_add("write", lambda *args: self.update_preview())
        self.sub_y_var.trace_add("write", lambda *args: self.update_preview())
        self.root.after(100, self.update_preview)
        self.update_ui_states()
        
        # --- Center Panel - Live Preview ---
        center_panel = tk.Frame(self.workspace, bg=bg_color)
        center_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        tk.Label(center_panel, text="Live Project Preview (9:16) [F11: Fullscreen Toggle]", bg=bg_color, fg=fg_color, font=('Arial', 11, 'bold')).pack(pady=(0, 10))
        
        self.preview_canvas = tk.Canvas(center_panel, bg="#000000", highlightthickness=2, highlightbackground="#555555")
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        self.preview_canvas.bind("<Configure>", self.update_preview)
        
        # --- Right Panel - Output & Actions ---
        right_panel = tk.Frame(self.workspace, bg=bg_color)
        right_panel.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        
        output_frame = tk.LabelFrame(right_panel, text=" Output Settings ", bg=panel_bg, fg=fg_color, font=('Arial', 11, 'bold'))
        output_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(output_frame, text="Output Directory:", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(10, 2))
        out_btn_frame = tk.Frame(output_frame, bg=panel_bg)
        out_btn_frame.pack(fill=tk.X, padx=10, pady=(2, 10))
        tk.Entry(out_btn_frame, textvariable=self.out_dir_var, bg=entry_bg, fg=fg_color, insertbackground=fg_color).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(out_btn_frame, text="Browse", command=self.browse_dir, bg=btn_bg, fg=fg_color).pack(side=tk.LEFT, padx=(5,0))
        
        action_frame = tk.LabelFrame(right_panel, text=" Render & Publish ", bg=panel_bg, fg=fg_color, font=('Arial', 11, 'bold'))
        action_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        btn_container = tk.Frame(action_frame, bg=panel_bg)
        btn_container.pack(fill=tk.X, pady=10, padx=10)
        
        self.btn_pre_gen = tk.Button(btn_container, text="PRE-GENERATE ASSETS", command=self.start_generation, bg="#FF9800", fg="white", font=('Arial', 12, 'bold'), pady=8)
        self.btn_pre_gen.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
        
        self.btn_render = tk.Button(btn_container, text="FINAL RENDER", command=self.start_final_render, bg="#4CAF50", fg="white", font=('Arial', 14, 'bold'), pady=10, state="disabled")
        self.btn_render.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
        
        self.open_media_btn = tk.Button(btn_container, text="OPEN LAST VIDEO", command=self.open_last_media, state="disabled", bg="#2196F3", fg="white", font=('Arial', 12, 'bold'), pady=5)
        self.open_media_btn.pack(side=tk.TOP, fill=tk.X)
        
        self.toggle_tl_btn = tk.Button(btn_container, text="TIMELINE PANEL", command=self.toggle_timeline, bg="#555555", fg="white", font=('Arial', 12, 'bold'), pady=5)
        self.toggle_tl_btn.pack(side=tk.TOP, fill=tk.X, pady=(10, 0))
        
        progress_container = tk.Frame(action_frame, bg=panel_bg)
        progress_container.pack(fill=tk.X, padx=10, pady=5)
        
        self.spinner_lbl = tk.Label(progress_container, text="-", font=('Courier', 12, 'bold'), bg=panel_bg, fg=fg_color, width=3)
        self.spinner_lbl.pack(side=tk.LEFT)
        
        self.progress_bar = ttk.Progressbar(progress_container, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.progress_text_lbl = tk.Label(progress_container, text="0.0%", font=('Arial', 10, 'bold'), bg=panel_bg, fg=fg_color, width=6)
        self.progress_text_lbl.pack(side=tk.LEFT)
        
        tk.Label(action_frame, text="Progress Logs:", font=('Arial', 10, 'bold'), bg=panel_bg, fg=fg_color).pack(anchor='w', padx=10)
        self.log_area = scrolledtext.ScrolledText(action_frame, state='disabled', bg=entry_bg, fg=fg_color)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # --- Bottom Panel - Integrated Timeline ---
        self.timeline_container = tk.Frame(self.main_paned, bg=panel_bg)
        
        self.tl_header = tk.Frame(self.timeline_container, bg="#1e1e1e")
        self.tl_header.pack(fill=tk.X)
        tk.Label(self.tl_header, text="Integrated Timeline", fg=fg_color, bg="#1e1e1e", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=10, pady=5)
        
        self.close_tl_btn = tk.Button(self.tl_header, text="▼ Hide Timeline", command=self.toggle_timeline, bg=btn_bg, fg=fg_color, relief=tk.FLAT)
        self.close_tl_btn.pack(side=tk.RIGHT, padx=5, pady=2)
        
        self.approve_tl_btn = tk.Button(self.tl_header, text="Approve Timeline", bg="#4CAF50", fg="white", font=('Arial', 10, 'bold'), state=tk.DISABLED)
        self.approve_tl_btn.pack(side=tk.RIGHT, padx=10, pady=2)
        
        self.timeline_editor = TimelineEditor(self.timeline_container, duration=0)
        self.timeline_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.timeline_visible = False

    def _create_collapsible_section(self, parent, title, bg_color, panel_bg, fg_color, expanded=True):
        container = tk.Frame(parent, bg=bg_color)
        container.pack(fill=tk.X, padx=5, pady=3)
        
        btn_text = "▼" if expanded else "▶"
        btn = tk.Button(container, text=f" {btn_text}  {title} ", bg="#3b3b3b", activebackground="#444444", fg=fg_color, activeforeground=fg_color, font=('Arial', 10, 'bold'), relief=tk.FLAT, anchor='w', cursor="hand2")
        btn.pack(fill=tk.X)
        
        content = tk.Frame(container, bg=panel_bg, highlightbackground="#3b3b3b", highlightthickness=1)
        if expanded:
            content.pack(fill=tk.X)
            
        def toggle():
            if content.winfo_ismapped():
                content.pack_forget()
                btn.config(text=f" ▶  {title} ")
            else:
                content.pack(fill=tk.X)
                btn.config(text=f" ▼  {title} ")
                
        btn.config(command=toggle)
        return content

    def toggle_timeline(self):
        if self.timeline_visible:
            self.main_paned.forget(self.timeline_container)
            self.timeline_visible = False
        else:
            self.main_paned.add(self.timeline_container, minsize=250)
            self.timeline_visible = True

    def update_ui_states(self, *args):
        mode = self.workflow_mode_var.get()
        if mode == "script":
            self.transcribe_mode_var.set(False)
            self.subtitle_only_var.set(False)
        elif mode == "illustrate":
            self.transcribe_mode_var.set(True)
            self.subtitle_only_var.set(False)
        elif mode == "subtitle":
            self.transcribe_mode_var.set(True)
            self.subtitle_only_var.set(True)
            
        sub_only = self.subtitle_only_var.get()
        if sub_only:
            self.use_images_var.set(False)
            self.use_videos_var.set(False)
            
        self.use_videos_cb.config(state="disabled" if sub_only else "normal")
        self.use_images_cb.config(state="disabled" if sub_only else "normal")
        
        transcribe = self.transcribe_mode_var.get()
        use_img = self.use_images_var.get()
        image_source = self.image_source_var.get()
        
        self.num_images_spinbox.config(state="normal" if use_img else "disabled")
        self.image_source_cb.config(state="readonly" if use_img else "disabled")
        self.prompts_text.config(state="normal" if use_img else "disabled")
        if image_source == "AI Generator (Google Imagen)":
            self.prompts_lbl.config(text="Image Prompts (one per line):")
            self.test_api_btn.config(state="normal" if use_img else "disabled")
        else:
            self.prompts_lbl.config(text="Image Search Terms (comma separated):")
            self.test_api_btn.config(state="disabled")

        self.prompt_text.config(state="disabled" if transcribe else "normal")
        self.model_cb.config(state="disabled" if transcribe else "readonly")
        self.tone_cb.config(state="disabled" if transcribe else "readonly")
        self.hook_cb.config(state="disabled" if transcribe else "readonly")

    def test_api_connection(self):
        def _test():
            from config import GEMINI_API_KEY
            self.log("[*] Testing Google API Connection...")
            if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
                self.log("[!] API Key is missing. Please set GEMINI_API_KEY in config.py.")
                return
            
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    self.log("[*] SUCCESS: Google API Connection verified!")
                else:
                    error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                    self.log(f"[!] FAILED: Google API Error {response.status_code}: {error_msg}")
            except Exception as e:
                self.log(f"[!] ERROR: Could not connect to Google API. Details: {e}")

        threading.Thread(target=_test, daemon=True).start()

    def on_font_change(self, *args):
        presets = ["Arial", "Arial Bold", "Impact", "Comic Sans", "Times New Roman"]
        if self.sub_font_var.get() in presets:
            self.sub_font_file_var.set("")
        self.update_preview()

    def browse_font(self):
        font_file = filedialog.askopenfilename(
            title="Select Font File",
            filetypes=[("Font Files", "*.ttf *.otf"), ("All files", "*.*")]
        )
        if font_file:
            self.sub_font_file_var.set(font_file)
            font_name = os.path.basename(font_file)
            if len(font_name) > 20: font_name = font_name[:17] + "..."
            self.sub_font_var.set(font_name)

    def update_preview(self, *args):
        try:
            sub_size = self.sub_size_var.get()
            stroke_width = self.sub_outline_width_var.get()
            sub_y = self.sub_y_var.get()
        except tk.TclError:
            return
            
        canvas_w = self.preview_canvas.winfo_width()
        canvas_h = self.preview_canvas.winfo_height()
        
        if canvas_w < 10 or canvas_h < 10:
            canvas_w = 400
            canvas_h = int(canvas_w * (1920/1080))
            
        target_ratio = 1080 / 1920
        canvas_ratio = canvas_w / float(max(1, canvas_h))
        
        if canvas_ratio > target_ratio:
            preview_h = canvas_h
            preview_w = int(preview_h * target_ratio)
        else:
            preview_w = canvas_w
            preview_h = int(preview_w / target_ratio)
            
        preview_w = max(10, preview_w)
        preview_h = max(10, preview_h)
        
        img = Image.new('RGB', (preview_w, preview_h), (30, 30, 30))
        draw = ImageDraw.Draw(img)
        
        # Draw a mock video border inside to simulate cellphone screen
        draw.rectangle([0, 0, preview_w, preview_h], outline=(80, 80, 80), width=10)
        
        font_file = self.sub_font_file_var.get()
        if not font_file or not os.path.exists(font_file):
            font_map = {"Arial": "arial.ttf", "Arial Bold": "arialbd.ttf", "Impact": "impact.ttf", "Comic Sans": "comic.ttf", "Times New Roman": "times.ttf"}
            font_file = font_map.get(self.sub_font_var.get(), "arialbd.ttf")

        sub_color = self.sub_color_var.get()
        sub_outline_color = self.sub_outline_color_var.get()
        
        try: font = ImageFont.truetype(font_file, sub_size)
        except Exception: font = ImageFont.load_default()
            
        texto = "SAMPLE\nSUBTITLE"
        
        try:
            bbox = draw.multiline_textbbox((0, 0), texto, font=font, align='center')
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            text_w, text_h = draw.textsize(texto, font=font)
            
        x, y = (preview_w - text_w) / 2, sub_y
        
        try:
            draw.multiline_text((x, y), texto, font=font, fill=sub_color, align='center', stroke_width=stroke_width, stroke_fill=sub_outline_color)
        except TypeError:
            for ox in range(-stroke_width, stroke_width + 1):
                for oy in range(-stroke_width, stroke_width + 1):
                    if ox == 0 and oy == 0: continue
                    try: draw.multiline_text((x + ox, y + oy), texto, font=font, fill=sub_outline_color, align='center')
                    except AttributeError: draw.text((x + ox, y + oy), texto, font=font, fill=sub_outline_color)
                    
            try: draw.multiline_text((x, y), texto, font=font, fill=sub_color, align='center')
            except AttributeError: draw.text((x, y), texto, font=font, fill=sub_color)
        
        img_resized = img.resize((int(preview_w), int(preview_h)), Image.LANCZOS)
        self.preview_tk = ImageTk.PhotoImage(img_resized)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(canvas_w // 2, canvas_h // 2, anchor=tk.CENTER, image=self.preview_tk)

    def open_last_media(self):
        if self.last_generated_media_path and os.path.exists(self.last_generated_media_path):
            try:
                if platform.system() == "Windows":
                    os.startfile(self.last_generated_media_path)
                elif platform.system() == "Darwin":
                    subprocess.call(["open", self.last_generated_media_path])
                else:
                    subprocess.call(["xdg-open", self.last_generated_media_path])
            except Exception as e:
                self.log(f"[!] Could not open media: {e}")

    def browse_dir(self):
        directory = filedialog.askdirectory(initialdir=self.out_dir_var.get())
        if directory:
            self.out_dir_var.set(directory)

    def browse_media(self):
        files = filedialog.askopenfilenames(title="Select Media", filetypes=[("Media Files", "*.png *.jpg *.jpeg *.bmp *.mp4 *.mov *.avi *.webm")])
        if files:
            self.local_imgs = list(files)
            self.local_imgs_lbl.config(text=f"{len(self.local_imgs)} files selected")
            self.update_media_previews()
            
    def update_media_previews(self):
        for widget in self.media_preview_frame.winfo_children():
            widget.destroy()
        self.preview_thumbnails.clear()

        for path in self.local_imgs[:5]:
            try:
                if path.lower().endswith(('.mp4', '.mov', '.avi', '.webm')):
                    img = Image.new('RGB', (40, 40), (80, 80, 80))
                    draw = ImageDraw.Draw(img)
                    draw.polygon([(15, 10), (15, 30), (30, 20)], fill="white")
                else:
                    with Image.open(path) as img_file:
                        if img_file.mode != 'RGB':
                            img_file = img_file.convert('RGB')
                        img = img_file.copy()
                        img.thumbnail((40, 40), Image.LANCZOS)
                        bg = Image.new('RGB', (40, 40), (50, 50, 50))
                        offset_x = (40 - img.width) // 2
                        offset_y = (40 - img.height) // 2
                        bg.paste(img, (offset_x, offset_y))
                        img = bg
                        
                photo = ImageTk.PhotoImage(img)
                self.preview_thumbnails.append(photo)
                tk.Label(self.media_preview_frame, image=photo, bg="#323232", bd=1, relief="solid").pack(side=tk.LEFT, padx=(0, 5))
            except Exception as e:
                self.log(f"[!] Could not load preview for {os.path.basename(path)}: {e}")

        if len(self.local_imgs) > 5:
            tk.Label(self.media_preview_frame, text=f"+{len(self.local_imgs)-5}", bg="#323232", fg="#ffffff", font=('Arial', 8, 'bold')).pack(side=tk.LEFT, padx=2)

    def browse_music(self):
        file = filedialog.askopenfilename(title="Select Background Music", filetypes=[("Audio Files", "*.mp3 *.wav")])
        if file:
            self.bg_music_var.set(file)

    def get_ollama_models(self):
        try:
            base_url = OLLAMA_API_URL.rsplit('/', 1)[0]
            response = requests.get(f"{base_url}/tags", timeout=3)
            response.raise_for_status()
            models = [m['name'] for m in response.json().get('models', [])]
            return models if models else ["llama3"]
        except Exception as e:
            print(f"Warning: Could not fetch Ollama models ({e}).")
            return ["llama3"]

    def log(self, msg):
        self.root.after(0, self._log_thread_safe, msg)
        
    def _log_thread_safe(self, msg):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, msg + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')
        print(msg) # Keeping terminal logs active as well
        
    def _update_spinner(self):
        if self.is_generating:
            self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_states)
            self.spinner_lbl.config(text=self.spinner_states[self.spinner_idx])
            self.root.after(200, self._update_spinner)
        else:
            self.spinner_lbl.config(text="-")

    def update_progress(self, val):
        def _set():
            self.progress_var.set(val)
            self.progress_text_lbl.config(text=f"{val:.1f}%")
        self.root.after(0, _set)

    def start_final_render(self):
        self.render_approved_event.set()
        self.btn_render.config(state='disabled')
        self.btn_pre_gen.config(state='disabled')

    def start_generation(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_generation_id = timestamp
        self.btn_pre_gen.config(state='disabled')
        self.btn_render.config(state='disabled')
        self.render_approved_event.clear()
        self.open_media_btn.config(state='disabled')
        self.log_area.config(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state='disabled')
        self.progress_var.set(0)
        self.progress_text_lbl.config(text="0.0%")
        self.is_generating = True
        self._update_spinner()
        
        model = self.model_var.get()
        base_prompt = self.prompt_text.get(1.0, tk.END).strip()
        tone = self.script_tone_var.get()
        hook = self.hook_type_var.get()
        
        prompt = base_prompt
        if tone: prompt += f"\n\nPlease ensure the overall tone of the script is strictly {tone}."
        if hook and hook != "None": prompt += f"\n\nIMPORTANT: The very first sentence of the script MUST be a powerful, engaging '{hook}' to hook the viewer instantly."
        
        image_source = self.image_source_var.get()
        prompts_raw = self.prompts_text.get(1.0, tk.END).strip()
        if image_source == "AI Generator (Google Imagen)":
            terms = [p.strip() for p in prompts_raw.split('\n') if p.strip()]
        else:
            terms = [t.strip() for t in prompts_raw.split(",") if t.strip()]
        out_dir = self.out_dir_var.get()
        use_images = self.use_images_var.get()
        use_videos = self.use_videos_var.get()
        bg_music = self.bg_music_var.get().strip()
        # Scale down 0-100% to a max of 0.15 for intuitive background mixing
        bg_volume = (self.volume_var.get() / 100.0) * 0.15
        loop_bg = self.loop_bg_var.get()
        num_images = self.num_images_var.get()
        enable_narration = self.enable_narration_var.get()
        transcribe_mode = self.transcribe_mode_var.get()
        sub_font = self.sub_font_var.get()
        sub_font_file = self.sub_font_file_var.get()
        sub_color = self.sub_color_var.get()
        sub_outline_color = self.sub_outline_color_var.get()
        sub_outline_width = self.sub_outline_width_var.get()
        sub_size = self.sub_size_var.get()
        transition = self.transition_var.get()
        sub_y = self.sub_y_var.get()
        visual_effect = self.visual_effect_var.get()
        
        # Use a background thread to prevent UI freezing
        threading.Thread(target=self.run_automation_thread, args=(timestamp, model, prompt, terms, out_dir, self.local_imgs, use_images, use_videos, bg_music, bg_volume, loop_bg, num_images, enable_narration, transcribe_mode, sub_font, sub_font_file, sub_color, sub_outline_color, sub_outline_width, sub_size, transition, sub_y, visual_effect, image_source), daemon=True).start()
        
    def run_automation_thread(self, timestamp, model, prompt, terms, out_dir, local_imgs, use_images, use_videos, bg_music, bg_volume, loop_bg, num_images, enable_narration, transcribe_mode, sub_font, sub_font_file, sub_color, sub_outline_color, sub_outline_width, sub_size, transition, sub_y, visual_effect, image_source):
        try:
            out_path = asyncio.run(self.async_workflow(timestamp, model, prompt, terms, out_dir, local_imgs, use_images, use_videos, bg_music, bg_volume, loop_bg, num_images, enable_narration, transcribe_mode, sub_font, sub_font_file, sub_color, sub_outline_color, sub_outline_width, sub_size, transition, sub_y, visual_effect, image_source))
            if out_path and self.current_generation_id == timestamp:
                self.last_generated_media_path = out_path
                self.log(f"\n[*] DONE! Video saved to {out_path}")
                self.root.after(0, lambda: self.open_media_btn.config(state='normal'))
        except Exception as e:
            if self.current_generation_id == timestamp:
                self.log(f"\n[!] Error: {str(e)}")
        finally:
            if self.current_generation_id == timestamp:
                self.is_generating = False
                self.root.after(0, lambda: self.btn_pre_gen.config(state='normal'))
            
    async def async_workflow(self, timestamp, model, prompt, terms, out_dir, local_imgs, use_images, use_videos, bg_music, bg_volume, loop_bg, num_images, enable_narration, transcribe_mode, sub_font, sub_font_file, sub_color, sub_outline_color, sub_outline_width, sub_size, transition, sub_y, visual_effect, image_source):
        self.custom_timeline = None
        base_name = f"projeto_{timestamp}"
        bot = ParceiroAutomacao(model=model, log_cb=self.log, progress_cb=self.update_progress)
        
        try:
            if transcribe_mode:
                video_path = next((p for p in local_imgs if p.lower().endswith(('.mp4', '.mov', '.avi', '.webm'))), None)
                if not video_path:
                    raise RuntimeError("Modo 'Transcribe Video' ativo, mas nenhum vídeo selecionado em Local Media!")
                srt_file = bot.transcrever_video(video_path, base_name)
                audio_file = video_path # MoviePy extracts audio automatically
                guiao = ""
            else:
                guiao = bot.gerar_guiao(prompt)
                
                self.script_approved_event.clear()
                self.approved_script = ""
                
                def on_script_approve(edited_script):
                    self.approved_script = edited_script
                    self.script_approved_event.set()
                    
                def on_script_cancel():
                    self.approved_script = ""
                    self.script_approved_event.set()

                self.root.after(0, lambda: show_script_review(self.root, guiao, on_script_approve, on_script_cancel))
                
                while not self.script_approved_event.is_set():
                    await asyncio.sleep(0.5)
                    
                if not self.approved_script:
                    raise RuntimeError("Script review cancelled by user.")
                    
                guiao = self.approved_script
                
                audio_file, srt_file = await bot.gerar_audio_e_legendas(guiao, base_name)
        except Exception as e:
            raise RuntimeError(f"Geração de Script/Áudio falhou: {str(e)}")
        
        try:
            while True:
                imagens_info = []
                
                if (use_images or use_videos) and not self.subtitle_only_var.get():
                    local_image_count = 0
                    # 1. Processar imagens locais
                    for i, path in enumerate(local_imgs):
                        is_video = path.lower().endswith(('.mp4', '.mov', '.avi', '.webm'))
                        if is_video:
                            if use_videos:
                                kw = os.path.splitext(os.path.basename(path))[0].replace('_', ' ').replace('-', ' ')
                                imagens_info.append({'path': path, 'keyword': kw})
                                self.log(f"[*] Vídeo local adicionado à fila: {kw}")
                            continue
        
                        if use_images and local_image_count < num_images:
                            safe_path = os.path.join(ASSETS_DIR, f"img_local_{i}_safe.jpg")
                            try:
                                with Image.open(path) as img:
                                    img.load() # Force load to memory to prevent file locking/truncation
                                    if img.mode != 'RGB':
                                        rgb_img = img.convert('RGB')
                                    else:
                                        rgb_img = img.copy()
                                        
                                # Save safely after the original file handle is closed
                                rgb_img.save(safe_path, 'JPEG')
                            except Exception as e:
                                self.log(f"[!] Imagem local ignorada (erro: {str(e)}): {os.path.basename(path)}")
                                continue
                            
                            kw = os.path.splitext(os.path.basename(path))[0].replace('_', ' ').replace('-', ' ')
                            imagens_info.append({'path': safe_path, 'keyword': kw})
                            local_image_count += 1
                            self.log(f"[*] Imagem local adicionada à fila: {kw}")
        
                    # 2. Processar imagens DuckDuckGo
                    if use_images and terms and local_image_count < num_images:
                        num_to_generate = num_images - local_image_count
                        if image_source == "AI Generator (Google Imagen)":
                            self.log(f"[*] Handing off to AI Image Generator...")
                            ai_gen = AIImageGenerator(log_cb=self.log)
                            try:
                                ai_images = await ai_gen.generate_images(terms, num_to_generate, ASSETS_DIR)
                                imagens_info.extend(ai_images)
                            except (ValueError, RuntimeError) as e:
                                self.log(f"[!] AI Generation Error: {e}")
                        else:
                            scraper = WebScraper(log_cb=self.log)
                            ddg_images, _ = await scraper.scrape_images(terms, num_to_generate, 0, ASSETS_DIR)
                            imagens_info.extend(ddg_images)
                                
                if not imagens_info:
                    if self.subtitle_only_var.get():
                        self.log("[*] Subtitle Only mode active. Skipping visual media collection.")
                    else:
                        self.log("[!] No media provided/found. Proceeding with base video/background.")
                        
                    duration, planned_clips = bot.planejar_timeline(audio_file, srt_file, imagens_info, transcribe_mode)
                    
                    self.timeline_approved_event = threading.Event()
                    self.custom_timeline = []
                    
                    self.root.after(0, self.show_and_load_timeline, duration, audio_file, bg_music, bg_volume, planned_clips)
                    
                    while not self.timeline_approved_event.is_set():
                        await asyncio.sleep(0.5)
                        
                    break
                    
                self.images_approved_event.clear()
                self.images_retry = False
                self.images_cancelled = False
                self.new_search_terms = ", ".join(terms)
                
                def on_image_approve():
                    self.images_retry = False
                    self.images_approved_event.set()
                    
                def on_image_retry(new_terms):
                    self.new_search_terms = new_terms
                    self.images_retry = True
                    self.images_approved_event.set()
                    
                def on_image_cancel():
                    self.images_retry = False
                    self.images_cancelled = True
                    self.images_approved_event.set()

                self.root.after(0, lambda: show_image_review(
                    self.root, 
                    imagens_info, 
                    self.new_search_terms, 
                    on_image_approve, 
                    on_image_retry, 
                    on_image_cancel, 
                    self.log
                ))
                
                while not self.images_approved_event.is_set():
                    await asyncio.sleep(0.5)
                    
                if self.images_cancelled:
                    raise RuntimeError("Image review cancelled by user.")
                    
                if self.images_retry:
                    terms = [t.strip() for t in self.new_search_terms.split(",") if t.strip()]
                    self.root.after(0, lambda: self.terms_var.set(self.new_search_terms))
                    self.log("[*] Retrying image search with new terms...")
                    continue
                else:
                    duration, planned_clips = bot.planejar_timeline(audio_file, srt_file, imagens_info, transcribe_mode)
                    
                    self.timeline_approved_event = threading.Event()
                    self.custom_timeline = []
                    
                    self.root.after(0, self.show_and_load_timeline, duration, audio_file, bg_music, bg_volume, planned_clips)
                    
                    while not self.timeline_approved_event.is_set():
                        await asyncio.sleep(0.5)
                        
                    break
        except Exception as e:
            raise RuntimeError(f"Image Collection failed: {str(e)}")
            
        self.log("\n[*] Phase 1 Complete: Assets pre-generated and timeline configured.")
        self.log("[*] Review the timeline, make adjustments, then click 'FINAL RENDER'.")
        self.root.after(0, lambda: self.btn_render.config(state='normal'))
        self.root.after(0, lambda: self.btn_pre_gen.config(state='normal'))
        
        while not self.render_approved_event.is_set():
            if self.current_generation_id != timestamp:
                self.log("[*] Workflow aborted for a new generation run.")
                return None
            await asyncio.sleep(0.5)
            
        self.root.after(0, lambda: self.btn_pre_gen.config(state='disabled'))
        self.root.after(0, lambda: self.btn_render.config(state='disabled'))
        
        self.log("[*] Starting final rendering phase...")
                    
        try:
            return bot.criar_video_com_legendas(audio_file, srt_file, imagens_info, guiao, output_dir=out_dir, bg_music_path=bg_music, bg_volume=bg_volume, loop_bg=loop_bg, enable_narration=enable_narration, transcribe_mode=transcribe_mode, sub_font=sub_font, sub_font_file=sub_font_file, sub_color=sub_color, sub_outline_color=sub_outline_color, sub_outline_width=sub_outline_width, sub_size=sub_size, transition=transition, sub_y=sub_y, visual_effect=visual_effect, custom_timeline=self.custom_timeline)
        except Exception as e:
            raise RuntimeError(f"Video Rendering (MoviePy) failed: {str(e)}")

    def show_and_load_timeline(self, duration, audio_file, bg_music, bg_volume, planned_clips):
        if not self.timeline_visible:
            self.toggle_timeline()
            
        self.timeline_editor.clear()
        self.timeline_editor.update_duration(duration)
        self.timeline_editor.set_audio_sources(audio_file, bg_music if bg_music and os.path.exists(bg_music) else None, bg_volume)
        
        self.timeline_editor.add_clip(0, 0, duration, "#e74c3c", "Narration / Base Audio", "audio_main")
        
        if bg_music and os.path.exists(bg_music):
            try:
                from moviepy.audio.io.AudioFileClip import AudioFileClip
                bg_dur = AudioFileClip(bg_music).duration
                self.timeline_editor.add_clip(3, 0, min(bg_dur, duration), "#9b59b6", os.path.basename(bg_music), "bg_music")
            except Exception as e:
                self.log(f"[!] Aviso: Não foi possível ler duração da música ({e}). Usando duração base.")
                self.timeline_editor.add_clip(3, 0, duration, "#9b59b6", os.path.basename(bg_music), "bg_music")
                
        for clip in planned_clips:
            color = "#3498db" if clip["track"] == 1 else "#2ecc71"
            self.timeline_editor.add_clip(clip["track"], clip["start"], clip["duration"], color, clip["text"], clip["id"])
            
        self.approve_tl_btn.config(state=tk.NORMAL, text="Approve Timeline")
        self.approve_tl_btn.config(command=lambda: self.approve_timeline_from_ui(planned_clips))
        
    def approve_timeline_from_ui(self, planned_clips):
        edited_clips = self.timeline_editor.get_clips()
        for e_clip in edited_clips:
            if e_clip["id"] == "bg_music":
                planned_clips.append({
                    "id": "bg_music",
                    "path": self.bg_music_var.get().strip(),
                    "start": e_clip["start"],
                    "duration": e_clip["duration"],
                    "track": e_clip["track"]
                })
                continue
            for p_clip in planned_clips:
                if p_clip["id"] == e_clip["id"]:
                    p_clip.update({"start": e_clip["start"], "duration": e_clip["duration"], "track": e_clip["track"]})
                    break
                    
        self.custom_timeline = planned_clips
        self.timeline_editor.is_playing = False
        self.timeline_editor._stop_audio()
        self.approve_tl_btn.config(state=tk.DISABLED, text="Timeline Approved")
        self.timeline_approved_event.set()