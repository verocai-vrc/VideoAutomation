import requests
import os
import datetime
import asyncio
import re
import threading
import tkinter as tk
from tkinter import scrolledtext, filedialog, ttk
import edge_tts
import pysubs2
from moviepy import TextClip, ColorClip, CompositeVideoClip, ImageClip, AudioFileClip, concatenate_videoclips
from moviepy.audio.AudioClip import CompositeAudioClip
from duckduckgo_search import DDGS

# --- CONFIGURAÇÃO ---
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OUTPUT_DIR = "output_videos"
ASSETS_DIR = "assets"

for folder in [OUTPUT_DIR, ASSETS_DIR]:
    if not os.path.exists(folder): os.makedirs(folder)

class ParceiroAutomacao:
    def __init__(self, model="llama3", log_cb=print):
        self.model = model
        self.log = log_cb

    def gerar_guiao(self, prompt):
        """Gera o guião usando o prompt fornecido."""
        self.log("[*] A criar guião...")
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()
        return response.json()['response'].strip()

    async def gerar_audio_e_legendas(self, texto, base_name):
        """
        Gera o áudio e o ficheiro de legendas .srt de forma manual e robusta.
        """
        self.log("[*] A gerar voz e calculando tempos das legendas...")
        audio_path = os.path.join(ASSETS_DIR, f"{base_name}.mp3")
        subs_path = os.path.join(ASSETS_DIR, f"{base_name}.srt")
        
        communicate = edge_tts.Communicate(texto, "en-US-AndrewNeural") # Voz premium-like
        subs_data = []
        
        # 1. Transmitir o áudio e capturar os limites das palavras (WordBoundaries)
        with open(audio_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    # Guardamos o tempo e o texto da palavra
                    subs_data.append({
                        "start": chunk["offset"],
                        "duration": chunk["duration"],
                        "text": chunk["text"]
                    })

        # 2. Função interna para formatar o tempo para o padrão SRT (00:00:00,000)
        def format_srt_time(microseconds):
            td = datetime.timedelta(microseconds=microseconds / 10)
            total_seconds = int(td.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            millis = int(td.microseconds / 1000)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

        # 3. Escrever o arquivo SRT manualmente
        with open(subs_path, "w", encoding="utf-8") as f:
            for i, word in enumerate(subs_data):
                start_time = format_srt_time(word["start"])
                # O fim é o início + a duração da palavra
                end_time = format_srt_time(word["start"] + word["duration"])
                
                f.write(f"{i + 1}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{word['text']}\n\n")
        
        self.log(f"[V] Áudio e Legendas gerados com sucesso em {ASSETS_DIR}")
        return audio_path, subs_path

    def criar_video_com_legendas(self, audio_p, srt_p, imagens_info, guiao, output_dir=OUTPUT_DIR, bg_music_path=None, bg_volume=0.1, loop_bg=True):
        """Monta o vídeo final com imagens sincronizadas ao guião e legendas queimadas."""
        self.log("[*] A planear cronologia das imagens e a renderizar vídeo...")
        if not os.path.exists(output_dir): os.makedirs(output_dir)
        audio = AudioFileClip(audio_p)
        duracao_total = audio.duration

        if bg_music_path and os.path.exists(bg_music_path):
            try:
                self.log(f"[*] A adicionar música de fundo: {os.path.basename(bg_music_path)}")
                bg_clip = AudioFileClip(bg_music_path)
                if hasattr(bg_clip, 'multiply_volume'): bg_clip = bg_clip.multiply_volume(bg_volume)
                elif hasattr(bg_clip, 'with_volume_multiplier'): bg_clip = bg_clip.with_volume_multiplier(bg_volume)
                elif hasattr(bg_clip, 'volumex'): bg_clip = bg_clip.volumex(bg_volume)
                
                if loop_bg:
                    repeats = int(duracao_total // bg_clip.duration) + 1
                    bg_clips = [bg_clip.with_start(i * bg_clip.duration) for i in range(repeats)]
                    bg_clip = CompositeAudioClip(bg_clips).with_duration(duracao_total)
                else:
                    bg_clip = bg_clip.with_duration(min(duracao_total, bg_clip.duration))
                    
                audio = CompositeAudioClip([audio, bg_clip])
            except Exception as e:
                self.log(f"[!] Erro ao processar música de fundo: {e}")

        # 1. Carregar legendas primeiro para ter tempos precisos
        subs = pysubs2.load(srt_p, encoding="utf-8")
        script_text = ""
        script_timings = [] # (index in script_text, start_time)
        
        for line in subs:
            script_timings.append((len(script_text), line.start / 1000.0))
            script_text += line.text + " "

        # 2. Planear a linha do tempo das imagens baseada nos tempos reais do guião
        guiao_lower = script_text.lower()
        matched = []
        unmatched = []
        
        for info in imagens_info:
            kw = info['keyword'].lower().strip()
            match = re.search(r'\b' + re.escape(kw) + r'\b', guiao_lower) if kw else None
            idx = match.start() if match else guiao_lower.find(kw)
                
            if idx != -1 and kw:
                t = 0
                for start_idx, time in reversed(script_timings):
                    if idx >= start_idx:
                        t = time
                        break
                matched.append((t, info['path']))
            else:
                unmatched.append(info['path'])
                
        matched.sort(key=lambda x: x[0])
        
        if not matched:
            dur = duracao_total / max(1, len(unmatched))
            img_clips = [ImageClip(img).with_duration(dur).resized(height=1920) for img in unmatched]
        else:
            if matched[0][0] > 0.5:
                matched.insert(0, (0.0, unmatched.pop(0))) if unmatched else matched.__setitem__(0, (0.0, matched[0][1]))
            else:
                matched[0] = (0.0, matched[0][1])
                
            starts, paths = [m[0] for m in matched], [m[1] for m in matched]
            
            if unmatched:
                last_t = starts[-1]
                step = (duracao_total - last_t) / (len(unmatched) + 1)
                for i, u in enumerate(unmatched):
                    starts.append(last_t + step * (i + 1))
                    paths.append(u)
                    
            img_clips = [ImageClip(paths[i]).with_duration((starts[i+1] if i+1 < len(starts) else duracao_total) - starts[i]).resized(height=1920) for i in range(len(starts)) if (starts[i+1] if i+1 < len(starts) else duracao_total) - starts[i] > 0]

        video_base = concatenate_videoclips(img_clips, method="compose").with_audio(audio)

        # 3. Processar Legendas (SRT -> TextClips)
        subtitle_clips = []
        
        for line in subs:
            start = line.start / 1000.0
            end = line.end / 1000.0
            duration = end - start
            if duration <= 0: continue
            
            # Criar a legenda visual
            try:
                txt = TextClip(
                    text=line.text, 
                    font_size=60, color='yellow', font='Arial-Bold',
                    stroke_color='black', stroke_width=2,
                    method='caption', size=(900, None)
                ).with_start(start).with_duration(duration).with_position(('center', 1400))
            except TypeError:
                txt = TextClip(
                    line.text, 
                    fontsize=60, color='yellow', font='Arial-Bold',
                    stroke_color='black', stroke_width=2,
                    method='caption', size=(900, None)
                ).with_start(start).with_duration(duration).with_position(('center', 1400))
            
            subtitle_clips.append(txt)

        # 4. Sobrepor tudo
        video_final = CompositeVideoClip([video_base] + subtitle_clips)
        out = os.path.join(output_dir, "video_legendado.mp4")
        video_final.write_videofile(out, fps=24, codec="libx264", audio_codec="aac")
        return out

# --- GUI E FLUXO PRINCIPAL ---
class AutomacaoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Automation Setup")
        self.root.geometry("650x880")
        
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
        
        # Local Images
        tk.Label(root, text="Local Images (optional):", font=('Arial', 10, 'bold'), bg=bg_color, fg=fg_color).pack(pady=(10, 0))
        img_frame = tk.Frame(root, bg=bg_color)
        img_frame.pack(pady=5)
        self.local_imgs = []
        self.local_imgs_lbl = tk.Label(img_frame, text="0 images selected", bg=bg_color, fg=fg_color)
        self.local_imgs_lbl.pack(side=tk.LEFT, padx=5)
        tk.Button(img_frame, text="Browse Images", command=self.browse_images, bg=btn_bg, fg=fg_color).pack(side=tk.LEFT)
        
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
        
        # Internet Search Toggle
        self.use_internet_search_var = tk.BooleanVar(value=True)
        tk.Checkbutton(root, text="Enable Internet Image Search (DuckDuckGo)", variable=self.use_internet_search_var, bg=bg_color, fg=fg_color, selectcolor=btn_bg, activebackground=bg_color, activeforeground=fg_color, font=('Arial', 10, 'bold')).pack(pady=(10, 0))
        
        # Search terms
        tk.Label(root, text="Image Search Terms (comma separated):", font=('Arial', 10, 'bold'), bg=bg_color, fg=fg_color).pack(pady=(10, 0))
        self.terms_var = tk.StringVar(value="The simulation theory and our reality, matrix code, digital universe, abstract technology, future city")
        tk.Entry(root, textvariable=self.terms_var, width=75, bg=entry_bg, fg=fg_color, insertbackground=fg_color).pack(pady=5)
        
        # Generate Button
        self.btn = tk.Button(root, text="Generate Video", command=self.start_generation, bg="#4CAF50", fg="white", font=('Arial', 12, 'bold'))
        self.btn.pack(pady=20)
        
        # Logs
        tk.Label(root, text="Progress Logs:", font=('Arial', 10, 'bold'), bg=bg_color, fg=fg_color).pack()
        self.log_area = scrolledtext.ScrolledText(root, height=12, width=75, state='disabled', bg=entry_bg, fg=fg_color)
        self.log_area.pack(pady=5)
        
    def browse_dir(self):
        directory = filedialog.askdirectory(initialdir=self.out_dir_var.get())
        if directory:
            self.out_dir_var.set(directory)

    def browse_images(self):
        files = filedialog.askopenfilenames(title="Select Images", filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")])
        if files:
            self.local_imgs = list(files)
            self.local_imgs_lbl.config(text=f"{len(self.local_imgs)} images selected")

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
        use_internet = self.use_internet_search_var.get()
        bg_music = self.bg_music_var.get().strip()
        bg_volume = self.volume_scale.get()
        loop_bg = self.loop_bg_var.get()
        
        # Use a background thread to prevent UI freezing
        threading.Thread(target=self.run_automation_thread, args=(model, prompt, terms, out_dir, self.local_imgs, use_internet, bg_music, bg_volume, loop_bg), daemon=True).start()
        
    def run_automation_thread(self, model, prompt, terms, out_dir, local_imgs, use_internet, bg_music, bg_volume, loop_bg):
        try:
            asyncio.run(self.async_workflow(model, prompt, terms, out_dir, local_imgs, use_internet, bg_music, bg_volume, loop_bg))
            self.log(f"\n[*] DONE! Video saved to {os.path.join(out_dir, 'video_legendado.mp4')}")
        except Exception as e:
            self.log(f"\n[!] Error: {str(e)}")
        finally:
            self.root.after(0, lambda: self.btn.config(state='normal'))
            
    async def async_workflow(self, model, prompt, terms, out_dir, local_imgs, use_internet, bg_music, bg_volume, loop_bg):
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
            
            # 1. Processar imagens locais
            for path in local_imgs:
                kw = os.path.splitext(os.path.basename(path))[0].replace('_', ' ').replace('-', ' ')
                imagens_info.append({'path': path, 'keyword': kw})
                self.log(f"[*] Imagem local adicionada à fila: {kw}")

            # 2. Processar imagens DuckDuckGo
            if terms and use_internet:
                self.log("[*] A descarregar imagens do DuckDuckGo...")
                with DDGS() as ddgs:
                    for i, t in enumerate(terms):
                        self.log(f"  -> A pesquisar: {t}")
                        if i > 0: await asyncio.sleep(2)
                        
                        try:
                            res = list(ddgs.images(t, max_results=1, safesearch="on"))
                        except Exception as e:
                            if "403" in str(e) or "Ratelimit" in str(e):
                                self.log("  [!] Rate limit. A aguardar 5s...")
                                await asyncio.sleep(5)
                                res = list(ddgs.images(t, max_results=1, safesearch="on"))
                            else: raise e
                                
                        if res:
                            path = os.path.join(ASSETS_DIR, f"img_ddg_{i}.jpg")
                            with open(path, 'wb') as f: f.write(requests.get(res[0]['image'], timeout=10).content)
                            imagens_info.append({'path': path, 'keyword': t})
                            
            if not imagens_info:
                raise ValueError("No images were found or downloaded.")
        except Exception as e:
            raise RuntimeError(f"Image Collection failed: {str(e)}")
                    
        try:
            bot.criar_video_com_legendas(audio_file, srt_file, imagens_info, guiao, output_dir=out_dir, bg_music_path=bg_music, bg_volume=bg_volume, loop_bg=loop_bg)
        except Exception as e:
            raise RuntimeError(f"Video Rendering (MoviePy) failed: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AutomacaoGUI(root)
    root.mainloop()