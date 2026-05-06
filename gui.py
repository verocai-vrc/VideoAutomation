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
from web_scraper import WebScraper
from dialogs import show_script_review, show_image_review

class AutomacaoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("VideoMaekar")
        self.root.geometry("1100x900")
        
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
        self.use_internet_search_var = tk.BooleanVar(value=True)
        self.enable_narration_var = tk.BooleanVar(value=True)
        self.transcribe_mode_var = tk.BooleanVar(value=False)
        self.sub_font_var = tk.StringVar(value="Arial Bold")
        self.sub_font_file_var = tk.StringVar(value="")
        self.sub_color_var = tk.StringVar(value="yellow")
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
        
        # --- Main Scrollable Layout ---
        self.main_canvas = tk.Canvas(root, bg=bg_color, highlightthickness=0)
        self.main_scrollbar = ttk.Scrollbar(root, orient="vertical", command=self.main_canvas.yview)
        self.scrollable_main_frame = tk.Frame(self.main_canvas, bg=bg_color)
        
        self.scrollable_main_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )
        
        self.canvas_window = self.main_canvas.create_window((0, 0), window=self.scrollable_main_frame, anchor="nw")
        
        self.main_canvas.bind(
            "<Configure>",
            lambda e: self.main_canvas.itemconfig(self.canvas_window, width=e.width)
        )
        
        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)
        self.main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.main_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def _on_mousewheel(event):
            # Prevent double-scrolling if hovering over independent scrollable widgets
            if isinstance(event.widget, (tk.Text, tk.Spinbox, ttk.Combobox)):
                return
            if platform.system() == "Windows":
                self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            elif platform.system() == "Darwin":
                self.main_canvas.yview_scroll(int(-1*event.delta), "units")
            else:
                if event.num == 4: self.main_canvas.yview_scroll(-1, "units")
                elif event.num == 5: self.main_canvas.yview_scroll(1, "units")

        if platform.system() == "Linux":
            self.root.bind_all("<Button-4>", _on_mousewheel)
            self.root.bind_all("<Button-5>", _on_mousewheel)
        else:
            self.root.bind_all("<MouseWheel>", _on_mousewheel)

        # --- Top and Bottom Frames ---
        top_frame = tk.Frame(self.scrollable_main_frame, bg=bg_color)
        top_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        bottom_frame = tk.Frame(self.scrollable_main_frame, bg=bg_color)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # --- Columns ---
        top_frame.columnconfigure(0, weight=1, uniform="equal_cols")
        top_frame.columnconfigure(1, weight=1, uniform="equal_cols")
        top_frame.columnconfigure(2, weight=1, uniform="equal_cols")
        top_frame.rowconfigure(0, weight=1)

        col1 = tk.LabelFrame(top_frame, text=" AI & Scripting ", bg=panel_bg, fg=fg_color, font=('Arial', 11, 'bold'))
        col1.grid(row=0, column=0, sticky="nsew", padx=5)
        
        col2 = tk.LabelFrame(top_frame, text=" Visuals & Media ", bg=panel_bg, fg=fg_color, font=('Arial', 11, 'bold'))
        col2.grid(row=0, column=1, sticky="nsew", padx=5)
        
        col3 = tk.LabelFrame(top_frame, text=" Audio & Output ", bg=panel_bg, fg=fg_color, font=('Arial', 11, 'bold'))
        col3.grid(row=0, column=2, sticky="nsew", padx=5)
        
        # --- Column 1: AI & Scripting ---
        tk.Label(col1, text="Ollama Model:", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(10, 2))
        available_models = self.get_ollama_models()
        if available_models: self.model_var.set(available_models[0])
        self.model_cb = ttk.Combobox(col1, textvariable=self.model_var, values=available_models, state="readonly")
        self.model_cb.pack(fill=tk.X, padx=10, pady=2)
        
        tk.Checkbutton(col1, text="Transcribe Uploaded Video (Whisper AI)", variable=self.transcribe_mode_var, command=self.update_ui_states, bg=panel_bg, fg=fg_color, selectcolor=btn_bg, activebackground=panel_bg, activeforeground=fg_color).pack(anchor='w', padx=10, pady=10)
        
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
        tk.Checkbutton(toggles_frame, text="Use Videos", variable=self.use_videos_var, command=self.update_ui_states, bg=panel_bg, fg=fg_color, selectcolor=btn_bg, activebackground=panel_bg, activeforeground=fg_color).pack(anchor='w', pady=2)
        tk.Checkbutton(toggles_frame, text="Use Images", variable=self.use_images_var, command=self.update_ui_states, bg=panel_bg, fg=fg_color, selectcolor=btn_bg, activebackground=panel_bg, activeforeground=fg_color).pack(anchor='w', pady=2)
        self.internet_search_cb = tk.Checkbutton(toggles_frame, text="Internet Image Search", variable=self.use_internet_search_var, command=self.update_ui_states, bg=panel_bg, fg=fg_color, selectcolor=btn_bg, activebackground=panel_bg, activeforeground=fg_color)
        self.internet_search_cb.pack(anchor='w', pady=2)
        
        tk.Label(col2, text="Number of Images:", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(5, 2))
        self.num_images_spinbox = tk.Spinbox(col2, from_=1, to=100, textvariable=self.num_images_var, bg=entry_bg, fg=fg_color, insertbackground=fg_color, buttonbackground=btn_bg)
        self.num_images_spinbox.pack(fill=tk.X, padx=10, pady=2)
        
        tk.Label(col2, text="Image Search Terms (comma separated):", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(10, 2))
        self.terms_entry = tk.Entry(col2, textvariable=self.terms_var, bg=entry_bg, fg=fg_color, insertbackground=fg_color)
        self.terms_entry.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Label(col2, text="Transition Effect:", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(5, 2))
        ttk.Combobox(col2, textvariable=self.transition_var, values=["Cut", "Fade In", "Fade Out", "Fade In & Out"], state="readonly").pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Label(col2, text="Visual Effect:", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(5, 2))
        ttk.Combobox(col2, textvariable=self.visual_effect_var, values=["None", "Zoom-In", "Zoom-Out", "Pan Left", "Pan Right", "Pan Up", "Pan Down"], state="readonly").pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # --- Column 3: Audio & Output ---
        tk.Label(col3, text="Output Directory:", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(10, 2))
        out_btn_frame = tk.Frame(col3, bg=panel_bg)
        out_btn_frame.pack(fill=tk.X, padx=10, pady=2)
        tk.Entry(out_btn_frame, textvariable=self.out_dir_var, bg=entry_bg, fg=fg_color, insertbackground=fg_color).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(out_btn_frame, text="Browse", command=self.browse_dir, bg=btn_bg, fg=fg_color).pack(side=tk.LEFT, padx=(5,0))
        
        tk.Checkbutton(col3, text="Enable Narration Audio", variable=self.enable_narration_var, bg=panel_bg, fg=fg_color, selectcolor=btn_bg, activebackground=panel_bg, activeforeground=fg_color).pack(anchor='w', padx=10, pady=15)
        
        tk.Label(col3, text="Background Music (.mp3):", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(5, 2))
        bg_btn_frame = tk.Frame(col3, bg=panel_bg)
        bg_btn_frame.pack(fill=tk.X, padx=10, pady=2)
        tk.Entry(bg_btn_frame, textvariable=self.bg_music_var, bg=entry_bg, fg=fg_color, insertbackground=fg_color).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(bg_btn_frame, text="Browse", command=self.browse_music, bg=btn_bg, fg=fg_color).pack(side=tk.LEFT, padx=(5,0))
        
        tk.Label(col3, text="Volume:", bg=panel_bg, fg=fg_color, font=('Arial', 9)).pack(anchor='w', padx=10, pady=(10, 0))
        vol_frame = tk.Frame(col3, bg=panel_bg)
        vol_frame.pack(fill=tk.X, padx=10, pady=2)
        self.volume_scale = ttk.Scale(vol_frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL)
        self.volume_scale.set(0.1)
        self.volume_scale.pack(fill=tk.X, expand=True)
        
        tk.Checkbutton(col3, text="Loop Background Music", variable=self.loop_bg_var, bg=panel_bg, fg=fg_color, selectcolor=btn_bg, activebackground=panel_bg, activeforeground=fg_color).pack(anchor='w', padx=10, pady=10)
        
        tk.Label(col3, text="Subtitles Styling:", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(5, 2))
        sub_frame = tk.Frame(col3, bg=panel_bg)
        sub_frame.pack(fill=tk.X, padx=10, pady=2)
        ttk.Combobox(sub_frame, textvariable=self.sub_font_var, values=["Arial", "Arial Bold", "Impact", "Comic Sans", "Times New Roman"], state="readonly", width=15).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(sub_frame, text="...", command=self.browse_font, bg=btn_bg, fg=fg_color, width=3).pack(side=tk.LEFT, padx=(2,5))
        ttk.Combobox(sub_frame, textvariable=self.sub_color_var, values=["yellow", "white", "cyan", "green", "red", "magenta"], state="readonly", width=8).pack(side=tk.LEFT, padx=(0, 5))
        tk.Spinbox(sub_frame, from_=30, to=120, textvariable=self.sub_size_var, width=4, bg=entry_bg, fg=fg_color, buttonbackground=btn_bg).pack(side=tk.LEFT)
        
        y_frame = tk.Frame(col3, bg=panel_bg)
        y_frame.pack(fill=tk.X, padx=10, pady=2)
        tk.Label(y_frame, text="Subtitle Y-Position (0-1920):", bg=panel_bg, fg=fg_color, font=('Arial', 9)).pack(side=tk.LEFT)
        tk.Spinbox(y_frame, from_=0, to=1920, textvariable=self.sub_y_var, width=5, bg=entry_bg, fg=fg_color, buttonbackground=btn_bg).pack(side=tk.LEFT, padx=5)
        
        self.preview_canvas = tk.Canvas(col3, width=162, height=288, bg="#000000", highlightthickness=2, highlightbackground="#555555")
        self.preview_canvas.pack(pady=(10, 0))
        
        self.sub_font_var.trace_add("write", self.on_font_change)
        self.sub_color_var.trace_add("write", lambda *args: self.update_preview())
        self.sub_size_var.trace_add("write", lambda *args: self.update_preview())
        self.sub_y_var.trace_add("write", lambda *args: self.update_preview())
        self.root.after(100, self.update_preview)
        
        # --- Bottom Frame: Logs & Progress ---
        btn_container = tk.Frame(bottom_frame, bg=bg_color)
        btn_container.pack(fill=tk.X, pady=(0, 10))
        
        self.btn = tk.Button(btn_container, text="GENERATE VIDEO", command=self.start_generation, bg="#4CAF50", fg="white", font=('Arial', 14, 'bold'), pady=10)
        self.btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.open_media_btn = tk.Button(btn_container, text="OPEN LAST VIDEO", command=self.open_last_media, state="disabled", bg="#2196F3", fg="white", font=('Arial', 14, 'bold'), pady=10)
        self.open_media_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))
        
        progress_container = tk.Frame(bottom_frame, bg=bg_color)
        progress_container.pack(fill=tk.X, pady=5)
        
        self.spinner_lbl = tk.Label(progress_container, text="-", font=('Courier', 12, 'bold'), bg=bg_color, fg=fg_color, width=3)
        self.spinner_lbl.pack(side=tk.LEFT)
        
        self.progress_bar = ttk.Progressbar(progress_container, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.progress_text_lbl = tk.Label(progress_container, text="0.0%", font=('Arial', 10, 'bold'), bg=bg_color, fg=fg_color, width=6)
        self.progress_text_lbl.pack(side=tk.LEFT)
        
        tk.Label(bottom_frame, text="Progress Logs:", font=('Arial', 10, 'bold'), bg=bg_color, fg=fg_color).pack(anchor='w')
        self.log_area = scrolledtext.ScrolledText(bottom_frame, height=8, state='disabled', bg=entry_bg, fg=fg_color)
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def update_ui_states(self):
        use_img = self.use_images_var.get()
        use_net = self.use_internet_search_var.get()
        transcribe = self.transcribe_mode_var.get()
        
        self.num_images_spinbox.config(state="normal" if use_img else "disabled")
        self.internet_search_cb.config(state="normal" if use_img else "disabled")
        self.terms_entry.config(state="normal" if (use_img and use_net) else "disabled")
        self.prompt_text.config(state="disabled" if transcribe else "normal")
        self.model_cb.config(state="disabled" if transcribe else "readonly")

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
            sub_y = self.sub_y_var.get()
        except tk.TclError:
            return
            
        preview_w, preview_h = 1080, 1920
        scale = 0.15 # 162x288
        
        img = Image.new('RGB', (preview_w, preview_h), (30, 30, 30))
        draw = ImageDraw.Draw(img)
        
        # Draw a mock video border inside to simulate cellphone screen
        draw.rectangle([0, 0, preview_w, preview_h], outline=(80, 80, 80), width=10)
        
        font_file = self.sub_font_file_var.get()
        if not font_file or not os.path.exists(font_file):
            font_map = {"Arial": "arial.ttf", "Arial Bold": "arialbd.ttf", "Impact": "impact.ttf", "Comic Sans": "comic.ttf", "Times New Roman": "times.ttf"}
            font_file = font_map.get(self.sub_font_var.get(), "arialbd.ttf")

        sub_color = self.sub_color_var.get()
        
        try: font = ImageFont.truetype(font_file, sub_size)
        except Exception: font = ImageFont.load_default()
            
        texto = "SAMPLE\nSUBTITLE"
        stroke_width = max(2, int(sub_size * 0.06))
        
        try:
            bbox = draw.multiline_textbbox((0, 0), texto, font=font, align='center')
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            text_w, text_h = draw.textsize(texto, font=font)
            
        x, y = (preview_w - text_w) / 2, sub_y
        
        for ox in range(-stroke_width, stroke_width + 1):
            for oy in range(-stroke_width, stroke_width + 1):
                if ox == 0 and oy == 0: continue
                try: draw.multiline_text((x + ox, y + oy), texto, font=font, fill='black', align='center')
                except AttributeError: draw.text((x + ox, y + oy), texto, font=font, fill='black')
                
        try: draw.multiline_text((x, y), texto, font=font, fill=sub_color, align='center')
        except AttributeError: draw.text((x, y), texto, font=font, fill=sub_color)
        
        img_resized = img.resize((int(preview_w * scale), int(preview_h * scale)), Image.LANCZOS)
        self.preview_tk = ImageTk.PhotoImage(img_resized)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=self.preview_tk)

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

    def start_generation(self):
        self.btn.config(state='disabled')
        self.open_media_btn.config(state='disabled')
        self.log_area.config(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state='disabled')
        self.progress_var.set(0)
        self.progress_text_lbl.config(text="0.0%")
        self.is_generating = True
        self._update_spinner()
        
        model = self.model_var.get()
        prompt = self.prompt_text.get(1.0, tk.END).strip()
        terms = [t.strip() for t in self.terms_var.get().split(",") if t.strip()]
        out_dir = self.out_dir_var.get()
        use_images = self.use_images_var.get()
        use_videos = self.use_videos_var.get()
        use_internet = self.use_internet_search_var.get()
        bg_music = self.bg_music_var.get().strip()
        bg_volume = self.volume_scale.get()
        loop_bg = self.loop_bg_var.get()
        num_images = self.num_images_var.get()
        enable_narration = self.enable_narration_var.get()
        transcribe_mode = self.transcribe_mode_var.get()
        sub_font = self.sub_font_var.get()
        sub_font_file = self.sub_font_file_var.get()
        sub_color = self.sub_color_var.get()
        sub_size = self.sub_size_var.get()
        transition = self.transition_var.get()
        sub_y = self.sub_y_var.get()
        visual_effect = self.visual_effect_var.get()
        
        # Use a background thread to prevent UI freezing
        threading.Thread(target=self.run_automation_thread, args=(model, prompt, terms, out_dir, self.local_imgs, use_images, use_videos, use_internet, bg_music, bg_volume, loop_bg, num_images, enable_narration, transcribe_mode, sub_font, sub_font_file, sub_color, sub_size, transition, sub_y, visual_effect), daemon=True).start()
        
    def run_automation_thread(self, model, prompt, terms, out_dir, local_imgs, use_images, use_videos, use_internet, bg_music, bg_volume, loop_bg, num_images, enable_narration, transcribe_mode, sub_font, sub_font_file, sub_color, sub_size, transition, sub_y, visual_effect):
        try:
            out_path = asyncio.run(self.async_workflow(model, prompt, terms, out_dir, local_imgs, use_images, use_videos, use_internet, bg_music, bg_volume, loop_bg, num_images, enable_narration, transcribe_mode, sub_font, sub_font_file, sub_color, sub_size, transition, sub_y, visual_effect))
            self.last_generated_media_path = out_path
            self.log(f"\n[*] DONE! Video saved to {out_path}")
            self.root.after(0, lambda: self.open_media_btn.config(state='normal'))
        except Exception as e:
            self.log(f"\n[!] Error: {str(e)}")
        finally:
            self.is_generating = False
            self.root.after(0, lambda: self.btn.config(state='normal'))
            
    async def async_workflow(self, model, prompt, terms, out_dir, local_imgs, use_images, use_videos, use_internet, bg_music, bg_volume, loop_bg, num_images, enable_narration, transcribe_mode, sub_font, sub_font_file, sub_color, sub_size, transition, sub_y, visual_effect):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
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
                
                if use_images or use_videos:
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
                    if use_images and terms and use_internet and local_image_count < num_images:
                        scraper = WebScraper(log_cb=self.log)
                        ddg_images, local_image_count = await scraper.scrape_images(terms, num_images, local_image_count, ASSETS_DIR)
                        imagens_info.extend(ddg_images)
                                
                if not imagens_info:
                    self.log("[!] No media provided/found. Rendering video with black background.")
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
                    
                    def show_timeline_window():
                        timeline_win = tk.Toplevel(self.root)
                        timeline_win.title("Timeline Editor")
                        timeline_win.geometry("1000x550")
                        timeline_win.configure(bg="#2b2b2b")
                        timeline_win.transient(self.root)
                        timeline_win.grab_set()
                        
                        tk.Label(timeline_win, text="Adjust Media Timings (Drag to move, edges to resize):", font=('Arial', 12, 'bold'), bg="#2b2b2b", fg="#ffffff").pack(pady=10)
                        
                        editor = TimelineEditor(timeline_win, duration=duration)
                        editor.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
                        
                        editor.add_clip(0, 0, duration, "#e74c3c", "Narration / Base Audio", "audio_main")
                        
                        for clip in planned_clips:
                            color = "#3498db" if clip["track"] == 1 else "#2ecc71"
                            editor.add_clip(clip["track"], clip["start"], clip["duration"], color, clip["text"], clip["id"])
                            
                        def approve_timeline():
                            edited_clips = editor.get_clips()
                            for e_clip in edited_clips:
                                for p_clip in planned_clips:
                                    if p_clip["id"] == e_clip["id"]:
                                        p_clip.update({"start": e_clip["start"], "duration": e_clip["duration"], "track": e_clip["track"]})
                                        break
                            self.custom_timeline = planned_clips
                            editor.is_playing = False
                            timeline_win.destroy()
                            self.timeline_approved_event.set()
                            
                        btn_frame = tk.Frame(timeline_win, bg="#2b2b2b")
                        btn_frame.pack(fill=tk.X, pady=10)
                        tk.Button(btn_frame, text="Approve & Render Video", command=approve_timeline, bg="#4CAF50", fg="white", font=('Arial', 12, 'bold'), padx=20).pack(side=tk.RIGHT, padx=10)
                        
                        timeline_win.protocol("WM_DELETE_WINDOW", approve_timeline)
                        
                    self.root.after(0, show_timeline_window)
                    
                    while not self.timeline_approved_event.is_set():
                        await asyncio.sleep(0.5)
                        
                    break
        except Exception as e:
            raise RuntimeError(f"Image Collection failed: {str(e)}")
                    
        try:
            return bot.criar_video_com_legendas(audio_file, srt_file, imagens_info, guiao, output_dir=out_dir, bg_music_path=bg_music, bg_volume=bg_volume, loop_bg=loop_bg, enable_narration=enable_narration, transcribe_mode=transcribe_mode, sub_font=sub_font, sub_font_file=sub_font_file, sub_color=sub_color, sub_size=sub_size, transition=transition, sub_y=sub_y, visual_effect=visual_effect, custom_timeline=self.custom_timeline)
        except Exception as e:
            raise RuntimeError(f"Video Rendering (MoviePy) failed: {str(e)}")