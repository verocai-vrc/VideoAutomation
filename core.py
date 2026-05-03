import os
import datetime
import asyncio
import re
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import edge_tts
import pysubs2

# Force MoviePy and ImageIO to use the local FFmpeg binary if it exists
ffmpeg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe")
if os.path.exists(ffmpeg_path):
    os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_path
    os.environ["FFMPEG_BINARY"] = ffmpeg_path

from moviepy import TextClip, ColorClip, CompositeVideoClip, ImageClip, AudioFileClip, VideoFileClip, concatenate_videoclips
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
        
        # 1. Transmitir o áudio e capturar limites com tentativas (Retries)
        for attempt in range(3):
            try:
                subs_data.clear()
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
                break  # Sucesso, sair do loop
            except Exception as e:
                if attempt < 2:
                    self.log(f"[!] Erro TTS (503 ou Rate Limit). A aguardar 5s (tentativa {attempt+1}/3)...")
                    await asyncio.sleep(5)
                else:
                    raise RuntimeError(f"Falha contínua no TTS. Tente rodar 'pip install --upgrade edge-tts' no terminal. Erro original: {str(e)}")

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
            if not subs_data:
                # Fallback to prevent pysubs2 "No suitable formats" crash on empty files
                f.write("1\n00:00:00,000 --> 00:00:01,000\n \n\n")
                self.log("[!] Aviso: O TTS não retornou limites de palavras. Legendas poderão faltar.")
            else:
                for i, word in enumerate(subs_data):
                    start_time = format_srt_time(word["start"])
                    # O fim é o início + a duração da palavra
                    end_time = format_srt_time(word["start"] + word["duration"])
                    
                    f.write(f"{i + 1}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{word['text']}\n\n")
        
        self.log(f"[V] Áudio e Legendas gerados com sucesso em {ASSETS_DIR}")
        return audio_path, subs_path

    def criar_video_com_legendas(self, audio_p, srt_p, imagens_info, guiao, output_dir=OUTPUT_DIR, bg_music_path=None, bg_volume=0.1, loop_bg=True, enable_narration=True):
        """Monta o vídeo final com imagens sincronizadas ao guião e legendas queimadas."""
        self.log("[*] A planear cronologia das imagens e a renderizar vídeo...")
        if not os.path.exists(output_dir): os.makedirs(output_dir)
        tts_audio = AudioFileClip(audio_p)
        duracao_planeada = tts_audio.duration

        def fit_to_vertical(clip):
            w, h = clip.size
            target_ratio = 1080 / 1920.0
            clip_ratio = w / float(max(h, 1))
            
            if clip_ratio > target_ratio:
                if hasattr(clip, 'resized'): clip = clip.resized(height=1920)
                else: clip = clip.resize(height=1920)
            else:
                if hasattr(clip, 'resized'): clip = clip.resized(width=1080)
                else: clip = clip.resize(width=1080)
                
            w, h = clip.size
            if hasattr(clip, 'cropped'):
                clip = clip.cropped(width=1080, height=1920, x_center=w/2, y_center=h/2)
            else:
                clip = clip.crop(width=1080, height=1920, x_center=w/2, y_center=h/2)
            
            return clip

        def get_media_clip(path, dur):
            if path.lower().endswith(('.mp4', '.mov', '.avi', '.webm')):
                clip = VideoFileClip(path)
                if clip.duration < dur:
                    repeats = int(dur // clip.duration) + 1
                    clip = concatenate_videoclips([clip] * repeats, method="compose")
                    if hasattr(clip, 'subclipped'):
                        clip = clip.subclipped(0, dur)
                    else:
                        clip = clip.subclip(0, dur)
                clip = fit_to_vertical(clip)
                return clip
            else:
                clip = ImageClip(np.array(Image.open(path).convert('RGB')))
                if hasattr(clip, 'with_duration'):
                    clip = clip.with_duration(dur)
                else:
                    clip = clip.set_duration(dur)
                clip = fit_to_vertical(clip)
                return clip

        # 1. Carregar legendas primeiro para ter tempos precisos
        try:
            subs = pysubs2.load(srt_p, encoding="utf-8")
        except Exception as e:
            self.log(f"[!] Ficheiro de legendas vazio/inválido ({str(e)}). A renderizar sem texto no ecrã.")
            subs = []
            
        script_text = ""
        script_timings = [] # (index in script_text, start_time)
        
        for line in subs:
            script_timings.append((len(script_text), line.start / 1000.0))
            script_text += line.text + " "

        # 2. Planear a linha do tempo das imagens baseada nos tempos reais do guião
        guiao_lower = script_text.lower()
        matched = []
        unmatched = []
        
        if not imagens_info:
            video_base = ColorClip(size=(1080, 1920), color=(0,0,0))
            if hasattr(video_base, 'with_duration'):
                video_base = video_base.with_duration(duracao_planeada)
            else:
                video_base = video_base.set_duration(duracao_planeada)
        else:
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
                dur = duracao_planeada / max(1, len(unmatched))
                img_clips = [get_media_clip(img, dur) for img in unmatched]
            else:
                if matched[0][0] > 0.5:
                    matched.insert(0, (0.0, unmatched.pop(0))) if unmatched else matched.__setitem__(0, (0.0, matched[0][1]))
                else:
                    matched[0] = (0.0, matched[0][1])
                    
                starts, paths = [m[0] for m in matched], [m[1] for m in matched]
                
                if unmatched:
                    last_t = starts[-1]
                    step = (duracao_planeada - last_t) / (len(unmatched) + 1)
                    for i, u in enumerate(unmatched):
                        starts.append(last_t + step * (i + 1))
                        paths.append(u)
                        
                img_clips = []
                for i in range(len(starts)):
                    dur = (starts[i+1] if i+1 < len(starts) else duracao_planeada) - starts[i]
                    if dur > 0:
                        img_clips.append(get_media_clip(paths[i], dur))

            video_base = concatenate_videoclips(img_clips, method="compose")

        duracao_final = video_base.duration if hasattr(video_base, 'duration') and video_base.duration else duracao_planeada

        audio_layers = []
        if video_base.audio:
            audio_layers.append(video_base.audio)
            
        if enable_narration:
            audio_layers.append(tts_audio)
            
        if bg_music_path and os.path.exists(bg_music_path):
            try:
                self.log(f"[*] A adicionar música de fundo: {os.path.basename(bg_music_path)}")
                bg_clip = AudioFileClip(bg_music_path)
                if hasattr(bg_clip, 'multiply_volume'): bg_clip = bg_clip.multiply_volume(bg_volume)
                elif hasattr(bg_clip, 'with_volume_multiplier'): bg_clip = bg_clip.with_volume_multiplier(bg_volume)
                elif hasattr(bg_clip, 'volumex'): bg_clip = bg_clip.volumex(bg_volume)
                
                if loop_bg:
                    repeats = int(duracao_final // bg_clip.duration) + 1
                    bg_clips = [bg_clip.with_start(i * bg_clip.duration) for i in range(repeats)]
                    bg_clip = CompositeAudioClip(bg_clips)
                    if hasattr(bg_clip, 'with_duration'): bg_clip = bg_clip.with_duration(duracao_final)
                    else: bg_clip = bg_clip.set_duration(duracao_final)
                else:
                    if hasattr(bg_clip, 'with_duration'):
                        bg_clip = bg_clip.with_duration(min(duracao_final, bg_clip.duration))
                    else:
                        bg_clip = bg_clip.set_duration(min(duracao_final, bg_clip.duration))
                    
                audio_layers.append(bg_clip)
            except Exception as e:
                self.log(f"[!] Erro ao processar música de fundo: {e}")

        if audio_layers:
            final_audio = CompositeAudioClip(audio_layers)
            if hasattr(video_base, 'with_audio'):
                video_base = video_base.with_audio(final_audio)
            else:
                video_base = video_base.set_audio(final_audio)

        # 3. Processar Legendas (SRT -> TextClips)
        subtitle_clips = []
        
        def criar_legenda_pil(texto):
            largura, altura = 900, 150
            img = Image.new('RGBA', (largura, altura), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            try:
                # Tentar usar Arial Bold padrão do Windows
                font = ImageFont.truetype("arialbd.ttf", 60)
            except IOError:
                try:
                    font = ImageFont.truetype("arial.ttf", 60)
                except IOError:
                    font = ImageFont.load_default()
                    
            try:
                bbox = draw.textbbox((0, 0), texto, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
            except AttributeError:
                text_w, text_h = draw.textsize(texto, font=font)
                
            x = (largura - text_w) / 2
            y = (altura - text_h) / 2
            
            # Desenhar o contorno (stroke)
            for ox in [-2, 0, 2]:
                for oy in [-2, 0, 2]:
                    draw.text((x + ox, y + oy), texto, font=font, fill='black')
                    
            # Desenhar o texto principal
            draw.text((x, y), texto, font=font, fill='yellow')
            
            img_np = np.array(img)
            rgb = img_np[:, :, :3]
            alpha = img_np[:, :, 3] / 255.0
            
            clip = ImageClip(rgb)
            try:
                # For newer MoviePy versions (e.g., 2.x)
                mask_clip = ImageClip(alpha, is_mask=True)
            except TypeError:
                # Fallback for older MoviePy versions (e.g., 1.x)
                mask_clip = ImageClip(alpha, ismask=True)

            if hasattr(clip, 'with_mask'):
                return clip.with_mask(mask_clip)
            return clip.set_mask(mask_clip)

        for line in subs:
            start = line.start / 1000.0
            end = line.end / 1000.0
            duration = end - start
            if duration <= 0: continue
            
            clip_sub = criar_legenda_pil(line.text)
            if hasattr(clip_sub, 'with_start'):
                txt = clip_sub.with_start(start).with_duration(duration).with_position(('center', 1400))
            else:
                txt = clip_sub.set_start(start).set_duration(duration).set_position(('center', 1400))
            subtitle_clips.append(txt)

        # 4. Sobrepor tudo
        video_final = CompositeVideoClip([video_base] + subtitle_clips, size=(1080, 1920))
        if hasattr(video_final, 'with_duration'):
            video_final = video_final.with_duration(duracao_final)
        else:
            video_final = video_final.set_duration(duracao_final)
            
        out = os.path.join(output_dir, "video_legendado.mp4")
        video_final.write_videofile(out, fps=24, codec="libx264", audio_codec="aac")
        return out