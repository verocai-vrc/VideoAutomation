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
        self.root.title("Video Automation Setup")
        self.root.geometry("650x920")
        
        # --- Dark Theme Colors ---
        bg_color = "#2b2b2b"
        fg_color = "#ffffff"
        entry_bg = "#3b3b3b"
        btn_bg = "#555555"
        
        self.root.configure(bg=bg_color)
        
        # Output Directory
        tk.Label(root, text="Output Directory:", font=('Arial', 10, 'bold'), bg=bg_color, fg=fg_color).pack(pady=(15, 0))
        out_frame = tk.Frame(root, bg=bg_color)
        out_frame.pack(pady=5)
        self.out_dir_var = tk.StringVar(value=os.path.abspath(OUTPUT_DIR))
        tk.Entry(out_frame, textvariable=self.out_dir_var, width=55, bg=entry_bg, fg=fg_color, insertbackground=fg_color).pack(side=tk.LEFT, padx=5)
        tk.Button(out_frame, text="Browse", command=self.browse_dir, bg=btn_bg, fg=fg_color).pack(side=tk.LEFT)
        
        # Model
        tk.Label(root, text="Ollama Model:", font=('Arial', 10, 'bold'), bg=bg_color, fg=fg_color).pack(pady=(10, 0))
        self.model_var = tk.StringVar()
        available_models = self.get_ollama_models()
        if available_models: self.model_var.set(available_models[0])
        self.model_cb = ttk.Combobox(root, textvariable=self.model_var, values=available_models, width=37, state="readonly")
        self.model_cb.pack(pady=5)
        
        # Local Media
        tk.Label(root, text="Local Media (Images/Videos, optional):", font=('Arial', 10, 'bold'), bg=bg_color, fg=fg_color).pack(pady=(10, 0))
        img_frame = tk.Frame(root, bg=bg_color)
        img_frame.pack(pady=5)
        self.local_imgs = []
        self.local_imgs_lbl = tk.Label(img_frame, text="0 files selected", bg=bg_color, fg=fg_color)
        self.local_imgs_lbl.pack(side=tk.LEFT, padx=5)
        tk.Button(img_frame, text="Browse Media", command=self.browse_media, bg=btn_bg, fg=fg_color).pack(side=tk.LEFT)
        
        # Background Music
        tk.Label(root, text="Background Music (.mp3, optional):", font=('Arial', 10, 'bold'), bg=bg_color, fg=fg_color).pack(pady=(10, 0))
        bg_frame = tk.Frame(root, bg=bg_color)
        bg_frame.pack(pady=5)
        self.bg_music_var = tk.StringVar()
        tk.Entry(bg_frame, textvariable=self.bg_music_var, width=32, bg=entry_bg, fg=fg_color, insertbackground=fg_color).pack(side=tk.LEFT, padx=5)
        tk.Button(bg_frame, text="Browse", command=self.browse_music, bg=btn_bg, fg=fg_color).pack(side=tk.LEFT, padx=5)
        tk.Label(bg_frame, text="Vol:", bg=bg_color, fg=fg_color).pack(side=tk.LEFT)
        self.volume_scale = tk.Scale(bg_frame, from_=0.0, to=1.0, resolution=0.01, orient=tk.HORIZONTAL, bg=bg_color, fg=fg_color, highlightthickness=0, length=80)
        self.volume_scale.set(0.1)  # Default background volume at 10%
        self.volume_scale.pack(side=tk.LEFT, padx=5)
        
        self.loop_bg_var = tk.BooleanVar(value=True)
        tk.Checkbutton(bg_frame, text="Loop", variable=self.loop_bg_var, bg=bg_color, fg=fg_color, selectcolor=btn_bg, activebackground=bg_color, activeforeground=fg_color).pack(side=tk.LEFT, padx=5)
        
        # Prompt
        tk.Label(root, text="AI Prompt:", font=('Arial', 10, 'bold'), bg=bg_color, fg=fg_color).pack(pady=(10, 0))
        self.prompt_text = scrolledtext.ScrolledText(root, height=8, width=75, bg=entry_bg, fg=fg_color, insertbackground=fg_color)
        self.prompt_text.pack(pady=5)
        default_prompt = (
            "Write a detailed educational script for a 70-second video about 'The simulation theory and our reality'. "
            "The script must be in English, engaging, and have at least 180 words. Return ONLY the spoken text."
        )
        self.prompt_text.insert(tk.END, default_prompt)
        
        # Number of Images
        tk.Label(root, text="Number of Images in Video:", font=('Arial', 10, 'bold'), bg=bg_color, fg=fg_color).pack(pady=(10, 0))
        self.num_images_var = tk.IntVar(value=5)
        self.num_images_spinbox = tk.Spinbox(root, from_=1, to=100, textvariable=self.num_images_var, width=10, bg=entry_bg, fg=fg_color, insertbackground=fg_color, buttonbackground=btn_bg)
        self.num_images_spinbox.pack(pady=5)
        
        # Toggles
        toggles_frame = tk.Frame(root, bg=bg_color)
        toggles_frame.pack(pady=(10, 0))
        
        self.use_videos_var = tk.BooleanVar(value=True)
        tk.Checkbutton(toggles_frame, text="Use Videos", variable=self.use_videos_var, command=self.update_ui_states, bg=bg_color, fg=fg_color, selectcolor=btn_bg, activebackground=bg_color, activeforeground=fg_color, font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        
        self.use_images_var = tk.BooleanVar(value=True)
        tk.Checkbutton(toggles_frame, text="Use Images", variable=self.use_images_var, command=self.update_ui_states, bg=bg_color, fg=fg_color, selectcolor=btn_bg, activebackground=bg_color, activeforeground=fg_color, font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        
        self.use_internet_search_var = tk.BooleanVar(value=True)
        self.internet_search_cb = tk.Checkbutton(toggles_frame, text="Internet Search", variable=self.use_internet_search_var, command=self.update_ui_states, bg=bg_color, fg=fg_color, selectcolor=btn_bg, activebackground=bg_color, activeforeground=fg_color, font=('Arial', 10, 'bold'))
        self.internet_search_cb.pack(side=tk.LEFT, padx=5)
        
        self.enable_narration_var = tk.BooleanVar(value=True)
        tk.Checkbutton(toggles_frame, text="Narration Audio", variable=self.enable_narration_var, bg=bg_color, fg=fg_color, selectcolor=btn_bg, activebackground=bg_color, activeforeground=fg_color, font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        
        # Search terms
        tk.Label(root, text="Image Search Terms (comma separated):", font=('Arial', 10, 'bold'), bg=bg_color, fg=fg_color).pack(pady=(10, 0))
        self.terms_var = tk.StringVar(value="The simulation theory and our reality, matrix code, digital universe, abstract technology, future city")
        self.terms_entry = tk.Entry(root, textvariable=self.terms_var, width=75, bg=entry_bg, fg=fg_color, insertbackground=fg_color)
        self.terms_entry.pack(pady=5)
        
        # Generate Button
        self.btn = tk.Button(root, text="Generate Video", command=self.start_generation, bg="#4CAF50", fg="white", font=('Arial', 12, 'bold'))
        self.btn.pack(pady=20)
        
        # Logs
        tk.Label(root, text="Progress Logs:", font=('Arial', 10, 'bold'), bg=bg_color, fg=fg_color).pack()
        self.log_area = scrolledtext.ScrolledText(root, height=12, width=75, state='disabled', bg=entry_bg, fg=fg_color)
        self.log_area.pack(pady=5)
        
    def update_ui_states(self):
        use_img = self.use_images_var.get()
        use_net = self.use_internet_search_var.get()
        
        self.num_images_spinbox.config(state="normal" if use_img else "disabled")
        self.internet_search_cb.config(state="normal" if use_img else "disabled")
        self.terms_entry.config(state="normal" if (use_img and use_net) else "disabled")

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
        
    def start_generation(self):
        self.btn.config(state='disabled')
        self.log_area.config(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state='disabled')
        
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
        
        # Use a background thread to prevent UI freezing
        threading.Thread(target=self.run_automation_thread, args=(model, prompt, terms, out_dir, self.local_imgs, use_images, use_videos, use_internet, bg_music, bg_volume, loop_bg, num_images, enable_narration), daemon=True).start()
        
    def run_automation_thread(self, model, prompt, terms, out_dir, local_imgs, use_images, use_videos, use_internet, bg_music, bg_volume, loop_bg, num_images, enable_narration):
        try:
            asyncio.run(self.async_workflow(model, prompt, terms, out_dir, local_imgs, use_images, use_videos, use_internet, bg_music, bg_volume, loop_bg, num_images, enable_narration))
            self.log(f"\n[*] DONE! Video saved to {os.path.join(out_dir, 'video_legendado.mp4')}")
        except Exception as e:
            self.log(f"\n[!] Error: {str(e)}")
        finally:
            self.root.after(0, lambda: self.btn.config(state='normal'))
            
    async def async_workflow(self, model, prompt, terms, out_dir, local_imgs, use_images, use_videos, use_internet, bg_music, bg_volume, loop_bg, num_images, enable_narration):
        bot = ParceiroAutomacao(model=model, log_cb=self.log)
        
        try:
            guiao = bot.gerar_guiao(prompt)
        except Exception as e:
            raise RuntimeError(f"Script Generation (Ollama) failed: {str(e)}")
            
        try:
            audio_file, srt_file = await bot.gerar_audio_e_legendas(guiao, "projeto_v1")
        except Exception as e:
            raise RuntimeError(f"Audio & Subtitle Generation failed: {str(e)}")
        
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
            bot.criar_video_com_legendas(audio_file, srt_file, imagens_info, guiao, output_dir=out_dir, bg_music_path=bg_music, bg_volume=bg_volume, loop_bg=loop_bg, enable_narration=enable_narration)
        except Exception as e:
            raise RuntimeError(f"Video Rendering (MoviePy) failed: {str(e)}")