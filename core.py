import os
import datetime
import re
import requests
import edge_tts
import pysubs2
from moviepy import TextClip, ColorClip, CompositeVideoClip, ImageClip, AudioFileClip, concatenate_videoclips
from moviepy.audio.AudioClip import CompositeAudioClip
from config import OLLAMA_API_URL, OUTPUT_DIR, ASSETS_DIR

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