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
    ffmpeg_dir = os.path.dirname(os.path.abspath(__file__))
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

from moviepy import TextClip, ColorClip, CompositeVideoClip, ImageClip, AudioFileClip, VideoFileClip, concatenate_videoclips
from moviepy.audio.AudioClip import CompositeAudioClip
from config import OLLAMA_API_URL, OUTPUT_DIR, ASSETS_DIR

try:
    from proglog import TqdmProgressBarLogger as BaseLogger
except ImportError:
    try:
        from proglog import ProgressBarLogger as BaseLogger
    except ImportError:
        BaseLogger = None

if BaseLogger:
    class UIProgressLogger(BaseLogger):
        def __init__(self, progress_cb):
            super().__init__()
            self.progress_cb = progress_cb
        def bars_callback(self, bar, attr, value, old_value=None):
            super().bars_callback(bar, attr, value, old_value)
            if attr == 'index':
                total = self.bars[bar].get('total', 0)
                if total > 0 and self.progress_cb:
                    self.progress_cb((value / total) * 100)
else:
    UIProgressLogger = None

class ParceiroAutomacao:
    def __init__(self, model="llama3", log_cb=print, progress_cb=None):
        self.model = model
        self.log = log_cb
        self.progress_cb = progress_cb

    def gerar_guiao(self, prompt):
        """Gera o guião usando o prompt fornecido."""
        self.log("[*] A criar guião...")
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()
        texto = response.json()['response'].strip()
        
        # Remover timestamps (ex: 00:00, 00:00:00) e descrições indesejadas
        texto = re.sub(r'\[?\b\d{1,2}:\d{2}(:\d{2})?\b\]?', '', texto)
        # Remover marcações de cena tipo (Visuals: ...) ou [Scene: ...]
        texto = re.sub(r'\(.*?\)', '', texto)
        texto = re.sub(r'\[.*?\]', '', texto)
        # Remover labels de speaker
        texto = re.sub(r'\b(Speaker\s*\d+|Narrator|Host|Voiceover|AI):\s*', '', texto, flags=re.IGNORECASE)
        texto = re.sub(r'\n+', '\n', texto)
        
        return re.sub(r'[ \t]+', ' ', texto).strip()

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

    def transcrever_video(self, video_path, base_name):
        try:
            import whisper
        except ImportError:
            raise RuntimeError("A biblioteca Whisper não está instalada. Abra o terminal e corra: pip install openai-whisper")
            
        self.log("[*] A analisar o áudio do vídeo local com Whisper (isto pode demorar alguns minutos)...")
        model = whisper.load_model("base")
        result = model.transcribe(video_path, word_timestamps=True)
        
        subs_path = os.path.join(ASSETS_DIR, f"{base_name}.srt")
        
        def format_srt_time(seconds):
            td = datetime.timedelta(seconds=seconds)
            total_seconds = int(td.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            secs = total_seconds % 60
            millis = int(td.microseconds / 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

        with open(subs_path, "w", encoding="utf-8") as f:
            idx = 1
            for segment in result.get("segments", []):
                words = segment.get("words", [])
                items_to_write = words if words else [segment]
                for item in items_to_write:
                    start_time = format_srt_time(item["start"])
                    end_time = format_srt_time(item["end"])
                    text = item.get("word", item.get("text", "")).strip()
                    if text:
                        f.write(f"{idx}\n")
                        f.write(f"{start_time} --> {end_time}\n")
                        f.write(f"{text}\n\n")
                        idx += 1
                        
        self.log(f"[V] Transcrição concluída com sucesso em {ASSETS_DIR}")
        return subs_path

    def criar_video_com_legendas(self, audio_p, srt_p, imagens_info, guiao, output_dir=OUTPUT_DIR, bg_music_path=None, bg_volume=0.1, loop_bg=True, enable_narration=True, transcribe_mode=False, sub_font="Arial Bold", sub_color="yellow", sub_size=60, transition="Cut", sub_y=1300, visual_effect="None"):
        """Monta o vídeo final com imagens sincronizadas ao guião e legendas queimadas."""
        self.log("[*] A planear cronologia das imagens e a renderizar vídeo...")
        if not os.path.exists(output_dir): os.makedirs(output_dir)
        
        video_base_original = None
        if transcribe_mode and audio_p.lower().endswith(('.mp4', '.mov', '.avi', '.webm')):
            video_base_original = VideoFileClip(audio_p)
            video_base_original = fit_to_vertical(video_base_original)
            tts_audio = video_base_original.audio
            duracao_planeada = video_base_original.duration if video_base_original.duration else tts_audio.duration
        else:
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

        def apply_visual_effect(clip, effect, dur):
            if effect == "None": return clip
            w, h = clip.size
            try:
                if effect == "Zoom-In":
                    c = clip.resized(lambda t: 1 + 0.1 * (t / max(dur, 0.001))) if hasattr(clip, 'resized') else clip.resize(lambda t: 1 + 0.1 * (t / max(dur, 0.001)))
                    c = c.with_position(('center', 'center')) if hasattr(c, 'with_position') else c.set_position(('center', 'center'))
                    comp = CompositeVideoClip([c], size=(w, h))
                    return comp.with_duration(dur) if hasattr(comp, 'with_duration') else comp.set_duration(dur)
                elif effect == "Zoom-Out":
                    c = clip.resized(lambda t: 1.1 - 0.1 * (t / max(dur, 0.001))) if hasattr(clip, 'resized') else clip.resize(lambda t: 1.1 - 0.1 * (t / max(dur, 0.001)))
                    c = c.with_position(('center', 'center')) if hasattr(c, 'with_position') else c.set_position(('center', 'center'))
                    comp = CompositeVideoClip([c], size=(w, h))
                    return comp.with_duration(dur) if hasattr(comp, 'with_duration') else comp.set_duration(dur)
                elif effect.startswith("Pan "):
                    c = clip.resized(1.1) if hasattr(clip, 'resized') else clip.resize(1.1)
                    def pos(t):
                        progress = t / max(dur, 0.001)
                        cw, ch = c.size
                        if effect == "Pan Left": x, y = -(cw - w) + (cw - w) * progress, -(ch - h) / 2
                        elif effect == "Pan Right": x, y = 0 - (cw - w) * progress, -(ch - h) / 2
                        elif effect == "Pan Up": x, y = -(cw - w) / 2, -(ch - h) + (ch - h) * progress
                        elif effect == "Pan Down": x, y = -(cw - w) / 2, 0 - (ch - h) * progress
                        else: x, y = -(cw - w) / 2, -(ch - h) / 2
                        return (x, y)
                    c = c.with_position(pos) if hasattr(c, 'with_position') else c.set_position(pos)
                    comp = CompositeVideoClip([c], size=(w, h))
                    return comp.with_duration(dur) if hasattr(comp, 'with_duration') else comp.set_duration(dur)
                return clip
            except Exception as e:
                self.log(f"[!] Aviso ao aplicar efeito visual {effect}: {e}")
                return clip

        def get_media_clip(path, dur):
            if path.lower().endswith(('.mp4', '.mov', '.avi', '.webm')):
                clip = VideoFileClip(path)
                if clip.duration < dur:
                    repeats = int(dur // clip.duration) + 1
                    clip = concatenate_videoclips([clip] * repeats, method="chain")
                    if hasattr(clip, 'subclipped'):
                        clip = clip.subclipped(0, dur)
                    else:
                        clip = clip.subclip(0, dur)
                clip = fit_to_vertical(clip)
            else:
                clip = ImageClip(np.array(Image.open(path).convert('RGB')))
                if hasattr(clip, 'with_duration'):
                    clip = clip.with_duration(dur)
                else:
                    clip = clip.set_duration(dur)
                clip = fit_to_vertical(clip)
                
            clip = apply_visual_effect(clip, visual_effect, dur)
            
            effect_dur = min(0.5, dur / 2.0) if dur > 0 else 0.5
            is_v2 = hasattr(clip, 'with_effects')
            
            try:
                if is_v2:
                    from moviepy.video.fx.FadeIn import FadeIn
                    from moviepy.video.fx.FadeOut import FadeOut
                    if transition == "Fade In": clip = clip.with_effects([FadeIn(effect_dur)])
                    elif transition == "Fade Out": clip = clip.with_effects([FadeOut(effect_dur)])
                    elif transition == "Fade In & Out": clip = clip.with_effects([FadeIn(effect_dur), FadeOut(effect_dur)])
                else:
                    def fx_fadein(c, d):
                        d = max(0.001, d)
                        return c.fl(lambda gf, t: (np.clip(t / d, 0.0, 1.0) * gf(t)).astype(np.uint8))
                    def fx_fadeout(c, d):
                        d = max(0.001, d)
                        dur_val = c.duration if c.duration is not None else dur
                        return c.fl(lambda gf, t: (np.clip((dur_val - t) / d, 0.0, 1.0) * gf(t)).astype(np.uint8))
                    
                    if transition == "Fade In": clip = fx_fadein(clip, effect_dur)
                    elif transition == "Fade Out": clip = fx_fadeout(clip, effect_dur)
                    elif transition == "Fade In & Out": clip = fx_fadeout(fx_fadein(clip, effect_dur), effect_dur)
            except Exception as e:
                self.log(f"[!] Aviso ao aplicar transição {transition}: {e}")
                
            return clip

        def get_overlay_clip(path, dur, sub_y, transition):
            if path.lower().endswith(('.mp4', '.mov', '.avi', '.webm')):
                clip = VideoFileClip(path)
                if clip.duration < dur:
                    repeats = int(dur // clip.duration) + 1
                    clip = concatenate_videoclips([clip] * repeats, method="chain")
                if hasattr(clip, 'subclipped'): clip = clip.subclipped(0, dur)
                else: clip = clip.subclip(0, dur)
            else:
                clip = ImageClip(np.array(Image.open(path).convert('RGB')))
                if hasattr(clip, 'with_duration'): clip = clip.with_duration(dur)
                else: clip = clip.set_duration(dur)
                
            max_h = max(200, sub_y - 150)
            max_w = 950
            w, h = clip.size
            ratio = min(max_w / float(max(w, 1)), max_h / float(max(h, 1)))
            
            if hasattr(clip, 'resized'): clip = clip.resized(ratio)
            else: clip = clip.resize(ratio)
                
            clip = apply_visual_effect(clip, visual_effect, dur)
            
            pos_y = (max_h - (h * ratio)) / 2 + 50
            if hasattr(clip, 'with_position'): clip = clip.with_position(('center', pos_y))
            else: clip = clip.set_position(('center', pos_y))
                
            effect_dur = min(0.5, dur / 2.0) if dur > 0 else 0.5
            is_v2 = hasattr(clip, 'with_effects')
            try:
                if is_v2:
                    from moviepy.video.fx.FadeIn import FadeIn
                    from moviepy.video.fx.FadeOut import FadeOut
                    if transition == "Fade In": clip = clip.with_effects([FadeIn(effect_dur)])
                    elif transition == "Fade Out": clip = clip.with_effects([FadeOut(effect_dur)])
                    elif transition == "Fade In & Out": clip = clip.with_effects([FadeIn(effect_dur), FadeOut(effect_dur)])
                else:
                    def fx_fadein(c, d):
                        d = max(0.001, d)
                        return c.fl(lambda gf, t: (np.clip(t / d, 0.0, 1.0) * gf(t)).astype(np.uint8))
                    def fx_fadeout(c, d):
                        d = max(0.001, d)
                        dur_val = c.duration if c.duration is not None else dur
                        return c.fl(lambda gf, t: (np.clip((dur_val - t) / d, 0.0, 1.0) * gf(t)).astype(np.uint8))
                    
                    if transition == "Fade In": clip = fx_fadein(clip, effect_dur)
                    elif transition == "Fade Out": clip = fx_fadeout(clip, effect_dur)
                    elif transition == "Fade In & Out": clip = fx_fadeout(fx_fadein(clip, effect_dur), effect_dur)
            except Exception as e:
                self.log(f"[!] Aviso ao aplicar transição overlay {transition}: {e}")
                
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
        overlaid_clips = []
        
        if video_base_original is not None:
            video_base = video_base_original
            if imagens_info:
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
                        
                matched.sort(key=lambda x: x[0])
                
                for i, (t, path) in enumerate(matched):
                    max_dur = 4.0
                    next_t = matched[i+1][0] if i + 1 < len(matched) else duracao_planeada
                    dur = min(max_dur, next_t - t)
                    if dur <= 0: continue
                    
                    try:
                        clip = get_overlay_clip(path, dur, sub_y, transition)
                        if hasattr(clip, 'with_start'): clip = clip.with_start(t)
                        else: clip = clip.set_start(t)
                        overlaid_clips.append(clip)
                    except Exception as e:
                        self.log(f"[!] Erro ao criar overlay de {path}: {e}")
        else:
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
            
        if enable_narration and not transcribe_mode:
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

        # 3. Processar Legendas (SRT -> TextClips)
        subtitle_clips = []
        
        def criar_legenda_pil(texto):
            import textwrap
            largura, altura = 1040, 500
            img = Image.new('RGBA', (largura, altura), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            font_map = {
                "Arial": "arial.ttf",
                "Arial Bold": "arialbd.ttf",
                "Impact": "impact.ttf",
                "Comic Sans": "comic.ttf",
                "Times New Roman": "times.ttf"
            }
            font_file = font_map.get(sub_font, "arialbd.ttf")

            try:
                font = ImageFont.truetype(font_file, sub_size)
            except IOError:
                try:
                    font = ImageFont.truetype("arial.ttf", sub_size)
                except IOError:
                    font = ImageFont.load_default()
                    
            # Auto-wrap text based on estimated character width vs box width
            char_width = max(10, sub_size * 0.55)
            max_chars = max(15, int(900 / char_width))
            wrapped_text = "\n".join(textwrap.wrap(texto, width=max_chars))

            try:
                bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, align='center')
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
            except AttributeError:
                text_w, text_h = draw.textsize(wrapped_text, font=font)
                
            x = (largura - text_w) / 2
            y = (altura - text_h) / 2
            
            # Desenhar o contorno (stroke)
            stroke_width = max(2, int(sub_size * 0.06))
            for ox in range(-stroke_width, stroke_width + 1):
                for oy in range(-stroke_width, stroke_width + 1):
                    if ox == 0 and oy == 0: continue
                    try:
                        draw.multiline_text((x + ox, y + oy), wrapped_text, font=font, fill='black', align='center')
                    except AttributeError:
                        draw.text((x + ox, y + oy), wrapped_text, font=font, fill='black')
                    
            # Desenhar o texto principal
            try:
                draw.multiline_text((x, y), wrapped_text, font=font, fill=sub_color, align='center')
            except AttributeError:
                draw.text((x, y), wrapped_text, font=font, fill=sub_color)
            
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

        # Group word-by-word subtitles into cleaner, multi-word lines for rendering
        grouped_subs = []
        if subs:
            current_line_text = ""
            line_start_time = subs[0].start
            last_word_end_time = subs[0].end
            max_chars_per_line = 60  # PIL will smartly wrap the lines inside the box bounds

            for event in subs:
                # If adding the new word exceeds the line limit, and the line isn't empty
                if len(current_line_text) + len(event.text) + 1 > max_chars_per_line and current_line_text:
                    # Finalize the current line and add it to our list
                    grouped_subs.append({
                        "text": current_line_text.strip(),
                        "start": line_start_time,
                        "end": last_word_end_time
                    })
                    # Start a new line with the current word
                    current_line_text = event.text + " "
                    line_start_time = event.start
                else:
                    # Otherwise, just add the word to the current line
                    current_line_text += event.text + " "
                last_word_end_time = event.end

            # Add the final accumulated line after the loop finishes
            if current_line_text:
                grouped_subs.append({ "text": current_line_text.strip(), "start": line_start_time, "end": last_word_end_time })


        for line in grouped_subs:
            start = line['start'] / 1000.0
            end = line['end'] / 1000.0
            duration = end - start
            if duration <= 0: continue
            
            clip_sub = criar_legenda_pil(line['text'])
            if hasattr(clip_sub, 'with_start'):
                txt = clip_sub.with_start(start).with_duration(duration).with_position(('center', sub_y))
            else:
                txt = clip_sub.set_start(start).set_duration(duration).set_position(('center', sub_y))
            subtitle_clips.append(txt)

        # 4. Sobrepor tudo
        bg_black = ColorClip(size=(1080, 1920), color=(0,0,0))
        if hasattr(bg_black, 'with_duration'):
            bg_black = bg_black.with_duration(duracao_final)
        else:
            bg_black = bg_black.set_duration(duracao_final)
            
        video_final = CompositeVideoClip([bg_black, video_base] + overlaid_clips + subtitle_clips, size=(1080, 1920))
        
        if audio_layers:
            final_audio = CompositeAudioClip(audio_layers)
            if hasattr(video_final, 'with_audio'):
                video_final = video_final.with_audio(final_audio)
            else:
                video_final = video_final.set_audio(final_audio)
                
        if hasattr(video_final, 'with_duration'):
            video_final = video_final.with_duration(duracao_final)
        else:
            video_final = video_final.set_duration(duracao_final)
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out = os.path.join(output_dir, f"video_legendado_{timestamp}.mp4")
        logger = UIProgressLogger(self.progress_cb) if UIProgressLogger and self.progress_cb else "bar"
        video_final.write_videofile(out, fps=24, codec="libx264", audio_codec="aac", logger=logger)
        
        # Clean up MoviePy clips to prevent FFmpeg memory leaks
        try:
            video_final.close()
            if video_base_original: video_base_original.close()
            if hasattr(tts_audio, 'close'): tts_audio.close()
        except Exception as e:
            self.log(f"[!] Aviso de limpeza de memória: {e}")
            
        return out