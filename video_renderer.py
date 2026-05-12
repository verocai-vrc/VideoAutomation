import os
import datetime
import re
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pysubs2
import tempfile

# Force MoviePy and ImageIO to use the local FFmpeg binary if it exists
ffmpeg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ffmpeg.exe")
if os.path.exists(ffmpeg_path):
    os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_path
    os.environ["FFMPEG_BINARY"] = ffmpeg_path
    ffmpeg_dir = os.path.dirname(ffmpeg_path)
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

from moviepy import TextClip, ColorClip, CompositeVideoClip, ImageClip, AudioFileClip, VideoFileClip, concatenate_videoclips
from moviepy.audio.AudioClip import CompositeAudioClip
from config import OUTPUT_DIR

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

class VideoRenderer:
    def __init__(self, log_cb=print, progress_cb=None):
        self.log = log_cb
        self.progress_cb = progress_cb

    def planejar_timeline(self, audio_p, srt_p, imagens_info, transcribe_mode=False):
        try:
            if transcribe_mode and audio_p.lower().endswith(('.mp4', '.mov', '.avi', '.webm')):
                with VideoFileClip(audio_p) as v:
                    duracao_planeada = v.duration or (v.audio.duration if v.audio else 60.0)
            else:
                with AudioFileClip(audio_p) as a:
                    duracao_planeada = a.duration
        except Exception as e:
            self.log(f"[!] Aviso ao calcular duração (usando 60s fallback): {e}")
            duracao_planeada = 60.0

        try:
            subs = pysubs2.load(srt_p, encoding="utf-8")
            script_text = ""
            script_timings = []
            for line in subs:
                script_timings.append((len(script_text), line.start / 1000.0))
                script_text += line.text + " "
        except Exception as e:
            self.log(f"[!] Erro ao carregar legendas no planeamento: {e}")
            script_text = ""
            script_timings = []

        guiao_lower = script_text.lower()
        
        image_matches = []
        for info in imagens_info:
            kw = info['keyword'].lower().strip()
            idx = -1
            if kw:
                match = re.search(r'\b' + re.escape(kw) + r'\b', guiao_lower)
                if match:
                    idx = match.start()
                else:
                    idx = guiao_lower.find(kw)
            
            if idx != -1:
                t = 0
                for start_idx, time in reversed(script_timings):
                    if idx >= start_idx:
                        t = time
                        break
                image_matches.append({"info": info, "t": t, "matched": True})
            else:
                image_matches.append({"info": info, "t": -1, "matched": False})
                
        matched = sorted([m for m in image_matches if m['matched']], key=lambda x: x['t'])
        unmatched = [m for m in image_matches if not m['matched']]
        
        final_schedule = matched[:]
        
        if not final_schedule and unmatched:
            step = duracao_planeada / max(1, len(unmatched))
            for i, u in enumerate(unmatched):
                final_schedule.append({"info": u["info"], "t": i * step})
            unmatched = []
            
        for u in unmatched:
            best_gap_idx = 0
            max_gap = final_schedule[0]['t'] - 0 if final_schedule else 0
            insert_t = max_gap / 2.0
            
            for i in range(len(final_schedule) - 1):
                gap = final_schedule[i+1]['t'] - final_schedule[i]['t']
                if gap > max_gap:
                    max_gap = gap
                    best_gap_idx = i + 1
                    insert_t = final_schedule[i]['t'] + gap / 2.0
                    
            if final_schedule:
                end_gap = duracao_planeada - final_schedule[-1]['t']
                if end_gap > max_gap:
                    max_gap = end_gap
                    best_gap_idx = len(final_schedule)
                    insert_t = final_schedule[-1]['t'] + end_gap / 2.0
            
            final_schedule.insert(best_gap_idx, {"info": u["info"], "t": insert_t})
            
        if final_schedule and not transcribe_mode:
            final_schedule[0]['t'] = 0.0
        
        timeline_plan = []
        if transcribe_mode:
            timeline_plan.append({"track": 1, "start": 0.0, "duration": duracao_planeada, "path": audio_p, "text": "Base Video", "id": "base_main"})
            for i, item in enumerate(final_schedule):
                t = item['t']
                next_t = final_schedule[i+1]['t'] if i + 1 < len(final_schedule) else duracao_planeada
                dur = min(4.0, next_t - t)
                if dur > 0:
                    info = item['info']
                    timeline_plan.append({"track": 2, "start": t, "duration": dur, "path": info['path'], "text": info['keyword'], "id": f"ov_{i}"})
        else:
            for i, item in enumerate(final_schedule):
                t = item['t']
                next_t = final_schedule[i+1]['t'] if i + 1 < len(final_schedule) else duracao_planeada
                dur = next_t - t
                if dur > 0:
                    info = item['info']
                    timeline_plan.append({"track": 1, "start": t, "duration": dur, "path": info['path'], "text": info['keyword'], "id": f"base_{i}"})
                            
        return duracao_planeada, timeline_plan

    def criar_video_com_legendas(self, audio_p, srt_p, imagens_info, guiao, output_dir=OUTPUT_DIR, bg_music_path=None, bg_volume=0.1, loop_bg=True, enable_narration=True, transcribe_mode=False, sub_font="Arial Bold", sub_font_file=None, sub_color="yellow", sub_outline_color="black", sub_outline_width=3, sub_size=60, transition="Cut", sub_y=1300, visual_effect="None", custom_timeline=None):
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
        base_clips = []
        
        if video_base_original is not None:
            if hasattr(video_base_original, 'with_start'):
                base_clips.append(video_base_original.with_start(0))
            else:
                base_clips.append(video_base_original.set_start(0))

        if custom_timeline is None:
            _, custom_timeline = self.planejar_timeline(audio_p, srt_p, imagens_info, transcribe_mode)

        if custom_timeline:
            for item in custom_timeline:
                path = item['path']
                dur = item['duration']
                start = item['start']
                track = item['track']
                
                if dur <= 0: continue
                
                # Skip re-adding the original base video since it's already added above
                if track == 1 and path == audio_p and transcribe_mode:
                    continue
                    
                if track == 1:
                    c = get_media_clip(path, dur)
                    if hasattr(c, 'with_start'): c = c.with_start(start)
                    else: c = c.set_start(start)
                    base_clips.append(c)
                elif track >= 2:
                    try:
                        c = get_overlay_clip(path, dur, sub_y, transition)
                        if hasattr(c, 'with_start'): c = c.with_start(start)
                        else: c = c.set_start(start)
                        overlaid_clips.append(c)
                    except Exception as e:
                        self.log(f"[!] Erro ao criar overlay de {path}: {e}")

        duracao_final = duracao_planeada

        audio_layers = []
        if enable_narration and not transcribe_mode:
            audio_layers.append(tts_audio)
        elif transcribe_mode and tts_audio is not None:
            audio_layers.append(tts_audio)
            
        for c in base_clips + overlaid_clips:
            if c is video_base_original:
                continue
            if getattr(c, 'audio', None) is not None:
                start_time = getattr(c, 'start', 0)
                if hasattr(c.audio, 'with_start'): audio_layers.append(c.audio.with_start(start_time))
                else: audio_layers.append(c.audio.set_start(start_time))
            
        if bg_music_path and os.path.exists(bg_music_path):
            try:
                self.log(f"[*] A adicionar música de fundo: {os.path.basename(bg_music_path)}")
                bg_clip = AudioFileClip(bg_music_path)
                
                try:
                    # MoviePy v2.0+
                    from moviepy.audio.fx.MultiplyVolume import MultiplyVolume
                    bg_clip = bg_clip.with_effects([MultiplyVolume(bg_volume)])
                except ImportError:
                    # MoviePy v1.x fallback
                    try:
                        from moviepy.audio.fx.volumex import volumex # type: ignore
                        bg_clip = volumex(bg_clip, bg_volume)
                    except ImportError:
                        if hasattr(bg_clip, 'multiply_volume'): bg_clip = bg_clip.multiply_volume(bg_volume)
                        elif hasattr(bg_clip, 'with_volume_multiplier'): bg_clip = bg_clip.with_volume_multiplier(bg_volume)
                        elif hasattr(bg_clip, 'volumex'): bg_clip = bg_clip.volumex(bg_volume)
                
                bg_start = 0.0
                bg_dur = None
                is_custom_bg = False
                bg_found_in_timeline = False
                
                if custom_timeline:
                    for item in custom_timeline:
                        if item.get('id') == 'bg_music':
                            bg_start = item['start']
                            bg_dur = item['duration']
                            is_custom_bg = True
                            bg_found_in_timeline = True
                            break
                            
                if custom_timeline and not bg_found_in_timeline:
                    self.log("[*] Música de fundo removida na timeline.")
                else:
                    if is_custom_bg:
                        if hasattr(bg_clip, 'with_start'): bg_clip = bg_clip.with_start(bg_start)
                        else: bg_clip = bg_clip.set_start(bg_start)
                        
                        if bg_dur is not None:
                            if hasattr(bg_clip, 'with_duration'): bg_clip = bg_clip.with_duration(bg_dur)
                            else: bg_clip = bg_clip.set_duration(bg_dur)
                        
                        if loop_bg:
                            repeats = int(bg_dur // bg_clip.duration) + 1
                            bg_clips = [bg_clip.with_start(bg_start + i * bg_clip.duration) for i in range(repeats)]
                            bg_clip = CompositeAudioClip(bg_clips)
                            if hasattr(bg_clip, 'with_duration'): bg_clip = bg_clip.with_duration(bg_dur).with_start(bg_start)
                            else: bg_clip = bg_clip.set_duration(bg_dur).set_start(bg_start)
                    else:
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
        
        # --- PERFORMANCE OPTIMIZATION 1: Cache the font outside the loop ---
        font_to_use = None
        if sub_font_file and os.path.exists(sub_font_file):
            font_to_use = sub_font_file
        else:
            font_map = {
                "Arial": "arial.ttf",
                "Arial Bold": "arialbd.ttf",
                "Impact": "impact.ttf",
                "Comic Sans": "comic.ttf",
                "Times New Roman": "times.ttf"
            }
            font_to_use = font_map.get(sub_font, "arialbd.ttf")

        try:
            cached_font = ImageFont.truetype(font_to_use, sub_size)
        except IOError:
            try:
                cached_font = ImageFont.truetype("arial.ttf", sub_size)
            except IOError:
                cached_font = ImageFont.load_default()
        # -------------------------------------------------------------------
        
        def criar_legenda_pil(texto):
            import textwrap
            import numpy as np
            largura, altura = 1040, 500
            img = Image.new('RGBA', (largura, altura), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            font = cached_font
                    
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
            
            # --- PERFORMANCE OPTIMIZATION 2: Native Pillow Stroke ---
            try:
                # Native stroke rendering is written in C and executes instantly
                draw.multiline_text((x, y), wrapped_text, font=font, fill=sub_color, align='center', stroke_width=sub_outline_width, stroke_fill=sub_outline_color)
            except TypeError:
                # Fallback for very old Pillow versions (< 6.2.0)
                stroke_width = sub_outline_width
                for ox in range(-stroke_width, stroke_width + 1):
                    for oy in range(-stroke_width, stroke_width + 1):
                        if ox == 0 and oy == 0: continue
                        try:
                            draw.multiline_text((x + ox, y + oy), wrapped_text, font=font, fill=sub_outline_color, align='center')
                        except AttributeError:
                            draw.text((x + ox, y + oy), wrapped_text, font=font, fill=sub_outline_color)
                            
                try:
                    draw.multiline_text((x, y), wrapped_text, font=font, fill=sub_color, align='center')
                except AttributeError:
                    draw.text((x, y), wrapped_text, font=font, fill=sub_color)
            # --------------------------------------------------------
            
            # Converting PIL Image directly to NumPy arrays to bypass MoviePy/ImageIO transparency bugs
            img_np = np.array(img)
            img_rgb = img_np[:, :, :3]
            img_alpha = img_np[:, :, 3] / 255.0
            
            clip = ImageClip(img_rgb)
            try:
                mask_clip = ImageClip(img_alpha, is_mask=True)
            except TypeError:
                mask_clip = ImageClip(img_alpha, ismask=True)
            
            if hasattr(clip, 'with_mask'): clip = clip.with_mask(mask_clip)
            else: clip = clip.set_mask(mask_clip)
            
            return clip

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
        if not (base_clips + overlaid_clips):
            c = ColorClip(size=(1080, 1920), color=(0,0,0))
            if hasattr(c, 'with_duration'): c = c.with_duration(duracao_planeada)
            else: c = c.set_duration(duracao_planeada)
            base_clips.append(c)
            
        base_composite = CompositeVideoClip(base_clips + overlaid_clips, size=(1080, 1920), bg_color=(0,0,0))
        
        if audio_layers:
            final_audio = CompositeAudioClip(audio_layers)
            if hasattr(base_composite, 'with_audio'):
                base_composite = base_composite.with_audio(final_audio)
            else:
                base_composite = base_composite.set_audio(final_audio)
                
        if hasattr(base_composite, 'with_duration'):
            base_composite = base_composite.with_duration(duracao_final)
        else:
            base_composite = base_composite.set_duration(duracao_final)
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out = os.path.join(output_dir, f"video_legendado_{timestamp}.mp4")
        logger = UIProgressLogger(self.progress_cb) if UIProgressLogger and self.progress_cb else "bar"
        threads = os.cpu_count() or 4
        
        temp_base_path = None
        if not transcribe_mode and subtitle_clips:
            self.log("[*] Renderizando fundo em vídeo (Passo 1 de 2) para garantir aplicação das legendas...")
            temp_base_path = os.path.join(output_dir, f"temp_bg_{timestamp}.mp4")
            base_composite.write_videofile(temp_base_path, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", threads=threads, logger=logger)
            
            try: base_composite.close()
            except Exception: pass
            
            base_composite = VideoFileClip(temp_base_path)
            self.log("[*] Renderizando legendas sobre o vídeo (Passo 2 de 2)...")

        # Isolate subtitles on the absolute top layer using a separate composition
        video_final = CompositeVideoClip([base_composite] + subtitle_clips, size=(1080, 1920))
        if hasattr(video_final, 'with_duration'): video_final = video_final.with_duration(duracao_final)
        else: video_final = video_final.set_duration(duracao_final)
        
        video_final.write_videofile(out, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", threads=threads, logger=logger)
        
        # Clean up MoviePy clips to prevent FFmpeg memory leaks
        try:
            video_final.close()
            if temp_base_path and os.path.exists(temp_base_path):
                base_composite.close()
                os.remove(temp_base_path)
            if video_base_original: video_base_original.close()
            if hasattr(tts_audio, 'close'): tts_audio.close()
        except Exception as e:
            self.log(f"[!] Aviso de limpeza de memória: {e}")
            
        return out