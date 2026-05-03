import os
import asyncio
import threading
import queue
import requests
from PIL import Image
import tkinter as tk
from tkinter import scrolledtext, filedialog, ttk
from duckduckgo_search import DDGS
from config import OLLAMA_API_URL, OUTPUT_DIR, ASSETS_DIR
from core import ParceiroAutomacao

class AutomacaoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("VideoMaekar")
        self.root.geometry("1100x750")
        
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
        self.terms_var = tk.StringVar(value="The simulation theory and our reality, matrix code, digital universe, abstract technology, future city")
        self.progress_var = tk.DoubleVar()
        self.is_generating = False
        self.spinner_states = ['|', '/', '-', '\\']
        self.spinner_idx = 0
        
        # --- Main Layout ---
        top_frame = tk.Frame(root, bg=bg_color)
        top_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        bottom_frame = tk.Frame(root, bg=bg_color)
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
            "The script must be in English, engaging, and have at least 180 words. Return ONLY the spoken text."
        )
        self.prompt_text.insert(tk.END, default_prompt)
        
        # --- Column 2: Visuals & Media ---
        tk.Label(col2, text="Local Media (Images/Videos):", bg=panel_bg, fg=fg_color, font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(10, 2))
        media_btn_frame = tk.Frame(col2, bg=panel_bg)
        media_btn_frame.pack(fill=tk.X, padx=10, pady=2)
        tk.Button(media_btn_frame, text="Browse Media", command=self.browse_media, bg=btn_bg, fg=fg_color).pack(side=tk.LEFT)
        self.local_imgs_lbl = tk.Label(media_btn_frame, text="0 files selected", bg=panel_bg, fg=fg_color)
        self.local_imgs_lbl.pack(side=tk.LEFT, padx=10)
        
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
        
        # --- Bottom Frame: Logs & Progress ---
        self.btn = tk.Button(bottom_frame, text="GENERATE VIDEO", command=self.start_generation, bg="#4CAF50", fg="white", font=('Arial', 14, 'bold'), pady=10)
        self.btn.pack(fill=tk.X, pady=(0, 10))
        
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
        self.terms_entry.config(state="normal" if (use_img and use_net and not transcribe) else "disabled")
        self.prompt_text.config(state="disabled" if transcribe else "normal")
        self.model_cb.config(state="disabled" if transcribe else "readonly")

    def browse_dir(self):
        directory = filedialog.askdirectory(initialdir=self.out_dir_var.get())
        if directory:
            self.out_dir_var.set(directory)

    def browse_media(self):
        files = filedialog.askopenfilenames(title="Select Media", filetypes=[("Media Files", "*.png *.jpg *.jpeg *.bmp *.mp4 *.mov *.avi *.webm")])
        if files:
            self.local_imgs = list(files)
            self.local_imgs_lbl.config(text=f"{len(self.local_imgs)} files selected")

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
        
        # Use a background thread to prevent UI freezing
        threading.Thread(target=self.run_automation_thread, args=(model, prompt, terms, out_dir, self.local_imgs, use_images, use_videos, use_internet, bg_music, bg_volume, loop_bg, num_images, enable_narration, transcribe_mode), daemon=True).start()
        
    def run_automation_thread(self, model, prompt, terms, out_dir, local_imgs, use_images, use_videos, use_internet, bg_music, bg_volume, loop_bg, num_images, enable_narration, transcribe_mode):
        try:
            asyncio.run(self.async_workflow(model, prompt, terms, out_dir, local_imgs, use_images, use_videos, use_internet, bg_music, bg_volume, loop_bg, num_images, enable_narration, transcribe_mode))
            self.log(f"\n[*] DONE! Video saved to {os.path.join(out_dir, 'video_legendado.mp4')}")
        except Exception as e:
            self.log(f"\n[!] Error: {str(e)}")
        finally:
            self.is_generating = False
            self.root.after(0, lambda: self.btn.config(state='normal'))
            
    async def async_workflow(self, model, prompt, terms, out_dir, local_imgs, use_images, use_videos, use_internet, bg_music, bg_volume, loop_bg, num_images, enable_narration, transcribe_mode):
        bot = ParceiroAutomacao(model=model, log_cb=self.log, progress_cb=self.update_progress)
        
        try:
            if transcribe_mode:
                video_path = next((p for p in local_imgs if p.lower().endswith(('.mp4', '.mov', '.avi', '.webm'))), None)
                if not video_path:
                    raise RuntimeError("Modo 'Transcribe Video' ativo, mas nenhum vídeo selecionado em Local Media!")
                srt_file = bot.transcrever_video(video_path, "projeto_v1")
                audio_file = video_path # MoviePy extracts audio automatically
                guiao = ""
            else:
                guiao = bot.gerar_guiao(prompt)
                audio_file, srt_file = await bot.gerar_audio_e_legendas(guiao, "projeto_v1")
        except Exception as e:
            raise RuntimeError(f"Geração de Script/Áudio falhou: {str(e)}")
        
        try:
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
                    self.log("[*] A descarregar imagens do DuckDuckGo...")
                    with DDGS() as ddgs:
                        for i, t in enumerate(terms):
                            if local_image_count >= num_images:
                                break
                                
                            remaining_terms = len(terms) - i
                            remaining_images = num_images - local_image_count
                            target_for_term = (remaining_images + remaining_terms - 1) // remaining_terms
                            
                            self.log(f"  -> A pesquisar: {t} (A tentar descarregar {target_for_term} imagens)")
                            if i > 0: await asyncio.sleep(2)
                            
                            res = []
                            for attempt in range(3):
                                try:
                                    res = list(ddgs.images(t, max_results=target_for_term * 3, safesearch="on"))
                                    break
                                except Exception as e:
                                    if "403" in str(e) or "Ratelimit" in str(e):
                                        if attempt < 2:
                                            wait_t = 5 * (attempt + 1)
                                            self.log(f"  [!] Rate limit. A aguardar {wait_t}s (tentativa {attempt+1}/3)...")
                                            await asyncio.sleep(wait_t)
                                        else:
                                            self.log(f"  [!] Falha contínua no DuckDuckGo para '{t}'. A ignorar termo.")
                                    else:
                                        self.log(f"  [!] Erro na pesquisa '{t}': {str(e)}. A ignorar termo.")
                                        break
                                    
                            if res:
                                downloaded_for_term = 0
                                for img_data in res:
                                    if local_image_count >= num_images or downloaded_for_term >= target_for_term:
                                        break
                                    try:
                                        path = os.path.join(ASSETS_DIR, f"img_ddg_{local_image_count}.jpg")
                                        response = requests.get(img_data['image'], timeout=10)
                                        response.raise_for_status() # Check for 403 or 404 HTTP errors
                                        
                                        with open(path, 'wb') as f: f.write(response.content)
                                        
                                        # Verify if the downloaded file is a valid image
                                        with Image.open(path) as img:
                                            img.verify()
                                            
                                        # Reopen to ensure it is in a standard RGB format (fixes WEBP/RGBA issues)
                                        with Image.open(path) as img:
                                            img.load() # Force load pixel data
                                            if img.mode != 'RGB':
                                                rgb_img = img.convert('RGB')
                                            else:
                                                rgb_img = img.copy()
                                                
                                        # Force save as JPEG unconditionally to correct fake .jpg extensions
                                        rgb_img.save(path, 'JPEG')
                                                
                                        imagens_info.append({'path': path, 'keyword': t})
                                        downloaded_for_term += 1
                                        local_image_count += 1
                                    except Exception as e:
                                        self.log(f"  [!] Link falhou ({str(e)[:30]}...). A tentar outra...")
                            
            if not imagens_info:
                self.log("[!] No media provided/found. Rendering video with black background.")
        except Exception as e:
            raise RuntimeError(f"Image Collection failed: {str(e)}")
                    
        try:
            bot.criar_video_com_legendas(audio_file, srt_file, imagens_info, guiao, output_dir=out_dir, bg_music_path=bg_music, bg_volume=bg_volume, loop_bg=loop_bg, enable_narration=enable_narration, transcribe_mode=transcribe_mode)
        except Exception as e:
            raise RuntimeError(f"Video Rendering (MoviePy) failed: {str(e)}")